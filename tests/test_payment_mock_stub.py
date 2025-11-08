# tests/test_payment_mock_stub.py
import os
import sys
import pytest
from unittest.mock import Mock

# ---------------------------------------------------------------------
# Ensure imports work when pytest runs from project root
# ---------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from services.library_service import pay_late_fees, refund_late_fee_payment


# ---------------------------------------------------------------------
# Fixtures for Stubbing (Database Dependencies)
# ---------------------------------------------------------------------
@pytest.fixture
def stub_get_book(mocker):
    """Stub get_book_by_id to simulate DB lookup."""
    return mocker.patch("services.library_service.get_book_by_id")


@pytest.fixture
def stub_calculate_fee(mocker):
    """Stub calculate_late_fee_for_book to simulate DB fee calculation."""
    return mocker.patch("services.library_service.calculate_late_fee_for_book")


# ---------------------------------------------------------------------
# Tests for pay_late_fees()
# ---------------------------------------------------------------------
def test_pay_late_fees_success(stub_get_book, stub_calculate_fee):
    """Successful payment through the mocked gateway."""
    stub_get_book.return_value = {"book_id": 1, "title": "Mock Book"}
    stub_calculate_fee.return_value = {"fee_amount": 5.0}

    mock_gateway = Mock()
    mock_gateway.process_payment.return_value = (True, "txn_123", "Success")

    success, msg, txn = pay_late_fees("123456", 1, mock_gateway)

    assert success is True
    assert "payment successful" in msg.lower()
    assert txn == "txn_123"
    mock_gateway.process_payment.assert_called_once_with(
        patron_id="123456", amount=5.0, description="Late fees for 'Mock Book'"
    )


def test_pay_late_fees_invalid_patron(stub_get_book, stub_calculate_fee):
    """Invalid patron ID should prevent payment and skip gateway call."""
    mock_gateway = Mock()
    success, msg, txn = pay_late_fees("12A45", 1, mock_gateway)

    assert not success
    assert "invalid patron" in msg.lower()
    assert txn is None
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_no_fee(stub_get_book, stub_calculate_fee):
    """No outstanding fee should skip payment gateway call."""
    stub_get_book.return_value = {"book_id": 1, "title": "No Fee Book"}
    stub_calculate_fee.return_value = {"fee_amount": 0.0}

    mock_gateway = Mock()
    success, msg, txn = pay_late_fees("123456", 1, mock_gateway)

    assert not success
    assert "no late fees" in msg.lower()
    assert txn is None
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_book_not_found(stub_get_book, stub_calculate_fee):
    """If book is missing, should fail before contacting gateway."""
    stub_get_book.return_value = None
    stub_calculate_fee.return_value = {"fee_amount": 4.0}

    mock_gateway = Mock()
    success, msg, txn = pay_late_fees("123456", 99, mock_gateway)

    assert not success
    assert "book not found" in msg.lower()
    assert txn is None
    mock_gateway.process_payment.assert_not_called()


def test_pay_late_fees_gateway_failure(stub_get_book, stub_calculate_fee):
    """Simulate a network exception from payment gateway."""
    stub_get_book.return_value = {"book_id": 1, "title": "Network Error Book"}
    stub_calculate_fee.return_value = {"fee_amount": 10.0}

    mock_gateway = Mock()
    mock_gateway.process_payment.side_effect = Exception("Timeout")

    success, msg, txn = pay_late_fees("123456", 1, mock_gateway)

    assert not success
    assert "payment processing error" in msg.lower()
    assert txn is None
    mock_gateway.process_payment.assert_called_once()


def test_pay_late_fees_declined_by_gateway(stub_get_book, stub_calculate_fee):
    """Simulate gateway returning a failed payment response."""
    stub_get_book.return_value = {"book_id": 1, "title": "Declined Book"}
    stub_calculate_fee.return_value = {"fee_amount": 12.5}

    mock_gateway = Mock()
    mock_gateway.process_payment.return_value = (False, None, "Card declined")

    success, msg, txn = pay_late_fees("123456", 1, mock_gateway)

    assert not success
    assert "payment failed" in msg.lower()
    assert txn is None
    mock_gateway.process_payment.assert_called_once()


# ---------------------------------------------------------------------
# Tests for refund_late_fee_payment()
# ---------------------------------------------------------------------
def test_refund_success():
    """Successful refund through the mocked gateway."""
    mock_gateway = Mock()
    mock_gateway.refund_payment.return_value = (True, "Refund OK")

    success, msg = refund_late_fee_payment("txn_123456", 5.0, mock_gateway)

    assert success
    assert "refund ok" in msg.lower()
    mock_gateway.refund_payment.assert_called_once_with("txn_123456", 5.0)


def test_refund_invalid_transaction_id():
    """Invalid transaction ID should skip gateway call."""
    mock_gateway = Mock()
    success, msg = refund_late_fee_payment("bad_txn", 5.0, mock_gateway)

    assert not success
    assert "invalid transaction" in msg.lower()
    mock_gateway.refund_payment.assert_not_called()


def test_refund_negative_amount():
    """Negative refund should be rejected."""
    mock_gateway = Mock()
    success, msg = refund_late_fee_payment("txn_123456", -5.0, mock_gateway)

    assert not success
    assert "greater than 0" in msg.lower()
    mock_gateway.refund_payment.assert_not_called()


def test_refund_exceeds_limit():
    """Refund over $15 limit should be rejected."""
    mock_gateway = Mock()
    success, msg = refund_late_fee_payment("txn_123456", 20.0, mock_gateway)

    assert not success
    assert "exceeds" in msg.lower()
    mock_gateway.refund_payment.assert_not_called()


def test_refund_gateway_failure():
    """Simulate refund failure from gateway."""
    mock_gateway = Mock()
    mock_gateway.refund_payment.return_value = (False, "Card error")

    success, msg = refund_late_fee_payment("txn_123456", 10.0, mock_gateway)

    assert not success
    assert "refund failed" in msg.lower()
    mock_gateway.refund_payment.assert_called_once_with("txn_123456", 10.0)


def test_refund_gateway_exception():
    """Simulate gateway throwing an exception."""
    mock_gateway = Mock()
    mock_gateway.refund_payment.side_effect = Exception("Timeout error")

    success, msg = refund_late_fee_payment("txn_123456", 5.0, mock_gateway)

    assert not success
    assert "refund processing error" in msg.lower()
    mock_gateway.refund_payment.assert_called_once_with("txn_123456", 5.0)
