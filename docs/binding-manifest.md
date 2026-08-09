# Binding manifest

This is the concrete migration checklist derived from the public high-level
services in the archived `taiyin-python` package. It lists calculation
entrypoints, not ctypes allocation helpers, struct readers/writers, enum
properties, or private validation helpers.

The legacy facade has **about 223 calculation/configuration methods**: **203
base-package methods** and **20 optional BaZi methods**. Many paired `*_tt`,
`*_ut1`, `*_utc`, and batch methods will share one C++ implementation and one
Python result type, but they remain individually listed so compatibility
choices are explicit.

## Foundation and runtime (43)

| Service | Bindings to provide |
| --- | --- |
| `Ephemeris` / runtime (21) | `add_source_path`, `load_eop_table`, `load_builtin_eop_table`, `clear_eop_table`, `has_eop_table`, `load_lunar_limb_model`, `clear_lunar_limb_model`, `has_lunar_limb_model`, `clear_ephemeris_cache`, `catalog_size`, `cache_entry_count`, `format_ephemeris_diagnostic`, `create_context`, `clone_context`, `register_custom_ayanamsha_model`, `register_custom_house_system_model`, `clear_custom_ayanamsha_models`, `clear_custom_house_system_models`, `register_builtin_astrology_targets`, `register_custom_target`, `clear_custom_targets` |
| `Time` (22) | `julian_day`, `reverse_julian_day`, `set_policy`, `set_tdb_model`, `set_delta_t_model`, `decimal_year`, `julian_centuries_since_j2000`, `julian_millennia_since_j2000`, `estimated_delta_t_for_decimal_year`, `estimated_delta_t_from_ut1`, `estimated_delta_t_from_tt`, `tt_to_tdb`, `tdb_to_tt`, `tai_minus_utc`, `utc_to_tai`, `tai_to_tt`, `utc_to_tt`, `utc_to_ut1`, `delta_t`, `tt_to_ut1`, `ut1_to_tt`, `precise_scales_from_utc` |

Value types bound alongside them: `JulianDate`, `AstroDateTime`, `Vector3`,
`CartesianState`, observer/atmosphere/configuration types, diagnostics, and
the associated enums/flags. These are ordinary pybind value bindings, not
separate C ABI calls.

## Ordinary astronomy services (82)

| Service | Bindings to provide |
| --- | --- |
| `Position` (9) | `at_tt`, `at_ut1`, `at_tdb`, `at_ut1_with_delta_t`, `at_utc`, `batch_at_tt`, `batch_at_ut1`, `state_at_tt`, `state_at_ut1` |
| `Observed` (4) | `at_ut1`, `at_utc`, `batch_at_ut1`, `batch_at_utc` |
| `SolarTime` (4) | `equation_of_time_at_ut1`, `equation_of_time_at_tt`, `mean_to_apparent`, `apparent_to_mean` |
| `Phenomena` (2) | `at_tt`, `at_ut1` |
| `Star` (10) | `at_tdb`, `at_tt`, `at_ut1`, `at_ut1_with_delta_t`, `batch_at_tdb`, `batch_at_tt`, `batch_at_ut1`, `batch_at_ut1_with_delta_t`, `observed_at_ut1`, `observed_batch_at_ut1` |
| `Visibility` (11) | `moon_rise_set_at_ut1`, `moon_transit_at_ut1`, `planet_rise_set_at_ut1`, `planet_transit_at_ut1`, `solar_rise_set_at_ut1`, `solar_twilight_at_ut1`, `solar_transit_at_ut1`, `solar_rise_set_fast_at_tt`, `solar_transit_fast_at_tt`, `star_rise_set_at_ut1`, `star_transit_at_ut1` |
| `Heliacal` (4) | `body_at_ut1`, `star_at_ut1`, `next_body_event_at_ut1`, `next_star_event_at_ut1` |
| `Orbital` (8) | `osculating_at_tt`, `osculating_at_ut1`, `reference_points_at_tt`, `reference_points_at_ut1`, `search_apsis_from_tt`, `search_apsis_from_ut1`, `search_plane_node_from_tt`, `search_plane_node_from_ut1` |
| `Occultation` (8) | `next_geocentric_star_at_ut1`, `next_local_star_at_ut1`, `next_geocentric_body_at_ut1`, `next_local_body_at_ut1`, `local_star_visibility_at_ut1`, `local_body_visibility_at_ut1`, `star_where_at_ut1`, `body_where_at_ut1` |
| `Events` (22) | `recommended_longitude_search_step_days`, `recommended_aspect_search_step_days`, `solar_longitude_at_ut1`, `solar_longitude_at_tt`, `moon_longitude_at_ut1`, `moon_longitude_at_tt`, `longitude_crossings_at_ut1`, `longitude_crossings_at_tt`, `longitude_stations_at_ut1`, `longitude_stations_at_tt`, `aspect_crossings_at_ut1`, `aspect_crossings_at_tt`, `exact_aspects_at_ut1`, `exact_aspects_at_tt`, `greatest_elongation_at_ut1`, `minimum_angular_separation_at_ut1`, `minimum_angular_separation_at_tt`, `next_solar_transit_at_ut1`, `local_solar_transit_at_ut1`, `next_local_solar_transit_at_ut1`, `lunar_phase_crossings_at_ut1`, `lunar_phase_crossings_at_tt` |

## Astrology and eclipses (59)

| Service | Bindings to provide |
| --- | --- |
| `Astrology` (21) | `ayanamsha_at_tt`, `sidereal_position_at_tt`, `sidereal_position_at_ut1`, `sidereal_coordinates_at_tt`, `sidereal_coordinates_at_ut1`, `lunar_true_node_at_tt`, `lunar_true_node_at_ut1`, `lunar_mean_node_at_tt`, `lunar_mean_node_at_ut1`, `lunar_mean_apogee_at_tt`, `lunar_mean_apogee_at_ut1`, `lunar_osculating_apogee_at_tt`, `lunar_osculating_apogee_at_ut1`, `lunar_fitted_apogee_at_tt`, `lunar_fitted_apogee_at_ut1`, `houses_from_armc`, `houses_at_ut1`, `houses_at_tt`, `house_position_of`, `has_ayanamsha_model`, `has_house_system_model` |
| `Eclipse` (38) | `solve_lunar_at_tt`, `solve_lunar_at_ut1`, `next_lunar_at_tt`, `next_lunar_at_ut1`, `lunar_eclipses_at_tt`, `lunar_eclipses_at_ut1`, `local_lunar_visibility_at_tt`, `local_lunar_visibility_at_ut1`, `next_local_lunar_at_tt`, `next_local_lunar_at_ut1`, `solve_solar_at_tt`, `solve_solar_at_ut1`, `next_solar_at_tt`, `next_solar_at_ut1`, `solar_eclipses_at_tt`, `solar_eclipses_at_ut1`, `solve_local_solar_at_tt`, `solve_local_solar_at_ut1`, `next_local_solar_at_tt`, `next_local_solar_at_ut1`, `local_solar_circumstances_at_tt`, `local_solar_circumstances_at_ut1`, `solar_besselian_elements_at_tt`, `solar_besselian_polynomial_at_tt`, `evaluate_solar_besselian_polynomial`, `solar_eclipse_route_row_at_tt`, `solar_eclipse_route_row_at_ut1`, `solar_eclipse_route_at_tt`, `solar_eclipse_route_at_ut1`, `solar_eclipse_route_curves_at_tt`, `solar_eclipse_route_curves_at_ut1`, `solar_eclipse_route_product_at_tt`, `solar_eclipse_route_product_at_ut1`, `solar_eclipse_route_map_product_at_tt`, `solar_eclipse_route_map_product_at_ut1`, `local_solar_eclipse_boundary_at_tt`, `local_solar_eclipse_boundary_at_ut1` |

## Chinese calendar and Ganzhi (19)

| Service | Bindings to provide |
| --- | --- |
| `ChineseCalendarContext` (12) | `calc_year_ut`, `get_specific_jie_qi_ut`, `get_prev_jie_qi_ut`, `get_next_jie_qi_ut`, `get_prev_jie_ut`, `get_next_jie_ut`, `get_prev_qi_ut`, `get_next_qi_ut`, `from_solar`, `from_lunar`, `get_month_days`, `four_pillars` |
| `Ganzhi` (7) | `make`, `advance`, `month_pillar`, `hour_pillar`, `day_pillar`, `nayin_element`, `nayin_id` |

`ChineseCalendarContext` and Ganzhi remain in the base `taiyin` package. A
future `Ephemeris.create_bazi(...)` facade will use the calendar context
internally rather than requiring callers to pass native pointers across Python
extension modules.

## Optional BaZi package (20)

| Service | Bindings to provide |
| --- | --- |
| `BaziContext` | `get_kong_wang`, `get_ten_god`, `get_hidden_stems`, `calc_stem_relation`, `calc_branch_relation`, `calc_branch_triple_relation`, `get_life_stage`, `calc_liunian`, `calc_liuyue`, `calc_liuri`, `calc_liushi`, `calc_chart`, `calc_xiaoyun`, `fill_xiaoyun`, `calc_qiyun`, `fill_dayun`, `calc_renyuan_siling`, `get_renyuan_siling_segments`, `collect_chart_relations`, `collect_target_shen_sha` |

BaZi has no Python callback registry. Its two operations that need calendar
information (`calc_qiyun`, `calc_renyuan_siling`) will stay behind the base
package facade rather than leak a raw `ChineseCalendarContext*` boundary.

## Already implemented in the first native slice

- Public `Ephemeris`, `EphemerisContext`, and `JulianDate` foundations;
  runtime initialization, source-path addition, cache statistics and context
  creation.
- All nine legacy `PositionApi` entrypoint shapes: TT, UT1, TDB, UTC, explicit
  Delta-T, TT/UT1 batch position, and TT/UT1/TDB state calculations. They
  currently return native numeric vectors/dicts; the full typed result and
  diagnostic objects are the next part of the position-service port.
- Custom target, ayanamsha and house-system registration objects.
- `ayanamsha_at_tt` and `houses_from_armc`, currently kept as native
  verification entrypoints while the public astrology facade is ported.
- `EphemerisContext.chinese_calendar` and `create_chinese_calendar()` with
  the old cached-parent shape, Chinese-calendar configuration profiles, and a
  direct `four_pillars()` binding. Its numeric regression passes a manually
  supplied source-tree OPM2 path through `Ephemeris(source_paths=[...])`;
  automatic data-package discovery is deliberately deferred.

The next implementation step should turn the foundation list into public
`taiyin.Ephemeris` / `taiyin.EphemerisContext` classes, then port position and
time services before expanding the search-heavy APIs.
