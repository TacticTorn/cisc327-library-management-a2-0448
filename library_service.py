"""
Library Service Module - Business Logic Functions
Contains all the core business logic for the Library Management System
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from database import (
    get_book_by_id, get_book_by_isbn, get_patron_borrow_count,  get_patron_borrowed_books,
    insert_book, insert_borrow_record, update_book_availability,
    update_borrow_record_return_date, get_all_books
)

def add_book_to_catalog(title: str, author: str, isbn: str, total_copies: int) -> Tuple[bool, str]:
    """
    Add a new book to the catalog.
    Implements R1: Book Catalog Management
    
    Args:
        title: Book title (max 200 chars)
        author: Book author (max 100 chars)
        isbn: 13-digit ISBN
        total_copies: Number of copies (positive integer)
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Input validation
    if not title or not title.strip():
        return False, "Title is required."
    
    if len(title.strip()) > 200:
        return False, "Title must be less than 200 characters."
    
    if not author or not author.strip():
        return False, "Author is required."
    
    if len(author.strip()) > 100:
        return False, "Author must be less than 100 characters."
    
    if len(isbn) != 13:
        return False, "ISBN must be exactly 13 digits."
    
    if not isinstance(total_copies, int) or total_copies <= 0:
        return False, "Total copies must be a positive integer."
    
    # Check for duplicate ISBN
    existing = get_book_by_isbn(isbn)
    if existing:
        return False, "A book with this ISBN already exists."
    
    # Insert new book
    success = insert_book(title.strip(), author.strip(), isbn, total_copies, total_copies)
    if success:
        return True, f'Book "{title.strip()}" has been successfully added to the catalog.'
    else:
        return False, "Database error occurred while adding the book."

def borrow_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    """
    Allow a patron to borrow a book.
    Implements R3 as per requirements  
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book to borrow
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."
    
    # Check if book exists and is available
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found."
    
    if book['available_copies'] <= 0:
        return False, "This book is currently not available."
    
    # Check patron's current borrowed books count
    current_borrowed = get_patron_borrow_count(patron_id)
    
    if current_borrowed > 5:
        return False, "You have reached the maximum borrowing limit of 5 books."
    
    # Create borrow record
    borrow_date = datetime.now()
    due_date = borrow_date + timedelta(days=14)
    
    # Insert borrow record and update availability
    borrow_success = insert_borrow_record(patron_id, book_id, borrow_date, due_date)
    if not borrow_success:
        return False, "Database error occurred while creating borrow record."
    
    availability_success = update_book_availability(book_id, -1)
    if not availability_success:
        return False, "Database error occurred while updating book availability."
    
    return True, f'Successfully borrowed "{book["title"]}". Due date: {due_date.strftime("%Y-%m-%d")}.'

def return_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    """
    Process book return by a patron.
    """
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."

    try:
        book_id = int(str(book_id).strip())
    except ValueError:
        return False, "Invalid Book ID."

    borrowed_books = get_patron_borrowed_books(patron_id)

    #find the matching active borrow record for this book
    active_record = next((b for b in borrowed_books if b["book_id"] == book_id), None)
    if not active_record:
        return False, "No active borrow record found for this patron and book."

    #update return record and availability
    return_date = datetime.now()
    updated = update_borrow_record_return_date(patron_id, book_id, return_date)
    if not updated:
        return False, "Database error occurred while updating return record."

    availability_updated = update_book_availability(book_id, +1)
    if not availability_updated:
        return False, "Database error occurred while updating book availability."

    #calculate late fee
    fee_info = calculate_late_fee_for_book(patron_id, book_id)
    fee_amt = fee_info.get("fee_amount", 0.0)

    if fee_amt > 0:
        return True, f'Book returned with late fee ${fee_amt:.2f} ({fee_info["days_overdue"]} days overdue).'
    else:
        return True, "Book returned successfully. No late fees."

    #update return record
    return_date = datetime.now()
    updated = update_borrow_record_return_date(str(patron_id).strip(), book_id, return_date)
    if not updated:
        return False, "Database error occurred while updating return record."

    if not update_book_availability(book_id, +1):
        return False, "Database error occurred while updating book availability."

    # --- Late fee calculation ---
    late_fee = calculate_late_fee_for_book(str(patron_id).strip(), book_id)
    fee_amt = late_fee.get("fee_amount", 0.0)

    if fee_amt > 0:
        return True, f'Book returned with late fee ${fee_amt:.2f} ({late_fee["days_overdue"]} days overdue).'
    return True, "Book returned successfully. No late fees."

def calculate_late_fee_for_book(patron_id: str, book_id: int) -> Dict:
    """
    Calculate late fees for a specific book.
    """
    # Find the borrow record for this patron and book (active or returned)
    from database import get_db_connection
    conn = get_db_connection()
    record = conn.execute(
        '''SELECT * FROM borrow_records WHERE patron_id = ? AND book_id = ? ORDER BY borrow_date DESC LIMIT 1''',
        (patron_id, book_id)
    ).fetchone()
    conn.close()
    if not record:
        return {"fee_amount": 0.0, "days_overdue": 0, "status": "No record found"}

    due = datetime.fromisoformat(record["due_date"])
    # Use return_date if present, otherwise today
    if record["return_date"]:
        returned = datetime.fromisoformat(record["return_date"])
    else:
        returned = datetime.now()
    days_overdue = (returned - due).days

    if days_overdue <= 0:
        return {"fee_amount": 0.0, "days_overdue": 0, "status": "Returned on time"}

    if days_overdue <= 7:
        fee = days_overdue * 0.5
    else:
        fee = 3.5 + (days_overdue - 7) * 1.0
    fee = round(min(fee, 15.0), 2)

    return {"fee_amount": fee, "days_overdue": days_overdue, "status": "Overdue"}


def search_books_in_catalog(search_term: str, search_type: str) -> List[Dict]:
    """
    Search for books in the catalog.
    """
    if not search_term or not search_type:
        return []

    term = search_term.lower()
    books = get_all_books()
    results = []

    for b in books:
        if search_type == "title" and term in b["title"].lower():
            results.append(b)
        elif search_type == "author" and term in b["author"].lower():
            results.append(b)
        elif search_type == "isbn" and term == b["isbn"]:
            results.append(b)

    return results

def get_patron_status_report(patron_id: str) -> Dict:
    """
    Get status report for a patron.
    """
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return {"error": "Invalid Patron ID format."}

    borrowed_books = get_patron_borrowed_books(patron_id)
    total_late_fees = 0.0

    for book in borrowed_books:
        fee_info = calculate_late_fee_for_book(patron_id, book["book_id"])
        total_late_fees += fee_info.get("fee_amount", 0.0)

    return {
        "patron_id": patron_id,
        "borrowed_books": borrowed_books,
        "total_late_fees": round(total_late_fees, 2),
        "borrowed_count": len(borrowed_books)

    }
