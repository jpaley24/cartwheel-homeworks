"""Tests for the student-added check_return_eligibility tool (HW1 Part A)."""

from __future__ import annotations

import pytest

from agent import tools
from agent.agent import TOOLS_BY_ROLE, check_return_eligibility
from agent.auth import AuthContext

SHOPPER_1 = AuthContext(user_id=1, role="shopper")
MERCHANT_2 = AuthContext(user_id=9002, role="merchant", store_id=2)
SUPPORT = AuthContext(user_id=9501, role="support")


def test_registered_for_every_role() -> None:
    for role in ("shopper", "merchant", "support"):
        assert check_return_eligibility in TOOLS_BY_ROLE[role]


def test_eligible_order_inside_window(world: dict) -> None:
    result = tools.check_return_eligibility(SHOPPER_1, 4127)
    assert result["ok"] is True
    assert result["eligible"] is True
    assert result["return_window_days"] == 30
    assert result["days_past_window"] == 0
    assert result["days_remaining"] == 30 - result["days_since_delivery"]
    assert "cw-returns" in result["policy_ids"]


def test_expired_order_reports_days_past_window(world: dict) -> None:
    result = tools.check_return_eligibility(SHOPPER_1, 3980)
    assert result["eligible"] is False
    assert result["reason_code"] == "window_expired"
    assert result["days_since_delivery"] == 45
    assert result["days_past_window"] == 15


def test_shipped_order_is_not_eligible_until_delivered(world: dict) -> None:
    result = tools.check_return_eligibility(SUPPORT, 880)
    assert result["eligible"] is False
    assert result["reason_code"] == "not_delivered"
    assert result["days_since_delivery"] is None
    assert "until it has been delivered" in result["reason"]


def test_store_override_window_and_fee(world: dict) -> None:
    # Order 2319 is a Cascade Audio order (restocking-fee store).
    result = tools.check_return_eligibility(SUPPORT, 2319)
    assert result["restocking_fee"]["may_apply"] is True
    assert result["restocking_fee"]["max_percent"] == 15
    assert "store-cascade-audio-policy" in result["policy_ids"]


def test_access_matrix_is_enforced_before_any_detail(world: dict) -> None:
    denied = tools.check_return_eligibility(MERCHANT_2, 4127)
    assert denied["ok"] is False
    assert denied["error"] == "permission_denied"
    assert "status" not in denied and "eligible" not in denied
    assert tools.check_return_eligibility(SUPPORT, 4127)["ok"] is True


def test_unknown_order(world: dict) -> None:
    result = tools.check_return_eligibility(SUPPORT, 99999999)
    assert result["ok"] is False and result["error"] == "not_found"


@pytest.mark.parametrize(
    "order_id,issue",
    [(8001, "reversed_chronology"), (8002, "missing_delivery_date"), (8003, "store_mismatch")],
)
def test_inconsistent_records_are_flagged_not_timelined(world: dict, order_id: int, issue: str) -> None:
    result = tools.check_return_eligibility(SUPPORT, order_id)
    assert result["ok"] is True
    assert result["eligible"] is None
    assert result["data_issue"] == issue
    assert result["days_since_delivery"] is None
    assert result["days_past_window"] is None
