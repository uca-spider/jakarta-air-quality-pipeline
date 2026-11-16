# Data inventory: Jakarta ISPU files

Profiled on 8 Nov 2026 (initial 5 files) and updated on 16 Nov 2026 from nine downloaded files spanning 2016 through 2025. Everything marked **observed** was measured directly on the files. Everything marked **inferred** is a conclusion drawn from the data and must be confirmed against the publisher's documentation. Add more years as they are inspected.

## Files

| Period / File | Real format | Rows | Columns | Expected rows | Layout Type |
|---------------|-------------|------|---------|---------------|-------------|
| 2016 | HTML table | 1,830 | 11 | 1,830 (5 stations x 366, leap year) | Layout A |
| 2017 | HTML table | 1,825 | 11 | 1,825 (5 stations x 365) | Layout A |
| 2018 | HTML table | 1,825 | 11 | 1,825 | Layout A |
| 2019 | HTML table | 345 | 11 | 1,825 (observed: 345, 1 station/day) | Layout B (variant without PM2.5) |
| 2020 | HTML table | 1,830 | 11 | 1,830 (5 stations x 366, leap year) | Layout A |
| 2021 | HTML table | 1,825 | 12 | 1,825 | Layout A + PM2.5 |
| 2022 | HTML table | 365 | 12 | 1,825 (observed: 365, 1 station/day) | Layout B |
| 2023 | HTML table | 1,825 | 12 | 1,825 | Layout C |
| 2024–2025 (multi-month) | HTML table | 3,501 | 13 | ~3,500 (23 months x ~150-155) | Layout C + `bulan` |

**Observed:** all files have an `.xls` extension but contain an HTML `<table>`, not an Excel workbook. `pandas.read_excel` cannot read them; `pandas.read_html` (with `lxml`) can. Every HTML row has the same number of cells as the header, so the shifted rows described below are in the source data, not a parsing artifact. File-type detection must look at the content, not the extension.

## Column layouts

| Meaning | Layout A (2016, 2017, 2018, 2020) | Layout A + PM2.5 (2021) | Layout B variant (2019) | Layout B (2022) | Layout C (2023) | Layout C + `bulan` (2024–2025) |
|---------|-----------------------------------|-------------------------|-------------------------|-----------------|-----------------|--------------------------------|
| Period (YYYYMM) | `periode_data` | `periode_data` | `periode_data` | `periode_data` | `periode_data` | `periode_data` |
| Month (1-12) | (no column) | (no column) | (no column) | (no column) | (no column) | `bulan` |
| Date | `tanggal` | `tanggal` | `tanggal` | `tanggal` | `tanggal` | `tanggal` (day of month: 1-31) |
| Station | `stasiun` (col 3) | `stasiun` (col 3) | `lokasi_spku` (last col) | `lokasi_spku` (last col) | `stasiun` (col 3) | `stasiun` (col 4) |
| PM10 | `pm10` | `pm10` | `pm10` | `pm_10` | `pm_sepuluh` | `pm_sepuluh` |
| PM2.5 | (no column) | `pm25` | (no column) | `pm_duakomalima` | `pm_duakomalima` | `pm_duakomalima` |
| SO2 | `so2` | `so2` | `so2` | `so2` | `sulfur_dioksida` | `sulfur_dioksida` |
| CO | `co` | `co` | `co` | `co` | `karbon_monoksida` | `karbon_monoksida` |
| O3 | `o3` | `o3` | `o3` | `o3` | `ozon` | `ozon` |
| NO2 | `no2` | `no2` | `no2` | `no2` | `nitrogen_dioksida` | `nitrogen_dioksida` |
| Index value | `max` | `max` | `max` | `max` | `max` | `max` |
| Critical parameter | `critical` | `critical` | `critical` | `critical` | `parameter_pencemar_kritis` | `parameter_pencemar_kritis` |
| Category | `categori` | `categori` | `categori` | `categori` | `kategori` | `kategori` |

## Value conventions by file

| Topic | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024–2025 |
|-------|------|------|------|------|------|------|------|------|-----------|
| Date format (observed) | ISO (1,754), `dd/mm/yyyy` (76 in Dec) | ISO | `dd/mm/yyyy` | ISO | ISO, plus `dd/mm/yyyy` in Nov, plus swapped day/month | ISO | ISO, plus one Excel serial number | ISO | Day-of-month integer (`1`–`31`) |
| Missing marker (observed) | `---` | `---` | `---` and empty | none seen | `---` and empty | `---` and empty in `pm25` | none seen | `-` (and a few `---`) | `NULL`, `N/A`, `---` |
| Station naming style (observed) | `DKI5 (KEBON JERUK) JAKARTA BARAT` | `DKI5 (KEBON JERUK)` | `DKI5 (KEBON JERUK) JAKARTA BARAT` | Code only (`DKI1`–`DKI5`) | `DKI5 (KEBON JERUK) JAKARTA BARAT` | `DKI5 (KEBON JERUK) JAKARTA BARAT` | Code only | `... JAKARTA BARAT` then `DKI5 KEBON JERUK` | Mixed (`BUNDARAN HOTEL INDONESIA (HI)`, `BUNDERAN HI`, `DKI5 KEBON JERUK`) |
| Critical labels (observed) | `O3`, `PM10`, `CO`, `SO2`, `NO2` | same | same | `O3`, `PM10` | same plus `PM25` | `PM25`, `PM10`, `O3`, `CO`, `SO2`, plus 1 `'BAIK'` | `PM2,5`, `O3`, `SO2` | `PM25`, `PM10`, `SO2`, `O3` | `PM25`, `SO2`, `PM10`, `O3`, `NO2`, `CO`, `N/A`, `NULL` |
| Rows with category `TIDAK ADA DATA` | 37 | 30 | 34 | 0 | 16 | 16 | 0 | 21 | 20 |

## Findings per file

### 2016 (clean, leap year)
- Exactly 1,830 rows (5 stations x 366 days); 366 distinct days per station; no duplicates (observed).
- 76 rows in late December use `dd/mm/yyyy` format, while the rest use standard ISO `YYYY-MM-DD` (observed).
- 37 rows have empty `critical` and `max=0` with category `TIDAK ADA DATA` (observed).
- Missing values in pollutant columns are consistently marked with `---`.

### 2017 (cleanest baseline)
- 365 distinct days for each of the five stations; no duplicate (date, station) pairs; all dates match `periode_data` (observed).
- `max` equals the highest component in all 1,534 rows where every component is present (observed).
- 30 rows have an empty `critical` and the category `TIDAK ADA DATA` (observed).
- Only issue: `---` as the missing marker (for example `pm10`: 115 rows).

### 2018
- **Shifted columns in April 2018 (observed).** 147 of the 150 April rows have a numeric code in `critical` and a pollutant name in `categori`. The real category (`BAIK`, `SEDANG`, ...) is missing for those rows.
- **Code meaning (inferred).** In those rows the code and name pair up one to one: `1` = PM10 (64 rows), `2` = SO2 (5), `3` = CO (2), `4` = O3 (76).
- `max` equals the highest component in all 1,598 complete rows; 365 days per station; no duplicates (observed).

### 2019 (daily summary layout)
- **Only 345 rows against 1,825 expected (observed).** Zero duplicate dates. Each calendar date appears at most once, with station codes varying by day: `DKI5` (147 rows), `DKI3` (119), `DKI4` (34), `DKI2` (33), `DKI1` (12).
- 20 calendar days are missing completely (e.g. May only has 12 rows).
- Layout puts station code at the end as `lokasi_spku` without PM2.5 (observed).
- Dates are 100% clean ISO `YYYY-MM-DD`.

### 2020 (most damaged)
- **March: station missing and columns shifted (observed).** All 155 March rows (5 stations x 31 days) have a number in the `stasiun` column. The values are shifted one column to the left: `stasiun` holds the PM10 value, `max` holds a numeric code, and `critical` holds the pollutant name. The station is not recoverable from the row itself.
- **June: date stuck on one value (observed).** The date `2020-06-06` appears on 121 rows. For DKI2, DKI3 and DKI4 each station has only one distinct date in June, and DKI1 has six. The rows have different values, so they are distinct observations with a wrong date, not duplicates.
- **November: three date formats (observed).** 90 rows use `dd/mm/yyyy` (days 13 to 30). The early days are written as year-day-month in ISO form, for example `2020-01-11` for 1 November and `2020-12-11` for 12 November (55 rows are detectably wrong; 5 rows for 11 November look right by coincidence). Read as normal dates, they collide with real dates such as 11 January.
- **PM2.5 without a column (observed).** `critical` is `PM25` in 271 rows (Sep to Dec), but the file has no PM2.5 column. In 160 of those rows `max` is higher than every listed component, so the index cannot be reproduced from the file.
- A few rows have all components missing, with `max` of 0 or empty and the category `TIDAK ADA DATA`.
- After excluding the March rows, there are 1,675 rows with a valid station label, but each station is missing between 46 and 69 days of 2020.

### 2021 (introduces PM2.5)
- Exactly 1,825 rows (5 stations x 365 days); full 12 months (observed).
- Introduces column `pm25` directly into Layout A structure (between `pm10` and `so2`).
- 100% dates are valid ISO `YYYY-MM-DD`.
- **Shifted row 1762 (observed):** Row for `2021-12-03` at `DKI1 (BUNDERAN HI)` has values shifted from `max` onward: `max` is `'PM25'`, `critical` is `'BAIK'`, and `categori` is `''`. Must be quarantined.

### 2022 (daily summary layout)
- **Incomplete coverage (observed).** 365 rows against 1,825 expected. Each date appears only once, and rows are heavily skewed to one station: `DKI4` 266, `DKI2` 39, `DKI3` 33, `DKI5` 22, `DKI1` 4, and one row with station `0`. Same daily summary pattern as 2019.
- **Wrong year in dates (observed).** All 28 February rows are dated `2020-02-01` to `2020-02-28` while `periode_data` is `202202`.
- One row stores the date as an Excel serial number (`44926.625`, which is 31 Dec 2022, 15:00).
- Station is in the last column (`lokasi_spku`) and has no name. Rows are not sorted by date.

### 2023
- **Covers Dec 2022 to Nov 2023, not calendar 2023 (observed).**
- **Overlap with the 2022 file (observed).** December 2022 appears in both files. For the 30 (date, station) pairs present in both, `max` is identical, but PM10 differs in some rows (for example on 2022-12-30: 40 in one file and 32 in the other).
- **Station spelling changes inside the file (observed).** The station code (`DKI1` to `DKI5`) is the stable key.
- **Mixed labels in the critical column (observed).** Names mixed with numeric codes (`1`, `2`, `3`, `5`), a dash, and 13 empty cells.
- **Code meaning differs from 2018 (inferred).** Matching each code to the component equal to `max` gives `1` = PM10, `2` = PM2.5, `3` = SO2, `5` = O3. In 2018, `2` meant SO2 and `3` meant CO. A code-to-pollutant mapping must be defined per file version.
- 365 days per station; no duplicates (observed).

### 2024–2025 (multi-month dataset)
- 3,501 rows covering 23 consecutive months (Jan 2024 to Nov 2025) (observed).
- Columns include `bulan` and full Indonesian pollutant names (`pm_sepuluh`, `pm_duakomalima`, `sulfur_dioksida`, etc.).
- **Date format change (observed):** Column `tanggal` contains only the day number (e.g. `'21'`), not a date string. Full calendar date must be synthesized from `periode_data` + `tanggal`.
- **Impossible calendar date (observed):** Row for `periode_data=202509`, `bulan=9`, `tanggal=31` (31 September does not exist). All component values are `'N/A'`. Must be quarantined.
- Contains string tokens `'NULL'` and `'N/A'` in `parameter_pencemar_kritis` and components.

## Category thresholds (observed on rows with a valid category)

| Category | 2016 | 2017 | 2018 | 2019 | 2021 | 2023 | 2024–2025 |
|----------|------|------|------|------|------|------|-----------|
| BAIK | 12 to 50 | 5 to 50 | 8 to 50 | 42 to 48 | 17 to 50 | 20 to 50 | 14 to 78 |
| SEDANG | 51 to 100 | 51 to 100 | 51 to 100 | 51 to 100 | 51 to 100 | 51 to 100 | 51 to 103 |
| TIDAK SEHAT | 101 to 176 | 101 to 168 | 101 to 197 | 101 to 199 | 101 to 179 | 101 to 199 | 101 to 187 |
| SANGAT TIDAK SEHAT | 203 | none | 202 to 234 | 201 to 243 | none | 217 to 287 | 202 |

The ranges match the standard Indonesian ISPU bands (0-50 BAIK, 51-100 SEDANG, 101-200 TIDAK SEHAT, 201-300 SANGAT TIDAK SEHAT). A few outliers (e.g. BAIK with max 78 or SEDANG with max 103 in 2024–2025) represent publisher calculation edge cases.

## Open questions

1. **Why do 2019 and 2022 hold only ~365 rows?**
   Both files have 0 duplicate dates and represent a single daily provincial summary recording rather than 5 individual station stations per day.
2. **Which file wins when two files disagree (December 2022: 2022 file vs 2023 file)?**
3. **Is there official documentation for the numeric codes in `critical`?**
4. **Can the June 2020 dates and the March 2020 stations be recovered from another resource or from the row order?** Treat any guess as unverified.
5. **What license or terms apply?** Record the exact wording from each source page here. **Not yet checked.**

## Decisions (draft)

| Decision | Reason |
|----------|--------|
| Use the station code (`DKI1` to `DKI5`) as the key; keep names in a separate dimension | Names are spelled differently across and within files |
| One parsing rule per layout and year; fail the run on an unknown layout | Column names, date formats, and code meanings all differ |
| Send the March 2020 rows to quarantine with the reason "station missing, columns shifted" | The station cannot be determined from the row |
| Send the June 2020 rows with a repeated date to quarantine, with the reason "date not trustworthy" | The date is wrong for most rows |
| Parse the November 2020 dates by format; treat year-day-month dates as a known defect and quarantine them unless a rule is confirmed | The same text can mean two different dates |
| Parse 2016 and 2018 dates supporting both ISO (`YYYY-MM-DD`) and slash (`DD/MM/YYYY`) | Late December rows in 2016 and 2018 use slash format |
| Quarantine row 1762 of 2021 with reason "shifted columns, non-numeric max" | `max` holds `'PM25'` and `critical` holds `'BAIK'` |
| Synthesize full date for 2024–2025 using `periode_data` + `tanggal`; quarantine impossible dates (e.g. 31 Sept) | Source provides day-of-month only |
| Treat `-`, `---`, empty, `'NULL'`, and `'N/A'` as missing, but keep original token in the raw layer | Files use different markers; the raw value must stay auditable |
| Do not overwrite the category silently for April 2018; if it is derived from `max`, add a flag column saying it was derived | The original value is missing, so the derived one is an inference |
| Record the source file for every row; decide a precedence rule for overlapping periods | December 2022 appears in two files with conflicting PM10 values |
| Report PM2.5 as unavailable for the 2016, 2017, 2018, 2019, and 2020 layouts | The column does not exist in the raw files |
