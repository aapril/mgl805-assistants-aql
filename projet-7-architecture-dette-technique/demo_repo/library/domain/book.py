"""Domain: books."""
from dataclasses import dataclass


@dataclass
class Book:
    isbn: str
    title: str
    copies: int = 1

    def is_available(self, on_loan):
        # TODO: handle reserved copies once the reservation requirement is specified
        return self.copies - on_loan > 0
