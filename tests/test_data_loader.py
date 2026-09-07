"""Test the Excel workbook loading layer."""

from pathlib import Path

import pandas as pd
import pytest

from src.data_loader import load_workbook


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_load_workbook_returns_all_datasets() -> None:
    """The generated workbook should load all five expected datasets."""
    datasets = load_workbook(PROJECT_ROOT / "data" / "commercial_ops_data.xlsx")

    assert list(datasets) == ["customers", "orders", "invoices", "payments", "projects"]
    assert {name: len(dataframe) for name, dataframe in datasets.items()} == {
        "customers": 15,
        "orders": 25,
        "invoices": 20,
        "payments": 15,
        "projects": 8,
    }


def test_load_workbook_reports_missing_sheets(tmp_path: Path) -> None:
    """A clear error should identify every required worksheet that is absent."""
    incomplete_workbook = tmp_path / "incomplete.xlsx"
    pd.DataFrame({"customer_id": ["CUST-001"]}).to_excel(
        incomplete_workbook, sheet_name="Customers", index=False
    )

    with pytest.raises(ValueError, match="Orders, Invoices, Payments, Projects"):
        load_workbook(incomplete_workbook)
