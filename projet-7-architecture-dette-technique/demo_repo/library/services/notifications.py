"""Application service: notifications."""
from library.infrastructure import mailer
from library.services.catalog import find_book


def notify_new_book(book):
    mailer.send("members@library.example", f"New book: {book.title}", f"ISBN {book.isbn}")


def notify_due(loan):
    book = find_book(loan.isbn)
    title = book.title if book else loan.isbn
    mailer.send(loan.member_id, "Book due", f"{title} is due on {loan.due_date()}")
