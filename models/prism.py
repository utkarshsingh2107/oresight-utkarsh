"""PRISM — Probabilistic Reserve Intelligence and Spatial Modeling.

Ordinary Kriging of synthetic borehole Mn composites onto the 3D block model.

Hackathon prototype: simple spherical variogram + local OK. Not a production
geostatistical system. Input tables are synthetic demonstration data (not MOIL).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Prototype configuration — change the Mn cutoff here (not scattered below).
# ---------------------------------------------------------------------------
MN_CUTOFF_PCT = 20.0
N_KRIGING_NEIGHBORS = 20
Z_ANISOTROPY = 5.0  # stretch vertical axis (shorter correlation in z)
RIDGE = 1e-4
MN_CLIP = (0.0, 55.0)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

def validate_inputs(boreholes: pd.DataFrame, blocks: pd.DataFrame) -> None:
    required_bh = ["hole_id", "x", "y", "collar_z", "depth", "Mn_pct"]
    required_bl = ["block_id", "mine_id", "x", "y", "z", "volume_m3", "density"]
    missing_bh = [c for c in required_bh if c not in boreholes.columns]
    missing_bl = [c for c in required_bl if c not in blocks.columns]
    if missing_bh:
        raise ValueError(f"boreholes.csv missing columns: {missing_bh}")
    if missing_bl:
        raise ValueError(f"blocks.csv missing columns: {missing_bl}")

    if boreholes[required_bh].isna().any().any():
        raise ValueError("boreholes contain nulls in coordinates or Mn_pct")
    if blocks[required_bl].isna().any().any():
        raise ValueError("blocks contain nulls in required columns")
    if not boreholes["hole_id"].is_unique:
        raise ValueError("hole_id must be unique")
    if not blocks["block_id"].is_unique:
        raise ValueError("block_id must be unique")
    if len(boreholes) < 5:
        raise ValueError("need at least 5 boreholes for Ordinary Kriging")
    if not np.isfinite(boreholes[["x", "y", "collar_z", "depth", "Mn_pct"]].to_numpy()).all():
        raise ValueError("non-finite borehole coordinates or Mn")
    if not np.isfinite(blocks[["x", "y", "z"]].to_numpy()).all():
        raise ValueError("non-finite block coordinates")
    if (blocks["volume_m3"] <= 0).any() or (blocks["density"] <= 0).any():
        raise ValueError("volume_m3 and density must be positive")
    mn = boreholes["Mn_pct"].to_numpy()
    if (mn < MN_CLIP[0]).any() or (mn > MN_CLIP[1]).any():
        raise ValueError(f"Mn_pct outside demonstration clip {MN_CLIP}")


def borehole_sample_xyz(boreholes: pd.DataFrame) -> np.ndarray:
    """Composite location: hole midpoint (collar minus half of hole length)."""
    x = boreholes["x"].to_numpy(dtype=float)
    y = boreholes["y"].to_numpy(dtype=float)
    z = boreholes["collar_z"].to_numpy(dtype=float) - 0.5 * boreholes["depth"].to_numpy(
        dtype=float
    )
    return np.column_stack([x, y, z])


def anisotropic_coords(xyz: np.ndarray) -> np.ndarray:
    out = np.array(xyz, dtype=float, copy=True)
    out[:, 2] = out[:, 2] * Z_ANISOTROPY
    return out


def pairwise_upper(coords: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = coords.shape[0]
    i, j = np.triu_indices(n, k=1)
    d = np.linalg.norm(coords[i] - coords[j], axis=1)
    gamma = 0.5 * (values[i] - values[j]) ** 2
    return d, gamma


def experimental_variogram(
    coords: np.ndarray, values: np.ndarray, n_bins: int = 10
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    dist, gamma = pairwise_upper(coords, values)
    max_lag = float(np.percentile(dist, 55))
    max_lag = max(max_lag, 1.0)
    edges = np.linspace(0.0, max_lag, n_bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    means = np.full(n_bins, np.nan)
    counts = np.zeros(n_bins, dtype=int)
    for b in range(n_bins):
        mask = (dist >= edges[b]) & (dist < edges[b + 1])
        counts[b] = int(mask.sum())
        if counts[b] >= 8:
            means[b] = float(gamma[mask].mean())
    return centers, means, counts


def spherical_variogram(h: np.ndarray, nugget: float, partial: float, range_a: float) -> np.ndarray:
    h = np.asarray(h, dtype=float)
    out = np.empty_like(h)
    zero = h <= 0.0
    inside = (h > 0.0) & (h < range_a)
    outside = h >= range_a
    out[zero] = 0.0
    hr = h[inside] / range_a
    out[inside] = nugget + partial * (1.5 * hr - 0.5 * hr**3)
    out[outside] = nugget + partial
    return out


def fit_spherical_variogram(coords: np.ndarray, values: np.ndarray) -> dict[str, float]:
    centers, means, counts = experimental_variogram(coords, values)
    valid = np.isfinite(means) & (counts > 0)
    sill = float(max(np.var(values, ddof=1), 1e-3))
    if valid.sum() < 3:
        return {"nugget": 0.1 * sill, "partial": 0.9 * sill, "range": 150.0, "sill": sill}

    h = centers[valid]
    g = means[valid]
    w = np.sqrt(counts[valid].astype(float))
    best = None
    best_err = np.inf
    dist, _ = pairwise_upper(coords, values)
    range_grid = np.linspace(max(float(np.percentile(dist, 15)), 30.0), float(np.percentile(dist, 70)), 18)
    nugget_fracs = (0.05, 0.1, 0.2, 0.35)
    for rng in range_grid:
        for nf in nugget_fracs:
            nugget = nf * sill
            partial = max(sill - nugget, 1e-4)
            pred = spherical_variogram(h, nugget, partial, float(rng))
            err = float(np.sum(w * (pred - g) ** 2))
            if err < best_err:
                best_err = err
                best = {"nugget": nugget, "partial": partial, "range": float(rng), "sill": sill}
    assert best is not None
    return best


def _krige_one(
    gamma_nn: np.ndarray,
    gamma_to_target: np.ndarray,
    values: np.ndarray,
) -> tuple[float, float]:
    n = values.shape[0]
    a = np.zeros((n + 1, n + 1), dtype=float)
    a[:n, :n] = gamma_nn
    np.fill_diagonal(a[:n, :n], a[:n, :n].diagonal() + RIDGE)
    a[:n, n] = 1.0
    a[n, :n] = 1.0
    b = np.zeros(n + 1, dtype=float)
    b[:n] = gamma_to_target
    b[n] = 1.0
    try:
        sol = np.linalg.solve(a, b)
    except np.linalg.LinAlgError:
        sol, *_ = np.linalg.lstsq(a, b, rcond=None)
    lam = sol[:n]
    mu = sol[n]
    estimate = float(lam @ values)
    variance = float(lam @ gamma_to_target + mu)
    return estimate, max(variance, 0.0)


def ordinary_kriging(
    sample_xyz: np.ndarray,
    sample_values: np.ndarray,
    target_xyz: np.ndarray,
    vparams: dict[str, float],
    n_neighbors: int = N_KRIGING_NEIGHBORS,
) -> tuple[np.ndarray, np.ndarray]:
    samples = anisotropic_coords(sample_xyz)
    targets = anisotropic_coords(target_xyz)
    n = samples.shape[0]
    k = int(min(max(n_neighbors, 3), n))
    d2 = ((targets[:, None, :] - samples[None, :, :]) ** 2).sum(axis=2)
    nn = np.argpartition(d2, kth=k - 1, axis=1)[:, :k]

    estimates = np.empty(targets.shape[0], dtype=float)
    variances = np.empty(targets.shape[0], dtype=float)
    nugget, partial, range_a = vparams["nugget"], vparams["partial"], vparams["range"]

    for i in range(targets.shape[0]):
        idx = nn[i]
        loc = samples[idx]
        vals = sample_values[idx]
        d_ij = np.linalg.norm(loc[:, None, :] - loc[None, :, :], axis=2)
        d_i0 = np.linalg.norm(loc - targets[i], axis=1)
        g_nn = spherical_variogram(d_ij.ravel(), nugget, partial, range_a).reshape(k, k)
        g_t = spherical_variogram(d_i0, nugget, partial, range_a)
        est, var = _krige_one(g_nn, g_t, vals)
        estimates[i] = est
        variances[i] = var

    estimates = np.clip(estimates, MN_CLIP[0], MN_CLIP[1])
    return estimates, variances


def build_summary(result: pd.DataFrame, cutoff: float) -> dict:
    ore = result["is_ore"].eq(1)
    n_ore = int(ore.sum())
    if n_ore:
        avg_ore = float(
            np.average(result.loc[ore, "estimated_mn_pct"], weights=result.loc[ore, "tonnage_t"])
        )
        declared = float(result.loc[ore, "tonnage_t"].sum())
    else:
        avg_ore = None
        declared = 0.0
    return {
        "total_blocks": int(len(result)),
        "ore_blocks": n_ore,
        "waste_blocks": int((~ore).sum()),
        "declared_reserve_t": round(declared, 1),
        "average_ore_mn_pct": None if avg_ore is None else round(avg_ore, 3),
        "min_estimated_mn_pct": round(float(result["estimated_mn_pct"].min()), 3),
        "max_estimated_mn_pct": round(float(result["estimated_mn_pct"].max()), 3),
        "mean_kriging_variance": round(float(result["kriging_variance"].mean()), 4),
        "mn_cutoff_pct": cutoff,
        "provenance": "SYNTHETIC demonstration blocks/boreholes — not real MOIL data",
    }


def run_prism(
    boreholes_path: Path | None = None,
    blocks_path: Path | None = None,
    output_dir: Path | None = None,
    mn_cutoff_pct: float = MN_CUTOFF_PCT,
) -> tuple[pd.DataFrame, dict]:
    boreholes_path = boreholes_path or (RAW / "boreholes.csv")
    blocks_path = blocks_path or (RAW / "blocks.csv")
    output_dir = output_dir or OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    boreholes = pd.read_csv(boreholes_path)
    blocks = pd.read_csv(blocks_path)
    validate_inputs(boreholes, blocks)

    sample_xyz = borehole_sample_xyz(boreholes)
    values = boreholes["Mn_pct"].to_numpy(dtype=float)
    target_xyz = blocks[["x", "y", "z"]].to_numpy(dtype=float)
    vparams = fit_spherical_variogram(anisotropic_coords(sample_xyz), values)

    estimates, variances = ordinary_kriging(sample_xyz, values, target_xyz, vparams)

    result = blocks.copy()
    result["estimated_mn_pct"] = np.round(estimates, 3)
    result["kriging_variance"] = np.round(variances, 4)
    result["tonnage_t"] = np.round(result["volume_m3"] * result["density"], 1)
    result["is_ore"] = (result["estimated_mn_pct"] >= mn_cutoff_pct).astype(int)

    summary = build_summary(result, mn_cutoff_pct)
    summary["variogram"] = {k: round(float(v), 4) for k, v in vparams.items()}

    result.to_csv(output_dir / "reserve_blocks.csv", index=False)
    with (output_dir / "reserve_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return result, summary


def main() -> None:
    result, summary = run_prism()
    print("PRISM Ordinary Kriging (synthetic DEMO-01 - not real MOIL data)")
    print(f"  Mn cutoff: {summary['mn_cutoff_pct']} %")
    print(f"  blocks: {summary['total_blocks']}")
    print(f"  ore / waste: {summary['ore_blocks']} / {summary['waste_blocks']}")
    print(f"  declared reserve: {summary['declared_reserve_t']} t")
    print(f"  average ore Mn: {summary['average_ore_mn_pct']} %")
    print(f"  estimated Mn min/max: {summary['min_estimated_mn_pct']} / {summary['max_estimated_mn_pct']}")
    print(f"  mean kriging variance: {summary['mean_kriging_variance']}")
    print(f"  wrote {OUTPUT_DIR / 'reserve_blocks.csv'}")
    print(f"  wrote {OUTPUT_DIR / 'reserve_summary.json'}")
    _ = result


if __name__ == "__main__":
    main()
