import pandas as pd
from src.ingestion.models import ValidationResult, LayoutMismatchError


def test_validation_result_holds_dataframes():
    df_valid = pd.DataFrame({"stasiun": ["DKI1 (BUNDERAN HI)"]})
    df_quarantine = pd.DataFrame(
        {"stasiun": ["73"], "quarantine_reason": ["INVALID_STATION_CODE"]}
    )
    res = ValidationResult(valid=df_valid, quarantined=df_quarantine)
    assert len(res.valid) == 1
    assert len(res.quarantined) == 1
    assert res.quarantined.iloc[0]["quarantine_reason"] == "INVALID_STATION_CODE"


def test_layout_mismatch_error_is_value_error():
    err = LayoutMismatchError("Columns do not match expected layout")
    assert isinstance(err, ValueError)
