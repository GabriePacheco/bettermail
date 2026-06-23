import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.usage_service import consume_rewrite_credit


class FakeUserRef:
    def __init__(self):
        self.updates = []

    def update(self, payload):
        self.updates.append(payload)


class UsageResilienceTests(unittest.TestCase):
    @patch("app.usage_service.register_usage", side_effect=RuntimeError("telemetry down"))
    def test_telemetry_failure_does_not_fail_a_successful_rewrite(self, _register):
        user_ref = FakeUserRef()
        result = consume_rewrite_credit(
            user=SimpleNamespace(email="user@example.com"),
            usage_info={
                "user_ref": user_ref,
                "usage_bucket": "monthly",
                "plan": "pro",
                "used": 6,
                "limit": 300,
                "trial_used": 24,
                "monthlyUsed": 6,
            },
            metadata={"action": "rewrite"},
        )

        self.assertEqual(result["used"], 7)
        self.assertEqual(result["monthlyUsed"], 7)
        self.assertEqual(len(user_ref.updates), 1)


if __name__ == "__main__":
    unittest.main()
