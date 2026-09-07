"""Generate SYNTHETIC demonstration datasets for OreSight (hackathon MVP).

All tables written to data/raw/ are synthetic. They are NOT real MOIL
(or any operator) data. No external APIs are used.

Re-run with the same SEED for identical CSVs.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
MINE_ID = "DEMO-01"
START_DATE = "2023-01-01"
END_DATE = "2025-12-31"

N_BOREHOLES = 80
NX, NY, NZ = 16, 14, 10  # 2240 blocks

X_MIN, X_MAX = 0.0, 800.0
Y_MIN, Y_MAX = 0.0, 600.0
Z_MIN, Z_MAX = 95.0, 245.0

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

EQUIPMENT = [
    ("SH-01", "shovel"),
    ("SH-02", "shovel"),
    ("DU-01", "dumper"),
    ("DU-02", "dumper"),
    ("DU-03", "dumper"),
    ("DU-04", "dumper"),
    ("DR-01", "drill"),
    ("LD-01", "loader"),
    ("DZ-01", "dozer"),
]


def monsoon_intensity(doy: np.ndarray) -> np.ndarray:
    """Indian monsoon-like seasonal intensity, peak ~ late July (doy 200)."""
    return np.exp(-0.5 * ((doy - 200.0) / 38.0) ** 2)


def ore_horizon_z(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Folded stratabound ore horizon (elevation in metres)."""
    return (
        168.0
        + 22.0 * np.sin(2 * np.pi * x / 420.0)
        + 12.0 * np.cos(2 * np.pi * y / 310.0)
        + 6.0 * np.sin(2 * np.pi * (x + 0.4 * y) / 580.0)
    )


def lateral_envelope(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Confine ore to a folded belt; not uniform across the mine."""
    axis_y = 280.0 + 90.0 * np.sin(2 * np.pi * x / 500.0)
    dist = np.abs(y - axis_y)
    return np.exp(-((dist / 115.0) ** 2))


def make_rbf_noise(rng: np.random.Generator, n_centers: int = 14):
    centers = np.column_stack(
        [
            rng.uniform(X_MIN, X_MAX, n_centers),
            rng.uniform(Y_MIN, Y_MAX, n_centers),
            rng.uniform(Z_MIN, Z_MAX, n_centers),
        ]
    )
    amps = rng.normal(0.0, 1.0, n_centers)
    scales = rng.uniform(80.0, 180.0, n_centers)

    def noise(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
        acc = np.zeros_like(x, dtype=float)
        for i in range(n_centers):
            dx = x - centers[i, 0]
            dy = y - centers[i, 1]
            dz = z - centers[i, 2]
            acc += amps[i] * np.exp(-(dx * dx + dy * dy + dz * dz) / (scales[i] ** 2))
        std = acc.std()
        if std < 1e-9:
            return acc
        return acc / std

    return noise


def manganese_field(
    x: np.ndarray, y: np.ndarray, z: np.ndarray, noise_fn
) -> np.ndarray:
    z_ore = ore_horizon_z(x, y)
    dvert = np.abs(z - z_ore)
    strat = np.exp(-((dvert / 14.0) ** 2))
    lat = lateral_envelope(x, y)
    spatial = noise_fn(x, y, z)
    mn = 3.8 + 34.0 * strat * lat * (1.0 + 0.18 * spatial)
    return np.clip(mn, 1.5, 48.0)


def gangue_from_mn(mn: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    fe = np.clip(16.5 - 0.18 * mn + rng.normal(0.0, 1.1, mn.shape), 2.0, 28.0)
    sio2 = np.clip(42.0 - 0.72 * mn + rng.normal(0.0, 1.6, mn.shape), 3.0, 55.0)
    total = mn + fe + sio2
    overflow = total > 92.0
    if np.any(overflow):
        scale = 92.0 / total[overflow]
        fe = fe.copy()
        sio2 = sio2.copy()
        fe[overflow] *= scale
        sio2[overflow] *= scale
    return fe, sio2


def density_from_grades(mn: np.ndarray, fe: np.ndarray) -> np.ndarray:
    return np.clip(2.62 + 0.028 * mn + 0.012 * fe, 2.55, 4.40)


def generate_boreholes(rng: np.random.Generator, noise_fn) -> pd.DataFrame:
    x = rng.uniform(X_MIN + 20, X_MAX - 20, N_BOREHOLES)
    y = rng.uniform(Y_MIN + 20, Y_MAX - 20, N_BOREHOLES)
    collar_z = 248.0 - 0.018 * x - 0.012 * y + rng.normal(0.0, 1.5, N_BOREHOLES)
    depth = rng.uniform(45.0, 125.0, N_BOREHOLES)

    mn_list, fe_list, si_list, den_list = [], [], [], []
    step = 2.0
    for i in range(N_BOREHOLES):
        n_samp = max(int(depth[i] // step), 8)
        zs = collar_z[i] - np.linspace(1.0, depth[i], n_samp)
        xs = np.full(n_samp, x[i])
        ys = np.full(n_samp, y[i])
        mn_s = manganese_field(xs, ys, zs, noise_fn)
        fe_s, si_s = gangue_from_mn(mn_s, rng)
        den_s = density_from_grades(mn_s, fe_s)
        # Length-weighted composite; ore-zone samples get extra weight
        z_ore = ore_horizon_z(xs, ys)
        w = np.exp(-((np.abs(zs - z_ore) / 18.0) ** 2))
        w = w / w.sum()
        mn_list.append(float(np.dot(w, mn_s)))
        fe_list.append(float(np.dot(w, fe_s)))
        si_list.append(float(np.dot(w, si_s)))
        den_list.append(float(np.dot(w, den_s)))

    return pd.DataFrame(
        {
            "hole_id": [f"BH-{i:03d}" for i in range(1, N_BOREHOLES + 1)],
            "x": np.round(x, 2),
            "y": np.round(y, 2),
            "collar_z": np.round(collar_z, 2),
            "depth": np.round(depth, 2),
            "Mn_pct": np.round(mn_list, 2),
            "Fe_pct": np.round(fe_list, 2),
            "SiO2_pct": np.round(si_list, 2),
            "density": np.round(den_list, 3),
        }
    )


def generate_blocks(rng: np.random.Generator, noise_fn) -> pd.DataFrame:
    xs = np.linspace(X_MIN + 25, X_MAX - 25, NX)
    ys = np.linspace(Y_MIN + 20, Y_MAX - 20, NY)
    zs = np.linspace(Z_MIN + 8, Z_MAX - 8, NZ)
    dx = float(xs[1] - xs[0])
    dy = float(ys[1] - ys[0])
    dz = float(zs[1] - zs[0])
    volume = dx * dy * dz

    xx, yy, zz = np.meshgrid(xs, ys, zs, indexing="ij")
    x = xx.ravel()
    y = yy.ravel()
    z = zz.ravel()
    n = x.size
    mn = manganese_field(x, y, z, noise_fn)
    fe, _ = gangue_from_mn(mn, rng)
    density = density_from_grades(mn, fe)

    return pd.DataFrame(
        {
            "block_id": [f"BLK-{i:04d}" for i in range(1, n + 1)],
            "mine_id": MINE_ID,
            "x": np.round(x, 2),
            "y": np.round(y, 2),
            "z": np.round(z, 2),
            "volume_m3": np.round(np.full(n, volume), 1),
            "density": np.round(density, 3),
        }
    )


def generate_weather(dates: pd.DatetimeIndex, rng: np.random.Generator) -> pd.DataFrame:
    doy = dates.dayofyear.to_numpy()
    mon = monsoon_intensity(doy)
    pre_monsoon = np.exp(-0.5 * ((doy - 140.0) / 22.0) ** 2) * 0.12
    winter_drizzle = np.exp(-0.5 * ((doy - 15.0) / 18.0) ** 2) * 0.05
    mean_rain = 2.0 + 28.0 * mon + 4.0 * pre_monsoon + 1.5 * winter_drizzle
    rainfall = rng.gamma(shape=1.15, scale=mean_rain / 1.15)
    dry = rng.random(len(dates)) > (0.18 + 0.62 * mon)
    rainfall = np.where(dry, rng.choice([0.0, 0.0, 0.0, 0.4], size=len(dates)), rainfall)
    rainfall = np.clip(rainfall, 0.0, 180.0)

    soil = np.zeros(len(dates))
    soil[0] = 0.22
    for t in range(1, len(dates)):
        wet = 1.0 - np.exp(-rainfall[t] / 18.0)
        soil[t] = np.clip(0.82 * soil[t - 1] + 0.22 * wet, 0.05, 0.98)

    ndvi = np.zeros(len(dates))
    ndvi[0] = 0.32
    for t in range(1, len(dates)):
        ndvi[t] = np.clip(0.90 * ndvi[t - 1] + 0.10 * (0.18 + 0.62 * soil[t]), 0.12, 0.82)

    # LST (°C): hot pre-monsoon, cooler monsoon and winter
    season = 33.0 + 8.5 * np.sin(2 * np.pi * (doy - 110) / 365.25)
    lst = season - 7.0 * mon - 2.5 * (rainfall / 40.0) + rng.normal(0.0, 1.4, len(dates))
    lst = np.clip(lst, 16.0, 46.0)

    return pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "mine_id": MINE_ID,
            "rainfall_mm": np.round(rainfall, 2),
            "soil_moisture": np.round(soil, 3),
            "NDVI": np.round(ndvi, 3),
            "LST": np.round(lst, 2),
        }
    )


def generate_equipment(
    dates: pd.DatetimeIndex, weather: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    rain = weather["rainfall_mm"].to_numpy()
    rows = []
    n = len(dates)
    for eq_id, eq_type in EQUIPMENT:
        base_down = {"shovel": 1.6, "dumper": 1.2, "drill": 1.8, "loader": 1.4, "dozer": 1.3}[
            eq_type
        ]
        fail_p = {"shovel": 0.04, "dumper": 0.05, "drill": 0.06, "loader": 0.045, "dozer": 0.04}[
            eq_type
        ]
        prev_fail = 0
        for i in range(n):
            rain_extra = 2.8 * (rain[i] / 25.0)
            p = np.clip(fail_p + 0.03 * (rain[i] > 20) + 0.08 * prev_fail, 0.01, 0.35)
            failure = int(rng.random() < p)
            repair = float(rng.uniform(1.5, 10.0) * failure)
            downtime = np.clip(
                rng.gamma(2.0, base_down / 2.0) + rain_extra + repair * 0.85,
                0.0,
                22.0,
            )
            if failure == 0:
                repair = 0.0
            availability = float(np.clip(1.0 - downtime / 24.0, 0.08, 1.0))
            prev_fail = failure
            rows.append(
                {
                    "date": dates[i].strftime("%Y-%m-%d"),
                    "mine_id": MINE_ID,
                    "equipment_id": eq_id,
                    "equipment_type": eq_type,
                    "downtime_h": round(float(downtime), 2),
                    "availability": round(availability, 3),
                    "failure": failure,
                    "repair_h": round(float(repair), 2),
                }
            )
    return pd.DataFrame(rows)


def generate_blast(
    dates: pd.DatetimeIndex, weather: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    rain = weather["rainfall_mm"].to_numpy()
    doy = dates.dayofyear.to_numpy()
    mon = monsoon_intensity(doy)
    blast_count = rng.poisson(lam=2.2 - 0.9 * mon)
    blast_count = np.clip(blast_count, 0, 6)
    delay = np.zeros(len(dates))
    reasons = []
    reason_pool_rain = np.array(["rainfall", "wet_holes", "ground_conditions"])
    reason_pool_dry = np.array(["misfire", "ventilation", "equipment", "ground_conditions"])
    for i in range(len(dates)):
        p_delay = 0.08 + 0.45 * (rain[i] > 15) + 0.15 * mon[i]
        if rng.random() < p_delay:
            delay[i] = float(np.clip(rng.gamma(2.0, 1.4) + 0.12 * rain[i], 0.3, 14.0))
            if rain[i] > 12:
                reasons.append(str(rng.choice(reason_pool_rain)))
            else:
                reasons.append(str(rng.choice(reason_pool_dry)))
        else:
            reasons.append("none")
    return pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "mine_id": MINE_ID,
            "blast_count": blast_count.astype(int),
            "delay_h": np.round(delay, 2),
            "delay_reason": reasons,
        }
    )


def generate_development(
    dates: pd.DatetimeIndex, weather: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    rain = weather["rainfall_mm"].to_numpy()
    doy = dates.dayofyear.to_numpy()
    mon = monsoon_intensity(doy)
    base = 18.0 * (1.0 - 0.35 * mon) * (1.0 - 0.25 * np.clip(rain / 40.0, 0, 1))
    development = np.clip(base + rng.normal(0.0, 1.8, len(dates)), 0.0, 32.0)
    return pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "mine_id": MINE_ID,
            "development_m": np.round(development, 2),
        }
    )


def generate_manpower(
    dates: pd.DatetimeIndex, weather: pd.DataFrame, rng: np.random.Generator
) -> pd.DataFrame:
    rain = weather["rainfall_mm"].to_numpy()
    doy = dates.dayofyear.to_numpy()
    mon = monsoon_intensity(doy)
    roster = 96
    available = roster - rng.integers(4, 14, len(dates))
    available = available - np.round(6 * mon + 4 * (rain > 25)).astype(int)
    available = np.clip(available, 55, roster)
    shifts = np.where(mon > 0.55, 2, 3)
    shifts = np.where((rain > 40) & (rng.random(len(dates)) < 0.25), np.maximum(shifts - 1, 1), shifts)
    return pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "mine_id": MINE_ID,
            "available_workers": available.astype(int),
            "shifts": shifts.astype(int),
        }
    )


def generate_production(
    dates: pd.DatetimeIndex,
    weather: pd.DataFrame,
    equipment: pd.DataFrame,
    blast: pd.DataFrame,
    development: pd.DataFrame,
    manpower: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    doy = dates.dayofyear.to_numpy()
    mon = monsoon_intensity(doy)
    rain = weather["rainfall_mm"].to_numpy()

    fleet = equipment.groupby("date", sort=False).agg(
        downtime_h=("downtime_h", "mean"),
        availability=("availability", "mean"),
    )
    fleet = fleet.reindex(dates.strftime("%Y-%m-%d"))

    planned = 2400.0 * (1.0 - 0.16 * mon) + rng.normal(0.0, 55.0, len(dates))
    planned = np.clip(planned, 1400.0, 2800.0)

    downtime = fleet["downtime_h"].to_numpy()
    avail = fleet["availability"].to_numpy()
    delay = blast["delay_h"].to_numpy()
    dev = development["development_m"].to_numpy()
    workers = manpower["available_workers"].to_numpy().astype(float)
    n_shifts = manpower["shifts"].to_numpy().astype(float)

    rain_f = np.clip(1.0 - rain / 55.0, 0.35, 1.0)
    down_f = np.clip(1.0 - downtime / 10.0, 0.30, 1.0)
    delay_f = np.clip(1.0 - delay / 9.0, 0.40, 1.0)
    dev_f = np.clip(dev / 18.0, 0.40, 1.15)
    man_f = np.clip(workers / 90.0, 0.55, 1.10)
    shift_f = np.clip(n_shifts / 3.0, 0.55, 1.0)

    actual = planned * (
        0.22
        + 0.18 * avail
        + 0.16 * down_f
        + 0.16 * rain_f
        + 0.10 * delay_f
        + 0.08 * dev_f
        + 0.06 * man_f
        + 0.04 * shift_f
    )
    actual = actual * (1.0 + rng.normal(0.0, 0.035, len(dates)))
    actual = np.clip(actual, 200.0, planned * 1.08)

    # Head grade: slightly lower in monsoon (dilution / wet handling)
    avg_mn = np.clip(31.5 - 2.2 * mon + rng.normal(0.0, 0.85, len(dates)), 18.0, 42.0)

    return pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m-%d"),
            "mine_id": MINE_ID,
            "planned_t": np.round(planned, 1),
            "actual_t": np.round(actual, 1),
            "avg_mn_pct": np.round(avg_mn, 2),
        }
    )


def print_summary(tables: dict[str, pd.DataFrame]) -> None:
    print("=" * 64)
    print("OreSight SYNTHETIC demonstration data (NOT real MOIL data)")
    print(f"mine_id={MINE_ID}  seed={SEED}")
    print("=" * 64)
    for name, df in tables.items():
        print(f"\n{name}: {len(df)} rows, {df.shape[1]} columns")
        print(f"  missing values: {int(df.isna().sum().sum())}")
        if "date" in df.columns:
            print(f"  date range: {df['date'].min()} -> {df['date'].max()}")
        print("  dtypes:")
        for col, dt in df.dtypes.items():
            print(f"    {col}: {dt}")
        num = df.select_dtypes(include=[np.number])
        if not num.empty:
            print(num.describe().round(3).to_string())

    prod = tables["production.csv"]
    weather = tables["weather.csv"]
    equipment = tables["equipment.csv"]
    daily_down = equipment.groupby("date")["downtime_h"].mean()
    merged = prod.merge(weather, on=["date", "mine_id"]).set_index("date")
    merged = merged.join(daily_down.rename("mean_downtime_h"))
    r_rain = merged["rainfall_mm"].corr(merged["actual_t"])
    r_down = merged["mean_downtime_h"].corr(merged["actual_t"])
    print("\nCorrelations with actual production (t):")
    print(f"  rainfall_mm vs actual_t:          {r_rain:.3f}")
    print(f"  mean equipment downtime vs actual_t: {r_down:.3f}")
    print("=" * 64)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    noise_fn = make_rbf_noise(rng)

    dates = pd.date_range(START_DATE, END_DATE, freq="D")

    boreholes = generate_boreholes(rng, noise_fn)
    blocks = generate_blocks(rng, noise_fn)
    weather = generate_weather(dates, rng)
    equipment = generate_equipment(dates, weather, rng)
    blast = generate_blast(dates, weather, rng)
    development = generate_development(dates, weather, rng)
    manpower = generate_manpower(dates, weather, rng)
    production = generate_production(
        dates, weather, equipment, blast, development, manpower, rng
    )

    tables = {
        "boreholes.csv": boreholes,
        "blocks.csv": blocks,
        "production.csv": production,
        "equipment.csv": equipment,
        "blast.csv": blast,
        "development.csv": development,
        "manpower.csv": manpower,
        "weather.csv": weather,
    }
    for name, df in tables.items():
        path = RAW / name
        df.to_csv(path, index=False)
        print(f"wrote {path}")

    print_summary(tables)


if __name__ == "__main__":
    main()
