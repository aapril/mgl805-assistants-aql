"""Reproduction written by a person: an on-time return must not fail."""
import unittest
from library.services import fines


class OnTimeReturn(unittest.TestCase):
    def test_on_time_return_has_a_summary(self):
        self.assertEqual(fines.compute_summary(0)["total"], 0)


if __name__ == "__main__":
    unittest.main()
