# Changelog

## 1.0.0b5

- Separate the caller's fixed civil-clock UTC offset from a mean-solar
  meridian used to assign new moons and solar terms to calendar days.
- Let BaZi and Ziwei local/instant conveniences retain the configured legal
  clock while a local astronomical calendar is rebuilt at another meridian.

## 1.0.0b4

- Update the pinned native core to Taiyin 1.0.0-beta.4 and C ABI 10.
- Add the three explicit Chinese-calendar policies: historical China,
  standard China, and locally reconstructed astronomical calendars.
- Preserve historical month identity and corrected month-building metadata in
  Ziwei flow resolution, including reform-year and leap-month boundaries.
- Expose Ziwei flow-month physical sequence, effective month, written month
  name, and palace-month strategy separately so leap-month schools can choose
  their palace rule without changing calendar facts.
- Canonicalize only the final civil/mean-solar/apparent-solar chart clock at
  exact floating-point hour boundaries; physical UTC and general astronomy
  time conversions remain unchanged.
- Keep Ziwei natal and flow calculations aligned with the selected virtual
  clock and Rat-hour policy.

## 1.0.0b3

- Update the native baseline to Taiyin 1.0.0-beta.3.
- Ship the base, BaZi, and Ziwei distributions as separate wheels from one
  repository.
