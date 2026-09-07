"""Detect and report operational data-quality and reconciliation issues."""

from datetime import date
from typing import Any

import pandas as pd


ISSUE_COLUMNS = [
    "issue_id",
    "issue_type",
    "severity",
    "entity",
    "record_id",
    "description",
    "recommended_action",
]

REQUIRED_FIELD_RULES = {
    "customers": {
        "entity": "Customer",
        "id_field": "customer_id",
        "fields": {
            "customer_id": "High",
            "customer_name": "Medium",
            "email": "Medium",
        },
    },
    "orders": {
        "entity": "Order",
        "id_field": "order_id",
        "fields": {
            "order_id": "High",
            "customer_id": "High",
            "order_date": "High",
            "order_amount": "High",
            "project_id": "High",
        },
    },
    "invoices": {
        "entity": "Invoice",
        "id_field": "invoice_id",
        "fields": {
            "invoice_id": "High",
            "order_id": "High",
            "invoice_date": "High",
            "due_date": "High",
            "invoice_amount": "High",
        },
    },
    "payments": {
        "entity": "Payment",
        "id_field": "payment_id",
        "fields": {
            "payment_id": "High",
            "invoice_id": "High",
            "payment_date": "High",
            "payment_amount": "High",
        },
    },
    "projects": {
        "entity": "Project",
        "id_field": "project_id",
        "fields": {
            "project_id": "High",
            "project_name": "Medium",
            "owner": "Medium",
            "budget": "High",
            "actual_cost": "High",
        },
    },
}

DUPLICATE_ID_RULES = {
    "customers": ("Customer", "customer_id"),
    "orders": ("Order", "order_id"),
    "invoices": ("Invoice", "invoice_id"),
    "payments": ("Payment", "payment_id"),
    "projects": ("Project", "project_id"),
}


def _is_missing(value: Any) -> bool:
    """Return True for null values and blank text."""
    return bool(pd.isna(value)) or (isinstance(value, str) and not value.strip())


def _clean_id(value: Any) -> str | None:
    """Convert a populated business ID to text."""
    if _is_missing(value):
        return None
    return str(value).strip()


def _record_id(row: pd.Series, id_field: str, excel_row: int) -> str:
    """Return a business ID, or an Excel row reference when that ID is missing."""
    return _clean_id(row[id_field]) or f"Row {excel_row}"


def _format_inr(value: float) -> str:
    """Format a numeric amount as Indian rupees for issue descriptions."""
    amount = float(value)
    if amount.is_integer():
        return f"₹{amount:,.0f}"
    return f"₹{amount:,.2f}"


def _issue(
    issue_type: str,
    severity: str,
    entity: str,
    record_id: str,
    description: str,
    recommended_action: str,
) -> dict[str, str]:
    """Build one issue before the final deterministic ID is assigned."""
    return {
        "issue_type": issue_type,
        "severity": severity,
        "entity": entity,
        "record_id": record_id,
        "description": description,
        "recommended_action": recommended_action,
    }


def _valid_ids(values: pd.Series) -> set[str]:
    """Return populated IDs without changing the source Series."""
    return {cleaned for value in values if (cleaned := _clean_id(value)) is not None}


def check_missing_required_fields(
    data: dict[str, pd.DataFrame],
) -> list[dict[str, str]]:
    """Find missing required values across all five datasets."""
    issues: list[dict[str, str]] = []
    action = "Complete the missing business data and verify the authoritative source record."

    for dataset_name, rule in REQUIRED_FIELD_RULES.items():
        dataframe = data[dataset_name]
        entity = str(rule["entity"])
        id_field = str(rule["id_field"])
        fields = rule["fields"]

        for excel_row, (_, row) in enumerate(dataframe.iterrows(), start=2):
            for field_name, severity in fields.items():
                if _is_missing(row[field_name]):
                    record_id = _record_id(row, id_field, excel_row)
                    issues.append(
                        _issue(
                            "MISSING_REQUIRED_FIELD",
                            severity,
                            entity,
                            record_id,
                            f"{entity} {record_id} is missing required field '{field_name}'.",
                            action,
                        )
                    )

    return issues


def check_duplicate_records(data: dict[str, pd.DataFrame]) -> list[dict[str, str]]:
    """Report one issue for each duplicated business ID."""
    issues: list[dict[str, str]] = []
    action = "Review duplicate records and retain the authoritative business record."

    for dataset_name, (entity, id_field) in DUPLICATE_ID_RULES.items():
        dataframe = data[dataset_name]
        populated_ids = dataframe[id_field].map(_clean_id).dropna()
        duplicated_ids = populated_ids[populated_ids.duplicated(keep=False)].drop_duplicates()

        for duplicated_id in duplicated_ids:
            count = int((populated_ids == duplicated_id).sum())
            issues.append(
                _issue(
                    "DUPLICATE_RECORD",
                    "High",
                    entity,
                    duplicated_id,
                    f"{entity} ID {duplicated_id} appears in {count} records.",
                    action,
                )
            )

    return issues


def check_order_customer_relationships(
    orders: pd.DataFrame, customers: pd.DataFrame
) -> list[dict[str, str]]:
    """Find orders that reference customers absent from the customer master."""
    issues: list[dict[str, str]] = []
    customer_ids = _valid_ids(customers["customer_id"])
    action = "Verify the customer master mapping before processing the order."

    for excel_row, (_, order) in enumerate(orders.iterrows(), start=2):
        customer_id = _clean_id(order["customer_id"])
        if customer_id is not None and customer_id not in customer_ids:
            order_id = _record_id(order, "order_id", excel_row)
            issues.append(
                _issue(
                    "ORDER_CUSTOMER_MISMATCH",
                    "High",
                    "Order",
                    order_id,
                    f"Order {order_id} references customer {customer_id}, which does not exist.",
                    action,
                )
            )

    return issues


def check_invoice_order_relationships(
    invoices: pd.DataFrame, orders: pd.DataFrame
) -> list[dict[str, str]]:
    """Find invoices that reference sales orders that do not exist."""
    issues: list[dict[str, str]] = []
    order_ids = _valid_ids(orders["order_id"])
    action = "Reconcile the invoice with its originating sales order."

    for excel_row, (_, invoice) in enumerate(invoices.iterrows(), start=2):
        order_id = _clean_id(invoice["order_id"])
        if order_id is not None and order_id not in order_ids:
            invoice_id = _record_id(invoice, "invoice_id", excel_row)
            issues.append(
                _issue(
                    "INVOICE_ORDER_MISMATCH",
                    "High",
                    "Invoice",
                    invoice_id,
                    f"Invoice {invoice_id} references order {order_id}, which does not exist.",
                    action,
                )
            )

    return issues


def check_order_invoice_amounts(
    invoices: pd.DataFrame, orders: pd.DataFrame
) -> list[dict[str, str]]:
    """Compare each valid invoice amount with its one-to-one sales order amount."""
    issues: list[dict[str, str]] = []
    action = "Verify pricing, quantity, taxes, discounts, or invoice adjustments."

    # A lookup copy avoids changing or deduplicating the source order DataFrame.
    order_lookup = orders.drop_duplicates(subset="order_id", keep="first").set_index("order_id")

    for excel_row, (_, invoice) in enumerate(invoices.iterrows(), start=2):
        order_id = _clean_id(invoice["order_id"])
        if order_id is None or order_id not in order_lookup.index:
            continue

        invoice_amount = pd.to_numeric(invoice["invoice_amount"], errors="coerce")
        order_amount = pd.to_numeric(
            order_lookup.at[order_id, "order_amount"], errors="coerce"
        )
        if pd.isna(invoice_amount) or pd.isna(order_amount):
            continue

        difference = abs(float(invoice_amount) - float(order_amount))
        if difference > 1:
            invoice_id = _record_id(invoice, "invoice_id", excel_row)
            issues.append(
                _issue(
                    "ORDER_INVOICE_AMOUNT_MISMATCH",
                    "High",
                    "Invoice",
                    invoice_id,
                    (
                        f"Invoice {invoice_id} amount {_format_inr(invoice_amount)} does not "
                        f"match Order {order_id} amount {_format_inr(order_amount)}. "
                        f"Difference: {_format_inr(difference)}."
                    ),
                    action,
                )
            )

    return issues


def check_payment_invoice_relationships(
    payments: pd.DataFrame, invoices: pd.DataFrame
) -> list[dict[str, str]]:
    """Find payments that reference invoices that do not exist."""
    issues: list[dict[str, str]] = []
    invoice_ids = _valid_ids(invoices["invoice_id"])
    action = "Reconcile the incoming payment against the correct invoice."

    for excel_row, (_, payment) in enumerate(payments.iterrows(), start=2):
        invoice_id = _clean_id(payment["invoice_id"])
        if invoice_id is not None and invoice_id not in invoice_ids:
            payment_id = _record_id(payment, "payment_id", excel_row)
            issues.append(
                _issue(
                    "PAYMENT_INVOICE_MISMATCH",
                    "High",
                    "Payment",
                    payment_id,
                    f"Payment {payment_id} references invoice {invoice_id}, which does not exist.",
                    action,
                )
            )

    return issues


def check_overdue_receivables(
    invoices: pd.DataFrame,
    payments: pd.DataFrame,
    as_of_date: str | date | pd.Timestamp | None = None,
) -> list[dict[str, str]]:
    """Find unpaid invoice balances whose due dates have passed."""
    issues: list[dict[str, str]] = []
    comparison_date = (
        pd.Timestamp.today().normalize()
        if as_of_date is None
        else pd.Timestamp(as_of_date).normalize()
    )
    action = "Follow up with the customer or account owner and confirm payment status."

    # Multiple payments may belong to one invoice, so accumulate them first.
    payment_totals: dict[str, float] = {}
    for _, payment in payments.iterrows():
        invoice_id = _clean_id(payment["invoice_id"])
        payment_amount = pd.to_numeric(payment["payment_amount"], errors="coerce")
        if invoice_id is not None and not pd.isna(payment_amount):
            payment_totals[invoice_id] = payment_totals.get(invoice_id, 0) + float(
                payment_amount
            )

    for excel_row, (_, invoice) in enumerate(invoices.iterrows(), start=2):
        invoice_id = _record_id(invoice, "invoice_id", excel_row)
        invoice_amount = pd.to_numeric(invoice["invoice_amount"], errors="coerce")
        due_date = pd.to_datetime(invoice["due_date"], errors="coerce")
        if pd.isna(invoice_amount) or pd.isna(due_date):
            continue

        total_payments = payment_totals.get(_clean_id(invoice["invoice_id"]) or "", 0)
        outstanding_balance = max(float(invoice_amount) - total_payments, 0)

        if outstanding_balance > 0 and due_date.normalize() < comparison_date:
            overdue_days = int((comparison_date - due_date.normalize()).days)
            severity = "Medium" if overdue_days <= 30 else "High"
            issues.append(
                _issue(
                    "OVERDUE_RECEIVABLE",
                    severity,
                    "Invoice",
                    invoice_id,
                    (
                        f"Invoice {invoice_id} has {_format_inr(outstanding_balance)} "
                        f"outstanding, due {due_date:%Y-%m-%d}, and is "
                        f"{overdue_days} days overdue."
                    ),
                    action,
                )
            )

    return issues


def check_project_budget_variances(
    projects: pd.DataFrame,
) -> list[dict[str, str]]:
    """Find projects whose actual cost exceeds budget by more than 10 percent."""
    issues: list[dict[str, str]] = []
    action = "Review project expenditure and investigate the cost overrun."

    for excel_row, (_, project) in enumerate(projects.iterrows(), start=2):
        budget = pd.to_numeric(project["budget"], errors="coerce")
        actual_cost = pd.to_numeric(project["actual_cost"], errors="coerce")

        # A missing or zero budget is reported by the required-field check when
        # applicable, but is skipped here to avoid an invalid percentage.
        if pd.isna(budget) or pd.isna(actual_cost) or float(budget) <= 0:
            continue

        variance = float(actual_cost) - float(budget)
        variance_percentage = (variance / float(budget)) * 100
        if variance > 0 and variance_percentage > 10:
            project_id = _record_id(project, "project_id", excel_row)
            project_name = project["project_name"]
            severity = "Medium" if variance_percentage <= 20 else "High"
            issues.append(
                _issue(
                    "PROJECT_BUDGET_VARIANCE",
                    severity,
                    "Project",
                    project_id,
                    (
                        f"Project {project_id} ({project_name}) has budget "
                        f"{_format_inr(budget)} and actual cost "
                        f"{_format_inr(actual_cost)}. It is {_format_inr(variance)} "
                        f"over budget ({variance_percentage:.1f}%)."
                    ),
                    action,
                )
            )

    return issues


def run_all_validations(
    data: dict[str, pd.DataFrame],
    as_of_date: str | date | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Run every check and return one standardized issues DataFrame."""
    issues: list[dict[str, str]] = []

    # The fixed check order makes issue IDs deterministic for the same input.
    issues.extend(check_missing_required_fields(data))
    issues.extend(check_duplicate_records(data))
    issues.extend(
        check_order_customer_relationships(data["orders"], data["customers"])
    )
    issues.extend(check_invoice_order_relationships(data["invoices"], data["orders"]))
    issues.extend(check_order_invoice_amounts(data["invoices"], data["orders"]))
    issues.extend(
        check_payment_invoice_relationships(data["payments"], data["invoices"])
    )
    issues.extend(
        check_overdue_receivables(
            data["invoices"], data["payments"], as_of_date=as_of_date
        )
    )
    issues.extend(check_project_budget_variances(data["projects"]))

    numbered_issues = [
        {"issue_id": f"ISSUE-{number:03d}", **issue}
        for number, issue in enumerate(issues, start=1)
    ]
    return pd.DataFrame(numbered_issues, columns=ISSUE_COLUMNS)
