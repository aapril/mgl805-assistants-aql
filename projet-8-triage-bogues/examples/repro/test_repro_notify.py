"""Reproduction written by a person: a late return must notify the member."""
import unittest
from unittest import mock
from library.api import routes


class LateReturn(unittest.TestCase):
    def test_late_return_notifies_the_member(self):
        with mock.patch("library.infrastructure.mailer.send") as send:
            routes.post_return({"member": {"id": "m1", "name": "Ana", "email": "ana@example.org"}, "days_late": 3})
        send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
