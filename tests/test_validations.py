"""Test the operational validation and reconciliation rules."""

import pandas as pd

from src.validations import run_all_validations


AS_OF_DATE = "2026-09-07"


def make_valid_data() -> dict[str, pd.DataFrame]:
    """Create a minimal, internally consistent dataset for each test."""
    return {
        "customers": pd.DataFrame(
            [["CUST-001", "Example Customer", "North", "SMB", "hello@example.com"]],
            columns=["customer_id", "customer_name", "region", "segment", "email"],
        ),
        "orders": pd.DataFrame(
            [["ORD-001", "CUST-001", "2026-08-01", 1000, "PRJ-001", "Completed"]],
            columns=[
                "order_id",
                "customer_id",
                "order_date",
                "order_amount",
                "project_id",
                "status",
            ],
        ),
        "invoices": pd.DataFrame(
            [["INV-001", "ORD-001", "2026-08-02", "2026-10-01", 1000, "Paid"]],
            columns=[
                "invoice_id",
                "order_id",
                "invoice_date",
                "due_date",
                "invoice_amount",
                "status",
            ],
        ),
        "payments": pd.DataFrame(
            [["PAY-001", "INV-001", "2026-08-15", 1000, "NEFT"]],
            columns=[
                "payment_id",
                "invoice_id",
                "payment_date",
                "payment_amount",
                "payment_method",
            ],
        ),
        "projects": pd.DataFrame(
            [["PRJ-001", "Example Project", "Project Owner", 5000, 4500, "Active"]],
            columns=[
                "project_id",
                "project_name",
                "owner",
                "budget",
                "actual_cost",
                "status",
            ],
        ),
    }


def issues_of_type(issues: pd.DataFrame, issue_type: str) -> pd.DataFrame:
    """Return only issues matching one business rule."""
    return issues.loc[issues["issue_type"] == issue_type]


def test_missing_required_field_detection() -> None:
    data = make_valid_data()
    data["customers"].loc[0, "email"] = None
    data["projects"].loc[0, "owner"] = ""

    issues = issues_of_type(
        run_all_validations(data, AS_OF_DATE), "MISSING_REQUIRED_FIELD"
    )

    assert len(issues) == 2
    assert set(issues["entity"]) == {"Customer", "Project"}
    assert set(issues["severity"]) == {"Medium"}


def test_missing_reconciliation_id_is_high_severity() -> None:
    data = make_valid_data()
    data["orders"].loc[0, "customer_id"] = None

    issues = issues_of_type(
        run_all_validations(data, AS_OF_DATE), "MISSING_REQUIRED_FIELD"
    )

    assert len(issues) == 1
    assert issues.iloc[0]["severity"] == "High"


def test_duplicate_business_id_detection_reports_one_issue() -> None:
    data = make_valid_data()
    data["customers"] = pd.concat(
        [data["customers"], data["customers"].copy()], ignore_index=True
    )

    issues = issues_of_type(run_all_validations(data, AS_OF_DATE), "DUPLICATE_RECORD")

    assert len(issues) == 1
    assert issues.iloc[0]["record_id"] == "CUST-001"


def test_broken_customer_order_relationship() -> None:
    data = make_valid_data()
    data["orders"].loc[0, "customer_id"] = "CUST-999"

    issues = issues_of_type(
        run_all_validations(data, AS_OF_DATE), "ORDER_CUSTOMER_MISMATCH"
    )

    assert issues.iloc[0]["record_id"] == "ORD-001"
    assert issues.iloc[0]["severity"] == "High"


def test_broken_invoice_order_relationship() -> None:
    data = make_valid_data()
    data["invoices"].loc[0, "order_id"] = "ORD-999"

    issues = issues_of_type(
        run_all_validations(data, AS_OF_DATE), "INVOICE_ORDER_MISMATCH"
    )

    assert issues.iloc[0]["record_id"] == "INV-001"


def test_invoice_order_amount_mismatch() -> None:
    data = make_valid_data()
    data["invoices"].loc[0, "invoice_amount"] = 1300
    data["payments"].loc[0, "payment_amount"] = 1300

    issues = issues_of_type(
        run_all_validations(data, AS_OF_DATE), "ORDER_INVOICE_AMOUNT_MISMATCH"
    )

    assert len(issues) == 1
    assert "₹1,300" in issues.iloc[0]["description"]
    assert "Difference: ₹300" in issues.iloc[0]["description"]


def test_payment_referencing_nonexistent_invoice() -> None:
    data = make_valid_data()
    data["payments"].loc[0, "invoice_id"] = "INV-999"

    issues = issues_of_type(
        run_all_validations(data, AS_OF_DATE), "PAYMENT_INVOICE_MISMATCH"
    )

    assert issues.iloc[0]["record_id"] == "PAY-001"


def test_overdue_receivable_calculation() -> None:
    data = make_valid_data()
    data["invoices"].loc[0, "due_date"] = "2026-08-01"
    data["payments"] = data["payments"].iloc[0:0].copy()

    issues = issues_of_type(run_all_validations(data, AS_OF_DATE), "OVERDUE_RECEIVABLE")

    assert len(issues) == 1
    assert "₹1,000 outstanding" in issues.iloc[0]["description"]
    assert "37 days overdue" in issues.iloc[0]["description"]


def test_partially_paid_invoice_outstanding_calculation() -> None:
    data = make_valid_data()
    data["invoices"].loc[0, "due_date"] = "2026-08-20"
    data["payments"].loc[0, "payment_amount"] = 400

    issues = issues_of_type(run_all_validations(data, AS_OF_DATE), "OVERDUE_RECEIVABLE")

    assert len(issues) == 1
    assert "₹600 outstanding" in issues.iloc[0]["description"]


def test_overdue_severity_boundary() -> None:
    data = make_valid_data()
    data["orders"] = pd.concat(
        [
            data["orders"],
            pd.DataFrame(
                [["ORD-002", "CUST-001", "2026-08-01", 1000, "PRJ-001", "Completed"]],
                columns=data["orders"].columns,
            ),
        ],
        ignore_index=True,
    )
    data["invoices"] = pd.DataFrame(
        [
            ["INV-001", "ORD-001", "2026-08-01", "2026-08-08", 1000, "Unpaid"],
            ["INV-002", "ORD-002", "2026-08-01", "2026-08-07", 1000, "Unpaid"],
        ],
        columns=data["invoices"].columns,
    )
    data["payments"] = data["payments"].iloc[0:0].copy()

    issues = issues_of_type(run_all_validations(data, AS_OF_DATE), "OVERDUE_RECEIVABLE")

    severities = dict(zip(issues["record_id"], issues["severity"]))
    assert severities == {"INV-001": "Medium", "INV-002": "High"}


def test_project_budget_variance_calculation() -> None:
    data = make_valid_data()
    data["projects"].loc[0, ["budget", "actual_cost"]] = [1000, 1150]

    issues = issues_of_type(
        run_all_validations(data, AS_OF_DATE), "PROJECT_BUDGET_VARIANCE"
    )

    assert len(issues) == 1
    assert "₹150 over budget (15.0%)" in issues.iloc[0]["description"]


def test_project_budget_severity() -> None:
    data = make_valid_data()
    data["projects"] = pd.DataFrame(
        [
            ["PRJ-001", "Medium Variance", "Owner One", 1000, 1200, "Active"],
            ["PRJ-002", "High Variance", "Owner Two", 1000, 1201, "At Risk"],
        ],
        columns=data["projects"].columns,
    )

    issues = issues_of_type(
        run_all_validations(data, AS_OF_DATE), "PROJECT_BUDGET_VARIANCE"
    )

    severities = dict(zip(issues["record_id"], issues["severity"]))
    assert severities == {"PRJ-001": "Medium", "PRJ-002": "High"}


def test_zero_budget_handling_does_not_crash() -> None:
    data = make_valid_data()
    data["projects"].loc[0, ["budget", "actual_cost"]] = [0, 100]

    issues = issues_of_type(
        run_all_validations(data, AS_OF_DATE), "PROJECT_BUDGET_VARIANCE"
    )

    assert issues.empty
