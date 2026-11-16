"""Integration and end-to-end pipeline tests for 2017 ISPU data."""

from pathlib import Path
from src.ingestion import read_ispu_2017_html, validate_ispu_2017


def test_pipeline_synthetic_e2e():
    html_content = """
    <table>
      <thead>
        <tr><th>periode_data</th><th>tanggal</th><th>stasiun</th><th>pm10</th><th>so2</th>
            <th>co</th><th>o3</th><th>no2</th><th>max</th><th>critical</th><th>categori</th></tr>
      </thead>
      <tbody>
        <tr><td>201701</td><td>2017-01-01</td><td>DKI1 (BUNDERAN HI)</td><td>49</td><td>---</td>
            <td>23</td><td>41</td><td>3</td><td>49</td><td>PM10</td><td>BAIK</td></tr>
        <tr><td>202003</td><td>2020-03-19</td><td>73</td><td>22</td>
            <td>27</td><td>37</td><td>9</td><td>73</td><td>1</td><td>PM10</td><td>SEDANG</td></tr>
      </tbody>
    </table>
    """
    import io

    df_raw = read_ispu_2017_html(io.StringIO(html_content))
    assert len(df_raw) == 2

    result = validate_ispu_2017(df_raw)
    assert len(result.valid) == 1
    assert len(result.quarantined) == 1

    # Valid row preserves raw tokens
    assert result.valid.iloc[0]["stasiun"] == "DKI1 (BUNDERAN HI)"
    assert result.valid.iloc[0]["so2"] == "---"

    # Quarantined row preserves original row plus reason
    assert result.quarantined.iloc[0]["stasiun"] == "73"
    assert (
        result.quarantined.iloc[0]["quarantine_reason"]
        == "INVALID_STATION_CODE"
    )


def test_pipeline_on_actual_2017_data_file():
    raw_path = Path(
        "data/raw/stasiun-pemantau-kualitas-udara-(-spku)-tahun-2017-komponen-data.xls"
    )
    if not raw_path.exists():
        return

    df_raw = read_ispu_2017_html(raw_path)

    # Invariant from docs/DATA_INVENTORY.md: exactly 1,825 rows (5 stations x 365 days)
    assert len(df_raw) == 1825

    result = validate_ispu_2017(df_raw)

    # Invariant: 2017 is the clean baseline - all 1,825 rows must be valid
    assert len(result.valid) == 1825
    assert len(result.quarantined) == 0

    # Invariant: raw missing token '---' exists as string in the valid output
    so2_missing_count = (result.valid["so2"] == "---").sum()
    assert so2_missing_count > 0
