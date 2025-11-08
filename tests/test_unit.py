# tests/test_unit.py
import os
import sys
import pytest

# Ensure imports work when pytest runs from repo root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from services.library_service import (
    add_book_to_catalog,
    return_book_by_patron,
    calculate_late_fee_for_book,
    search_books_in_catalog,
    get_patron_status_report,
)

def test_add_book_invalid_isbn_too_short():
    success, message = add_book_to_catalog("Test Book", "Test Author", "123456789", 3)
    assert success is False
    assert "13 digits" in message.lower()

def test_add_book_invalid_isbn_too_long():
    success, message = add_book_to_catalog("Test Book", "Test Author", "123456789012345", 3)
    assert success is False
    assert "13 digits" in message.lower()

def test_add_book_negative_copies():
    success, message = add_book_to_catalog("Test Book", "Test Author", "1234567890123", -1)
    assert success is False
    assert ("positive" in message.lower()) or ("copies" in message.lower())

def test_add_book_zero_copies():
    success, message = add_book_to_catalog("Test Book", "Test Author", "1234567890123", 0)
    assert success is False
    assert ("positive" in message.lower()) or ("copies" in message.lower())

def test_add_book_long_title():
    long_title = (
        "iedwiuudfehihwefhufhiewhfeuwhifiuwehfiuwfuhiwfuewfhuiewfuhwehfwehuifeiuwihuweiifuh"
        "wfhiueihfwhiuweiueihwfiuwihuewfiehuwfhiuewihfuewiuhfewiuhfwihueuhiewfihuweuhifweiuf"
        "eiuhwfhiuwfihuewfiewhiufhwefuhwiefikklawdlkawndlwalk"
    )
    success, message = add_book_to_catalog(long_title, "Test Author", "1234567890123", 3)
    assert success is False
    assert "title" in message.lower()

def test_add_book_long_author():
    long_author = (
        "iedwiuudfehihwefhufhiewhfeuwhifiuwehfiuwfuhiwfuewfhuiewfuhwehfwehuifeiuwihuweiifuh"
        "wfhiueihfwhiuweiueihwfiuwihuewfiehuwfhiuewihfuewiuhfewiuhfwihueuhiewfihuweuhifweiuf"
        "eiuhwfhiuwfihuewfiewhiufhwefuhwiefikklawdlkawndlwalk"
    )
    success, message = add_book_to_catalog("Test Book", long_author, "1234567890123", 3)
    assert success is False
    assert "author" in message.lower()

def test_return_book_not_borrowed():
    success, msg = return_book_by_patron("999999", 2)
    assert success is False
    assert "no active borrow" in msg.lower()

def test_calculate_fee_no_record():
    fee = calculate_late_fee_for_book("000000", 1)
    assert fee["fee_amount"] == 0.0
    assert "no record" in fee["status"].lower()

def test_search_books_by_title():
    results = search_books_in_catalog("1984", "title")
    assert any("1984" in b.get("title", "") for b in results)

def test_patron_status_invalid_id():
    report = get_patron_status_report("abc123")
    assert "error" in str(report).lower()
