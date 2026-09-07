"""Load the five commercial operations datasets from an Excel workbook."""

from pathlib import Path

import pandas as pd


REQUIRED_SHEETS = {
    "Customers": "customers",
    "Orders": "orders",
    "Invoices": "invoices",
    "Payments": "payments",
    "Projects": "projects",
}


def load_workbook(path: str | Path) -> dict[str, pd.DataFrame]:
    """Load required worksheets and return DataFrames keyed by dataset name."""
    workbook_path = Path(path)

    with pd.ExcelFile(workbook_path, engine="openpyxl") as workbook:
        missing_sheets = [
            sheet_name
            for sheet_name in REQUIRED_SHEETS
            if sheet_name not in workbook.sheet_names
        ]

        if missing_sheets:
            missing_list = ", ".join(missing_sheets)
            raise ValueError(f"Workbook is missing required worksheet(s): {missing_list}")

        return {
            dataset_name: pd.read_excel(workbook, sheet_name=sheet_name)
            for sheet_name, dataset_name in REQUIRED_SHEETS.items()
        }
