/**
 * Human-readable label mapping for SHAP feature names.
 * Raw model feature names → plain language for mine managers.
 */
export const FEATURE_LABELS = {
  planned_t:                    null,           // exclude — planning input, not a driver
  fleet_availability:           'Fleet availability',
  development_m:                'Development progress',
  delay_h:                      'Blast scheduling delays',
  fleet_downtime_h:             'Equipment downtime',
  fleet_failures:               'Equipment failures',
  fleet_repair_h:               'Repair time',
  available_workers:            'Workforce availability',
  shifts:                       'Scheduled shifts',
  blast_count:                  'Blast activity',
  blast_delay_indicator:        'Blast delay occurrence',
  rainfall_mm:                  'Rainfall',
  soil_moisture:                'Soil moisture',
  NDVI:                         'Vegetation index',
  LST:                          'Site temperature',
  day_of_year:                  'Seasonal position',
  day_of_week:                  'Day of week',
  month:                        'Month',
  quarter:                      'Quarter',
  day_of_month:                 'Day of month',
  actual_t_lag_1:               'Yesterday\'s production',
  actual_t_lag_2:               'Production 2 days ago',
  actual_t_lag_3:               'Production 3 days ago',
  actual_t_lag_7:               'Production last week',
  actual_t_lag_14:              'Production 2 weeks ago',
  actual_t_lag_30:              'Production 30 days ago',
  actual_t_rolling_mean_7:      '7-day production trend',
  actual_t_rolling_mean_14:     '14-day production trend',
  actual_t_rolling_mean_30:     '30-day production trend',
  actual_t_rolling_std_7:       'Recent production variability (7d)',
  actual_t_rolling_std_14:      'Recent production variability (14d)',
  actual_t_rolling_std_30:      'Production variability (30d)',
  fleet_availability_rolling_mean_7:  'Fleet availability trend (7d)',
  fleet_availability_rolling_mean_14: 'Fleet availability trend (14d)',
  fleet_availability_rolling_mean_30: 'Fleet availability trend (30d)',
  rainfall_rolling_sum_7:       'Cumulative rainfall (7d)',
  rainfall_rolling_sum_14:      'Cumulative rainfall (14d)',
  rainfall_rolling_sum_30:      'Cumulative rainfall (30d)',
}

/** Return human label or null if feature should be excluded. */
export function featureLabel(name) {
  if (name in FEATURE_LABELS) return FEATURE_LABELS[name]
  return name  // fallback: return raw name if not in map
}

/** Format a nudge candidate feature value with correct units. */
export function formatFeatureValue(feature, value) {
  const v = Number(value)
  switch (feature) {
    case 'fleet_availability':    return `${(v * 100).toFixed(1)}%`
    case 'fleet_downtime_h':      return `${v.toFixed(1)} h/day`
    case 'development_m':         return `${v.toFixed(1)} m/day`
    case 'available_workers':     return `${Math.round(v)} persons`
    default:                      return v.toFixed(2)
  }
}

/** Format tonnes with thousand-separator, 0 decimals. */
export function fmtT(v) {
  return Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

/** Format a probability as percentage with 1 decimal. */
export function fmtPct(v) {
  return (Number(v) * 100).toFixed(1) + '%'
}
