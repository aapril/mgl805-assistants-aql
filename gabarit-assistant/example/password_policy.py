"""Password policy of the example application: the artifact under assessment."""
MIN_LENGTH = 8


def is_valid_password(password: str) -> bool:
    return len(password) >= MIN_LENGTH and any(c.isdigit() for c in password)
