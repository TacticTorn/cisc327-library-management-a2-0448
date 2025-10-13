import pytest
from library_service import (
    add_book_to_catalog,
    return_book_by_patron,
    calculate_late_fee_for_book,
    search_books_in_catalog,
    get_patron_status_report,
)

def test_add_book_valid_input():
    """Test adding a book with valid input."""
    success, message = add_book_to_catalog("Test Book", "Test Author", "1234567890123", 3)
    
    assert success == True
    assert "successfully added" in message.lower()

def test_add_book_invalid_isbn_too_short():
    """Test adding a book with ISBN too short."""
    success, message = add_book_to_catalog("Test Book", "Test Author", "123456789", 3)
    
    assert success == False
    assert "13 digits" in message

def test_add_book_invalid_isbn_too_long():
    """Test adding a book with ISBN too long."""
    success, message = add_book_to_catalog("Test Book", "Test Author", "123456789012345", 3)
    assert success is False
    assert "13 digits" in message.lower()
    #Unable to be tested since it does not allow digits exceeding 13
    

def test_add_book_negative_copies():
    """Test adding a book with negative copies."""
    success, message = add_book_to_catalog("Test Book", "Test Author", "1234567890123", -1)
    assert success is False
    assert "positive" in message.lower() or "copies" in message.lower()

def test_add_book_zero_copies():
    """Test adding a book with zero copies."""
    success, message = add_book_to_catalog("Test Book", "Test Author", "1234567890123", 0)
    assert success is False
    assert "positive" in message.lower() or "copies" in message.lower()

def test_add_book_long_title():
    """Test adding a book with a title longer than 200 characters."""
    long_title = "iedwiuudfehihwefhufhiewhfeuwhifiuwehfiuwfuhiwfuewfhuiewfuhwehfwehuifeiuwihuweiifuhwfhiueihfwhiuweiueihwfiuwihuewfiehuwfhiuewihfuewiuhfewiuhfwihueuhiewfihuweuhifweiufeiuhwfhiuwfihuewfiewhiufhwefuhwiefikklawdlkawndlwalk"
    success, message = add_book_to_catalog(long_title, "Test Author", "1234567890123", 3)
    assert success is False
    assert "title" in message.lower()
    #Unable to be tested since it does not allow characters exceeding 200


def test_add_book_long_author():
    """Test adding a book with an author name longer than 100 characters."""
    long_author = "iedwiuudfehihwefhufhiewhfeuwhifiuwehfiuwfuhiwfuewfhuiewfuhwehfwehuifeiuwihuweiifuhwfhiueihfwhiuweiueihwfiuwihuewfiehuwfhiuewihfuewiuhfewiuhfwihueuhiewfihuweuhifweiufeiuhwfhiuwfihuewfiewhiufhwefuhwiefikklawdlkawndlwalk"
    success, message = add_book_to_catalog("Test Book", long_author, "1234567890123", 3)
    assert success is False
    assert "author" in message.lower()
    #Unable to be tested since it does not allow characters exceeding 100
    
def test_add_book_duplicate_isbn():
    """Test adding a book with a duplicate ISBN (should fail if already exists)."""
    #First add should succeed
    success, message = add_book_to_catalog("test", "test", "9999999999999", 2)
    assert success is True
    #Second add with same ISBN should fail
    success, message = add_book_to_catalog("test2", "test2", "9999999999999", 2)
    assert success is False
    assert "isbn" in message.lower() or "duplicate" in message.lower()

#Task 2 tests
def test_return_book_not_borrowed():
    """Return attempt for book not borrowed by patron."""
    success, msg = return_book_by_patron("999999", 2)
    assert success is False
    assert "no active borrow" in msg.lower()

def test_calculate_fee_no_record():
    """Should handle missing record gracefully."""
    fee = calculate_late_fee_for_book("000000", 1)
    assert fee["fee_amount"] == 0.0
    assert "no record" in fee["status"].lower()

def test_search_books_by_title():
    results = search_books_in_catalog("1984", "title")
    assert any("1984" in b["title"] for b in results)

def test_patron_status_invalid_id():
    report = get_patron_status_report("abc123")
    assert "error" in report