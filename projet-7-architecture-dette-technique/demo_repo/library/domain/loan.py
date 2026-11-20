"""Domain: loans."""
from dataclasses import dataclass
from datetime import date, timedelta
from library.infrastructure.db import save_loan


@dataclass
class Loan:
    isbn: str
    member_id: str
    start: date

    def due_date(self, days=21):
        return self.start + timedelta(days=days)

    def persist(self):
        save_loan(self)
