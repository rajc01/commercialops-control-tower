# CommercialOps Control Tower

## Business problem

Commercial operations teams often manage customer, order, invoice, payment, and project information across separate spreadsheets. This makes it difficult to see the full operational picture, reconcile related records, and identify missing, inconsistent, or delayed data before those issues affect reporting and decision-making.

## Proposed solution

CommercialOps Control Tower will be a small ERP-style monitoring system that brings these business records together in one beginner-friendly Streamlit dashboard. It will calculate operational KPIs, run clear data-quality and reconciliation checks, and suggest practical follow-up actions without introducing unnecessary infrastructure or complexity.

## Technology stack

- Python
- Pandas
- Streamlit
- Excel and openpyxl
- pytest

## Planned data flow

1. Generate sample customer, order, invoice, payment, and project data as Excel files.
2. Load the files into Pandas DataFrames.
3. Validate data quality and reconcile related records.
4. Calculate commercial operations KPIs.
5. Create recommendations from the detected issues.
6. Display KPIs, validation results, and recommendations in Streamlit.

Phase 0 contains only the project scaffold. Business logic and sample data will be added in a later phase.
