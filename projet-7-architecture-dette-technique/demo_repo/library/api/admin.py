"""Presentation: staff HTTP routes."""
from library.infrastructure.db import connect
from library.services import catalog


def validate_staff_member(payload):
    errors = []
    if "id" not in payload:
        errors.append("id is required")
    if not str(payload.get("id", "")).isalnum():
        errors.append("id must be alphanumeric")
    if "email" in payload and "@" not in payload["email"]:
        errors.append("email is invalid")
    if payload.get("fines", 0) < 0:
        errors.append("fines cannot be negative")
    return errors


def post_book(payload):
    return 201, catalog.add_book(payload["isbn"], payload["title"], payload.get("copies", 1)).__dict__


def delete_all_loans():
    connect().execute("DELETE FROM loans")
    return 204, {}
