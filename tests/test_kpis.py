"""Test the Phase 3 commercial operations KPI calculations."""

import pandas as pd

from src.kpis import (
    calculate_data_quality_score,
    calculate_issue_counts,
    calculate_outstanding_receivables,
    calculate_revenue_at_risk,
)


def make_invoice_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create invoices with partial, excessive, and missing payments."""
    invoices = pd.DataFrame(
        [
            ["INV-001", 1000, "2026-08-01"],
            ["INV-002", 500, "2026-10-01"],
            ["INV-003", 300, "2026-10-15"],
        ],
        columns=["invoice_id", "invoice_amount", "due_date"],
    )
    payments = pd.DataFrame(
        [
            ["INV-001", 200],
            ["INV-001", 300],
            ["INV-002", 600],
        ],
        columns=["invoice_id", "payment_amount"],
    )
    return invoices, payments


def test_outstanding_receivables() -> None:
    invoices, payments = make_invoice_data()

    result = calculate_outstanding_receivables(invoices, payments)

    assert result == 800


def test_revenue_at_risk_does_not_double_count_invoices() -> None:
    invoices, payments = make_invoice_data()
    issues = pd.DataFrame(
        [
            ["High", "Invoice", "INV-001"],
            ["High", "Invoice", "INV-003"],
            ["High", "Payment", "INV-002"],
        ],
        columns=["severity", "entity", "record_id"],
    )

    result = calculate_revenue_at_risk(
        invoices, payments, issues, as_of_date="2026-09-07"
    )

    # INV-001 is overdue and High severity but is included only once.
    # INV-003 is not overdue but is included because it has a High invoice issue.
    assert result == 800


def test_data_quality_score_uses_unique_affected_records() -> None:
    data = {
        "customers": pd.DataFrame(index=range(2)),
        "orders": pd.DataFrame(index=range(2)),
        "invoices": pd.DataFrame(index=range(2)),
        "payments": pd.DataFrame(index=range(2)),
        "projects": pd.DataFrame(index=range(2)),
    }
    issues = pd.DataFrame(
        [
            ["Customer", "CUST-001"],
            ["Customer", "CUST-001"],
            ["Order", "ORD-001"],
        ],
        columns=["entity", "record_id"],
    )

    result = calculate_data_quality_score(data, issues)

    assert result == 80


def test_severity_counts() -> None:
    issues = pd.DataFrame(
        {"severity": ["High", "Medium", "High", "Medium", "High"]}
    )

    result = calculate_issue_counts(issues)

    assert result == {
        "high_severity_issues": 3,
        "medium_severity_issues": 2,
        "total_issues": 5,
    }
