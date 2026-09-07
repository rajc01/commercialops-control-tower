"""Calculate the core commercial operations key performance indicators."""

from datetime import date

import pandas as pd


DATASET_NAMES = ("customers", "orders", "invoices", "payments", "projects")


def calculate_data_quality_score(
    data: dict[str, pd.DataFrame], issues: pd.DataFrame
) -> float:
    """Calculate the percentage of records not affected by a reported issue."""
    total_records = sum(len(data[dataset_name]) for dataset_name in DATASET_NAMES)
    if total_records == 0:
        return 100.0

    if issues.empty:
        affected_records = 0
    else:
        affected_records = len(
            issues[["entity", "record_id"]].drop_duplicates()
        )

    score = 100 * (1 - affected_records / total_records)
    return round(max(0.0, min(100.0, score)), 2)


def calculate_invoice_balances(
    invoices: pd.DataFrame, payments: pd.DataFrame
) -> pd.DataFrame:
    """Return invoice amounts, payments received, and outstanding balances."""
    invoice_columns = ["invoice_id", "invoice_amount", "due_date"]
    if "status" in invoices.columns:
        invoice_columns.append("status")

    balances = invoices[invoice_columns].copy()
    balances["invoice_amount"] = pd.to_numeric(
        balances["invoice_amount"], errors="coerce"
    ).fillna(0)
    balances["due_date"] = pd.to_datetime(balances["due_date"], errors="coerce")

    payment_values = payments[["invoice_id", "payment_amount"]].copy()
    payment_values["payment_amount"] = pd.to_numeric(
        payment_values["payment_amount"], errors="coerce"
    ).fillna(0)
    payment_totals = (
        payment_values.groupby("invoice_id", as_index=False)["payment_amount"]
        .sum()
        .rename(columns={"payment_amount": "payments_received"})
    )

    balances = balances.merge(payment_totals, on="invoice_id", how="left")
    balances["payments_received"] = balances["payments_received"].fillna(0)

    # Overpayments should not create negative receivables.
    balances["outstanding_balance"] = (
        balances["invoice_amount"] - balances["payments_received"]
    ).clip(lower=0)
    return balances


def calculate_outstanding_receivables(
    invoices: pd.DataFrame, payments: pd.DataFrame
) -> float:
    """Sum all positive invoice balances still awaiting payment."""
    balances = calculate_invoice_balances(invoices, payments)
    return round(float(balances["outstanding_balance"].sum()), 2)


def calculate_revenue_at_risk(
    invoices: pd.DataFrame,
    payments: pd.DataFrame,
    issues: pd.DataFrame,
    as_of_date: str | date | pd.Timestamp | None = None,
) -> float:
    """Sum outstanding invoices that are overdue or have a High invoice issue."""
    comparison_date = (
        pd.Timestamp.today().normalize()
        if as_of_date is None
        else pd.Timestamp(as_of_date).normalize()
    )
    balances = calculate_invoice_balances(invoices, payments)

    if issues.empty:
        high_issue_invoice_ids: set[str] = set()
    else:
        high_invoice_issues = issues.loc[
            (issues["severity"] == "High") & (issues["entity"] == "Invoice")
        ]
        high_issue_invoice_ids = set(high_invoice_issues["record_id"].astype(str))

    overdue = balances["due_date"].notna() & (
        balances["due_date"] < comparison_date
    )
    has_high_invoice_issue = balances["invoice_id"].astype(str).isin(
        high_issue_invoice_ids
    )

    # Combining the conditions first prevents double-counting an invoice that
    # is both overdue and affected by a High-severity reconciliation issue.
    at_risk = balances["outstanding_balance"].gt(0) & (
        overdue | has_high_invoice_issue
    )
    return round(float(balances.loc[at_risk, "outstanding_balance"].sum()), 2)


def calculate_issue_counts(issues: pd.DataFrame) -> dict[str, int]:
    """Count High, Medium, and total validation issues."""
    if issues.empty:
        return {
            "high_severity_issues": 0,
            "medium_severity_issues": 0,
            "total_issues": 0,
        }

    return {
        "high_severity_issues": int((issues["severity"] == "High").sum()),
        "medium_severity_issues": int((issues["severity"] == "Medium").sum()),
        "total_issues": len(issues),
    }


def build_receivables_monitor(
    invoices: pd.DataFrame,
    payments: pd.DataFrame,
    as_of_date: str | date | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Build the invoice-level table used by the receivables dashboard section."""
    comparison_date = (
        pd.Timestamp.today().normalize()
        if as_of_date is None
        else pd.Timestamp(as_of_date).normalize()
    )
    monitor = calculate_invoice_balances(invoices, payments).rename(
        columns={"payments_received": "amount_paid"}
    )

    if "status" not in monitor.columns:
        monitor["status"] = ""

    overdue_days = (comparison_date - monitor["due_date"]).dt.days
    is_overdue = monitor["outstanding_balance"].gt(0) & overdue_days.gt(0)
    monitor["days_overdue"] = overdue_days.where(is_overdue, 0).fillna(0).astype(int)

    # Keep unpaid invoices at the top, with the oldest overdue items first.
    monitor["_is_outstanding"] = monitor["outstanding_balance"].gt(0)
    monitor = monitor.sort_values(
        ["_is_outstanding", "days_overdue"], ascending=[False, False], kind="stable"
    ).drop(columns="_is_outstanding")

    return monitor[
        [
            "invoice_id",
            "due_date",
            "invoice_amount",
            "amount_paid",
            "outstanding_balance",
            "days_overdue",
            "status",
        ]
    ].reset_index(drop=True)


def build_project_budget_monitor(projects: pd.DataFrame) -> pd.DataFrame:
    """Build the project budget table used by the dashboard."""
    monitor = projects[
        ["project_id", "project_name", "owner", "budget", "actual_cost", "status"]
    ].copy()
    monitor["budget"] = pd.to_numeric(monitor["budget"], errors="coerce")
    monitor["actual_cost"] = pd.to_numeric(monitor["actual_cost"], errors="coerce")
    monitor["variance"] = monitor["actual_cost"] - monitor["budget"]

    # A zero budget has no meaningful percentage variance.
    valid_budget = monitor["budget"].gt(0)
    monitor["variance_percentage"] = (
        monitor["variance"].div(monitor["budget"]).mul(100).where(valid_budget)
    )

    return monitor[
        [
            "project_id",
            "project_name",
            "owner",
            "budget",
            "actual_cost",
            "variance",
            "variance_percentage",
            "status",
        ]
    ]


def calculate_kpis(
    data: dict[str, pd.DataFrame],
    issues: pd.DataFrame,
    as_of_date: str | date | pd.Timestamp | None = None,
) -> dict[str, float | int]:
    """Calculate and return the four Phase 3 business KPIs."""
    issue_counts = calculate_issue_counts(issues)

    return {
        "data_quality_score": calculate_data_quality_score(data, issues),
        "outstanding_receivables": calculate_outstanding_receivables(
            data["invoices"], data["payments"]
        ),
        "revenue_at_risk": calculate_revenue_at_risk(
            data["invoices"],
            data["payments"],
            issues,
            as_of_date=as_of_date,
        ),
        **issue_counts,
    }
