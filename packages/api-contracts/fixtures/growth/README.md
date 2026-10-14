# Growth metric test vectors

Shared by `apps/mobile` (Dart) and `services/api` (Python) so both deterministic
implementations produce identical numbers. Compare with an absolute tolerance of `1e-6`.

Semantics (records are sorted by `measured_at` ascending first; timestamps are ISO-8601 and
compared as absolute instants):

| field | definition |
|---|---|
| `count` | number of records in the window |
| `latest_grams` / `first_grams` | weight of last / first record |
| `previous_grams` | weight of the second-to-last record, `null` if `count < 2` |
| `change_since_previous_grams` | `latest - previous` |
| `percent_change_since_previous` | `(latest - previous) / previous * 100` |
| `total_change_grams` | `latest - first`, `null` if `count < 2` |
| `span_days` | `(latest_at - first_at)` in fractional days |
| `avg_daily_change_grams` | `total_change / span_days`, `null` if `span_days < 1` |
| `avg_weekly_change_grams` | `avg_daily_change * 7` |
| `max_grams` / `max_at` | historical maximum (earliest record wins ties) |
| `is_losing_weight` | `change_since_previous < 0` |

Average rates describe the endpoints only — growth is not assumed to be linear.
