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

1. Generate one Excel workbook containing five worksheets for customer, order, invoice, payment, and project data.
2. Load the five worksheets into Pandas DataFrames.
3. Validate data quality and reconcile related records.
4. Calculate commercial operations KPIs.
5. Create recommendations from the detected issues.
6. Display KPIs, validation results, and recommendations in Streamlit.

## Current Phase 4 features

- A deterministic Excel workbook with five commercial operations datasets
- Realistic sample records with a small number of deliberate data issues
- A reusable data loader that checks for all required worksheets
- A Streamlit view with record counts and expandable data previews
- A standardized validation and reconciliation engine for operational exceptions
- Business KPIs for data quality, receivables, revenue at risk, and issue severity
- A Streamlit dashboard for KPIs, exceptions, receivables, projects, and source data

Automated recommendations are intentionally reserved for a later phase.

## Run the project

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/generate_sample_data.py
streamlit run app.py
```
