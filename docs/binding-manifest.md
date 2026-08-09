# Binding manifest

This is the concrete migration checklist derived from the public high-level
services in the archived `taiyin-python` package. It lists calculation
entrypoints, not ctypes allocation helpers, struct readers/writers, enum
properties, or private validation helpers.

The legacy facade has **about 222 calculation/configuration methods**: **202
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

## Astrology and eclipses (58)

| Service | Bindings to provide |
| --- | --- |
| `Astrology` (21) | `ayanamsha_at_tt`, `sidereal_position_at_tt`, `sidereal_position_at_ut1`, `sidereal_coordinates_at_tt`, `sidereal_coordinates_at_ut1`, `lunar_true_node_at_tt`, `lunar_true_node_at_ut1`, `lunar_mean_node_at_tt`, `lunar_mean_node_at_ut1`, `lunar_mean_apogee_at_tt`, `lunar_mean_apogee_at_ut1`, `lunar_osculating_apogee_at_tt`, `lunar_osculating_apogee_at_ut1`, `lunar_fitted_apogee_at_tt`, `lunar_fitted_apogee_at_ut1`, `houses_from_armc`, `houses_at_ut1`, `houses_at_tt`, `house_position_of`, `has_ayanamsha_model`, `has_house_system_model` |
| `Eclipse` (37) | `solve_lunar_at_tt`, `solve_lunar_at_ut1`, `next_lunar_at_tt`, `next_lunar_at_ut1`, `lunar_eclipses_at_tt`, `lunar_eclipses_at_ut1`, `local_lunar_visibility_at_tt`, `local_lunar_visibility_at_ut1`, `next_local_lunar_at_tt`, `next_local_lunar_at_ut1`, `solve_solar_at_tt`, `solve_solar_at_ut1`, `next_solar_at_tt`, `next_solar_at_ut1`, `solar_eclipses_at_tt`, `solar_eclipses_at_ut1`, `solve_local_solar_at_tt`, `solve_local_solar_at_ut1`, `next_local_solar_at_tt`, `next_local_solar_at_ut1`, `local_solar_circumstances_at_tt`, `local_solar_circumstances_at_ut1`, `solar_besselian_elements_at_tt`, `solar_besselian_polynomial_at_tt`, `evaluate_solar_besselian_polynomial`, `solar_eclipse_route_row_at_tt`, `solar_eclipse_route_row_at_ut1`, `solar_eclipse_route_at_tt`, `solar_eclipse_route_at_ut1`, `solar_eclipse_route_curves_at_tt`, `solar_eclipse_route_curves_at_ut1`, `solar_eclipse_route_product_at_tt`, `solar_eclipse_route_product_at_ut1`, `solar_eclipse_route_map_product_at_tt`, `solar_eclipse_route_map_product_at_ut1`, `local_solar_eclipse_boundary_at_tt`, `local_solar_eclipse_boundary_at_ut1` |

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

## Implemented so far

- Public `Ephemeris`, `EphemerisContext`, and `JulianDate` foundations;
  runtime initialization, source-path addition, cache statistics and context
  creation. Runtime construction and mutation cover explicit EOP and TLL1
  lunar-limb paths, built-in EOP loading, clearing, and availability queries.
- All nine legacy `PositionApi` entrypoint shapes: TT, UT1, TDB, UTC, explicit
  Delta-T, TT/UT1 batch position, and TT/UT1/TDB state calculations, returning
  typed `EphemerisResult`, `Position`, `CartesianState`, and route diagnostics.
- The complete four-method `SolarTimeApi`: equation of time from UT1/TT and
  local mean/apparent solar-time conversion, including legacy regression cases
  and C++ multi-epoch Swiss-oracle coverage.
- The complete 22-entry `EventsApi`: longitude, station, aspect, lunar-phase,
  greatest-elongation, minimum-separation, and global/local solar-transit
  searches. Its test suite ports the legacy cases and the matching C++ OPM2
  event-search oracles.
- The complete 11-entry `VisibilityApi`: Moon, planet, Sun, and catalogued-star
  rise/set and transit searches, twilight, plus fast TT solar routes. Its
  regression suite covers configured-observer paths, direct-observer fast
  paths, custom horizons, and input validation.
- The complete two-entry `PhenomenaApi`, with typed phase, illumination,
  angular-size, brightness, and lunar-parallax results at TT and UT1.
- The complete four-entry `ObservedApi`: UT1/UTC single and batch routes with
  geometric/apparent Cartesian states, diagnostics, horizontal coordinates,
  rates, and refracted output.
- The complete ten-entry `StarApi` plus process-wide `StarCatalog`: TSC1 file
  and memory loading, TSF1 loading, aliases/magnitude lookup, four time routes,
  matching batches with partial-failure diagnostics, and observed stars.
- The complete four-entry `HeliacalApi`: instant body/star visibility and
  bounded body/star morning/evening event searches with measured conditions.
- The complete eight-entry `OrbitalApi`: osculating elements, instantaneous
  reference points, and forward/reverse apsis and plane-node searches in TT
  and UT1, including every supported reference frame and barycenter policy.
- The complete eight-entry `OccultationApi`: geocentric/local star and body
  searches, optional body radii, local visibility, and global path/visible-
  region products with defensive validation of native fixed-array counts.
- The complete 37-entry `EclipseApi`: global lunar/solar solve, next and
  interval searches in TT and UT1; local visibility and circumstances;
  Besselian elements and polynomial fitting/evaluation; solar route rows,
  curves, core/map polygon products, and local shadow boundaries. Regression
  coverage includes known 2024/2025 eclipses, TT/UT1 agreement, observer
  visibility, antimeridian products, and route input validation.
- Time calendar/JD conversion, TT/TDB, UTC/TAI/TT/UT1 conversion, Delta-T,
  leap-second lookup, and explicit precise/estimated time-scale aggregates.
- Custom target, ayanamsha and house-system registration objects.
- The complete 21-entry `AstrologyApi`: ayanamshas, typed sidereal position
  and generic coordinates, true/mean nodes, all three lunar-apogee
  conventions, and house-system calculations. Its regressions include the
  relevant legacy API shapes plus fixed C++ Swiss house-oracle cases.
- `EphemerisContext.chinese_calendar` and `create_chinese_calendar()` with
  the old cached-parent shape, Chinese-calendar configuration profiles, and a
  direct `four_pillars()` binding. Numeric regressions select the source-tree
  `600y` OPM2 fixture for stable oracles, while a separate integration test
  passes the complete `data_root` and exercises OPC-backed package discovery.
- `ChineseCalendarContext.from_solar`, `from_lunar`, and `get_month_days`,
  returning the old package's `SolarDate` / `LunarDate` value shapes. The
  regression uses the matching 2025/2026 C++ calendar oracles.

The remaining work is concentrated in unported runtime/configuration controls,
then the optional BaZi package facade.
