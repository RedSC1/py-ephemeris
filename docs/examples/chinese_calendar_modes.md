# Chinese-calendar modes at a new moon

Script: [`examples/chinese_calendar_modes.py`](../../examples/chinese_calendar_modes.py)

```bash
python examples/chinese_calendar_modes.py
```

The selected new moon occurs at 2026-08-12 17:36:45 UT, which is shortly
after 01:36 on August 13 in Beijing but shortly after 23:06 on August 12 in
India. At 17:40 UT the example demonstrates:

- Beijing is lunar month 7, day 1.
- Both China-standard modes map India's local August 12 to lunar month 6,
  day 30.
- Local astronomical mode assigns the new moon to India's August 12 and
  therefore returns lunar month 7, day 1.

It also queries 23-12-02 under the historical profile and prints the preserved
alternate-twelve month name. This confirms that choosing a non-China local
offset does not disable historical month naming.
