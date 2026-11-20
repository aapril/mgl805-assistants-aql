"""Presentation: public HTTP routes."""
from library.services import catalog, loans


def validate_member_payload(payload):
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


def post_checkout(payload):
    errors = validate_member_payload(payload.get("member", {}))
    if errors:
        return 400, {"errors": errors}
    return 200, loans.checkout(payload["isbn"], payload["member"])


def get_book(isbn):
    book = catalog.find_book(isbn)
    return (200, book.__dict__) if book else (404, {"error": "not found"})
