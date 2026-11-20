"""Infrastructure: database access."""
import sqlite3

_CONNECTION = None


def connect(path="library.db"):
    global _CONNECTION
    # HACK: a single shared connection; replace with a pool before going to production
    if _CONNECTION is None:
        _CONNECTION = sqlite3.connect(path, check_same_thread=False)
    return _CONNECTION


def save_loan(loan):
    connect().execute("INSERT INTO loans VALUES (?, ?, ?)", (loan.isbn, loan.member_id, loan.start.isoformat()))


def count_loans(isbn):
    row = connect().execute("SELECT COUNT(*) FROM loans WHERE isbn = ?", (isbn,)).fetchone()
    return row[0]
