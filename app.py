"""Display the OpsTower Streamlit dashboard."""

from pathlib import Path

import streamlit as st

from src.data_loader import load_workbook
from src.kpis import (
    build_project_budget_monitor,
    build_receivables_monitor,
    calculate_kpis,
)
from src.validations import run_all_validations


DEMO_AS_OF_DATE = "2026-09-07"


def format_inr(value: float | int) -> str:
    """Format a dashboard metric as Indian rupees."""
    return f"₹{value:,.0f}"


st.set_page_config(page_title="OpsTower", layout="wide")
st.title("OpsTower")
st.subheader(
    "ERP-style monitoring for commercial operations, reconciliation and exception management"
)

workbook_path = Path(__file__).parent / "data" / "commercial_ops_data.xlsx"

try:
    datasets = load_workbook(workbook_path)
except (FileNotFoundError, ValueError) as error:
    st.error(f"Unable to load commercial operations data: {error}")
    st.stop()

issues = run_all_validations(datasets, as_of_date=DEMO_AS_OF_DATE)
kpis = calculate_kpis(datasets, issues, as_of_date=DEMO_AS_OF_DATE)
receivables_monitor = build_receivables_monitor(
    datasets["invoices"], datasets["payments"], as_of_date=DEMO_AS_OF_DATE
)
project_monitor = build_project_budget_monitor(datasets["projects"])

kpi_columns = st.columns(4)
kpi_columns[0].metric("Data Quality Score", f"{kpis['data_quality_score']:.2f}%")
kpi_columns[1].metric("Revenue at Risk", format_inr(kpis["revenue_at_risk"]))
kpi_columns[2].metric(
    "Outstanding Receivables", format_inr(kpis["outstanding_receivables"])
)
kpi_columns[3].metric("High-Severity Issues", kpis["high_severity_issues"])

st.header("Operational Exceptions")
filter_columns = st.columns(3)
severity_options = issues["severity"].drop_duplicates().tolist()
issue_type_options = sorted(issues["issue_type"].unique())
entity_options = sorted(issues["entity"].unique())

selected_severities = filter_columns[0].multiselect(
    "Severity", severity_options, default=severity_options
)
selected_issue_types = filter_columns[1].multiselect(
    "Issue Type", issue_type_options, default=issue_type_options
)
selected_entities = filter_columns[2].multiselect(
    "Entity", entity_options, default=entity_options
)

filtered_issues = issues.loc[
    issues["severity"].isin(selected_severities)
    & issues["issue_type"].isin(selected_issue_types)
    & issues["entity"].isin(selected_entities)
]
issue_columns = [
    "severity",
    "issue_type",
    "entity",
    "record_id",
    "description",
    "recommended_action",
]
st.dataframe(filtered_issues[issue_columns], width="stretch", hide_index=True)

currency_columns = {
    "invoice_amount": st.column_config.NumberColumn(format="₹ %,.2f"),
    "amount_paid": st.column_config.NumberColumn(format="₹ %,.2f"),
    "outstanding_balance": st.column_config.NumberColumn(format="₹ %,.2f"),
}

st.header("Receivables Monitor")
st.dataframe(
    receivables_monitor,
    width="stretch",
    hide_index=True,
    column_config={
        **currency_columns,
        "due_date": st.column_config.DateColumn(format="YYYY-MM-DD"),
        "days_overdue": st.column_config.NumberColumn(format="%d"),
    },
)

st.header("Project Budget Monitor")
st.dataframe(
    project_monitor,
    width="stretch",
    hide_index=True,
    column_config={
        "budget": st.column_config.NumberColumn(format="₹ %,.2f"),
        "actual_cost": st.column_config.NumberColumn(format="₹ %,.2f"),
        "variance": st.column_config.NumberColumn(format="₹ %,.2f"),
        "variance_percentage": st.column_config.NumberColumn(format="%.1f%%"),
    },
)

st.header("Source Data")
for dataset_name, dataframe in datasets.items():
    with st.expander(dataset_name.title()):
        st.dataframe(dataframe, width="stretch", hide_index=True)
