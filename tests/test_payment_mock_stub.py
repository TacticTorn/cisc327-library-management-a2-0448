# tests/test_payment_mock_stub.py
import os
import sys
import pytest
from unittest.mock import Mock

# Ensure imports work when pytest runs from repo root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from services.library_service import pay_late_fees, refund_late_fee_payment

# ---- STUBBED FUNCTIONS ----
@pytest.fixture
def stub_calculate_fee(mocker):
    """Stub calculate_late_fee_for_book to avoid real DB call."""
    return mocker.patch("services.library_service.calculate_late_fee_for_book")

@pytest.fixture
def stub_get_book(mocker):
    """Stub get_book_by_id to avoid real DB call."""
    return mocker.patch("services.library_service.get_book_by_id")

# ---- PAY_LATE_FEES TESTS ----
def test_pay_late_fees_success(stub_get_book, stub_calculate_fee):
    stub_get_book.return_value = {"book_id": 1, "title": "Mocked Book"}
    stub_calculate_fee.return_value = {"fee_amount": 5.0, "status": "Overdue"}

    mock_gateway = Mock()
    mock_gateway.process_payment.return_value = {"status": "success"}

    success, msg = pay_late_fees("123456", 1, mock_gateway)
    assert success is True
    assert "completed successfully" in msg.lower()
    mock_gateway.process_payment.assert_called_once_with("123456", 5.0)


def test_pay_late_fees_declined(stub_get_book, stub_calculate_fee):
    stub_get_book.return_value = {"book_id": 1, "title": "Declined Book"}
    stub_calculate_fee.return_value = {"fee_amount": 7.0, "status": "Overdue"}

    mock_gateway = Mock()
    mock_gateway.process_payment.return_value = {"status": "failed", "message": "Card declined"}

    success, msg = pay_late_fees("123456", 1, mock_gateway)
    assert not success
    assert "declined" in msg.lower()
    mock_gateway.process_payment.assert_called_once_with("123456", 7.0)


def test_pay_late_fees_invalid_patron(stub_get_book, stub_calculate_fee):
    mock_gateway = Mock()
    success, msg = pay_late_fees("12A45", 1, mock_gateway)
    assert not success
    assert "invalid patron" in msg.lower()
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_no_fee(stub_get_book, stub_calculate_fee):
    stub_get_book.return_value = {"book_id": 1, "title": "No Fee Book"}
    stub_calculate_fee.return_value = {"fee_amount": 0.0, "status": "Returned on time"}

    mock_gateway = Mock()
    success, msg = pay_late_fees("123456", 1, mock_gateway)
    assert not success
    assert "no outstanding" in msg.lower()
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_network_error(stub_get_book, stub_calculate_fee):
    stub_get_book.return_value = {"book_id": 1, "title": "Network Error Book"}
    stub_calculate_fee.return_value = {"fee_amount": 10.0, "status": "Overdue"}

    mock_gateway = Mock()
    mock_gateway.process_payment.side_effect = Exception("Timeout")

    success, msg = pay_late_fees("123456", 1, mock_gateway)
    assert not success
    assert "network error" in msg.lower()
    mock_gateway.process_payment.assert_called_once_with("123456", 10.0)

# ---- REFUND TESTS ----
def test_refund_success():
    mock_gateway = Mock()
    mock_gateway.refund_payment.return_value = {"status": "success"}

    success, msg = refund_late_fee_payment("TX123", 5.0, mock_gateway)
    assert success
    assert "processed successfully" in msg.lower()
    mock_gateway.refund_payment.assert_called_once_with("TX123", 5.0)


def test_refund_invalid_transaction():
    mock_gateway = Mock()
    success, msg = refund_late_fee_payment("", 5.0, mock_gateway)
    assert not success
    assert "invalid transaction" in msg.lower()
    mock_gateway.refund_payment.assert_not_called()


def test_refund_negative_amount():
    mock_gateway = Mock()
    success, msg = refund_late_fee_payment("TX123", -5.0, mock_gateway)
    assert not success
    assert "greater than zero" in msg.lower()
    mock_gateway.refund_payment.assert_not_called()


def test_refund_exceeds_limit():
    mock_gateway = Mock()
    success, msg = refund_late_fee_payment("TX123", 16.0, mock_gateway)
    assert not success
    assert "exceeds" in msg.lower()
    mock_gateway.refund_payment.assert_not_called()


def test_refund_gateway_failure():
    mock_gateway = Mock()
    mock_gateway.refund_payment.return_value = {"status": "failed", "message": "Refund declined"}

    success, msg = refund_late_fee_payment("TX999", 10.0, mock_gateway)
    assert not success
    assert "refund failed" in msg.lower()
    mock_gateway.refund_payment.assert_called_once_with("TX999", 10.0)
