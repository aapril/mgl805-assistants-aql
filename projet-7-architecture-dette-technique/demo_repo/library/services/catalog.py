"""Application service: catalog."""
from library.domain.book import Book
from library.services.notifications import notify_new_book

_BOOKS = {}


def add_book(isbn, title, copies=1):
    book = Book(isbn, title, copies)
    _BOOKS[isbn] = book
    notify_new_book(book)
    return book


def find_book(isbn):
    # TODO: add tests for unknown ISBNs
    return _BOOKS.get(isbn)
