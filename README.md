# OpsTower

## Project Overview

OpsTower simulates an ERP-style commercial operations control layer using Excel, Python, Pandas, and Streamlit. It monitors customer, order, invoice, payment, and project data to highlight data-quality, reconciliation, receivables, and budget exceptions. This is a simulated ERP-style project and does not connect to a real SAP or ERP system.

## Business Flow

`Customer → Order → Invoice → Payment`

`Order → Project`

## Controls

- Missing records and important fields
- Duplicate records
- Customer/order mismatch
- Invoice/order mismatch
- Order and invoice amount mismatch
- Payment/invoice mismatch
- Overdue receivables
- Project budget variance

## KPIs

- **Data Quality Score:** Percentage of records not affected by a detected issue.
- **Outstanding Receivables:** Total positive invoice balance remaining after payments.
- **Revenue at Risk:** Outstanding balance that is overdue or linked to a high-severity invoice issue.
- **High-Severity Issues:** Number of exceptions requiring urgent attention.

## Tech Stack

- Python
- Pandas
- Streamlit
- Excel / openpyxl
- pytest

## Run Locally

```bash
pip install -r requirements.txt
python scripts/generate_sample_data.py
streamlit run app.py
pytest
```

## Example Business Scenario

An order is recorded for ₹12,000, but its invoice is ₹15,000 and no payment has been received. OpsTower detects the ₹3,000 order-to-invoice mismatch, reports the ₹15,000 outstanding balance, and recommends reconciling the invoice with the source order and following up on payment.

## Future Improvements

The following are possible future improvements and are not implemented in this project:

- SAP/ERP API integration
- Scheduled data refresh
- Teams/email alerts
- Role-based access
- Exception audit history
