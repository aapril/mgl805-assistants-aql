import unittest
from example.password_policy import is_valid_password


class PasswordPolicyTests(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(is_valid_password("longpassword7"))

    def test_too_short(self):
        self.assertFalse(is_valid_password("abc1"))
