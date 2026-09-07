"""Provide the Streamlit entry point for the CommercialOps dashboard."""

from pathlib import Path

import streamlit as st

from src.data_loader import load_workbook


st.title("CommercialOps Control Tower")
st.subheader("ERP-style commercial operations monitoring and reconciliation dashboard")

workbook_path = Path(__file__).parent / "data" / "commercial_ops_data.xlsx"

try:
    datasets = load_workbook(workbook_path)
except (FileNotFoundError, ValueError) as error:
    st.error(f"Unable to load commercial operations data: {error}")
    st.stop()

st.success("Commercial operations data loaded successfully.")

columns = st.columns(len(datasets))
for column, (dataset_name, dataframe) in zip(columns, datasets.items()):
    column.metric(dataset_name.title(), len(dataframe))

st.write("Expand a dataset below to preview its records.")
for dataset_name, dataframe in datasets.items():
    with st.expander(f"{dataset_name.title()} preview"):
        st.dataframe(dataframe, width="stretch")
