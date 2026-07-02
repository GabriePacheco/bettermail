import unittest
from unittest.mock import patch

from starlette.requests import Request

from app.main import rewrite
from app.models import OfficeUser, RewriteRequest
from app.openai_service import RewriteResult


def usage_for(plan="trial", status="trial"):
    return {
        "allowed": True,
        "status": status,
        "plan": plan,
        "used": 0,
        "limit": 10,
        "remaining": 10,
        "trial_limit": 10,
        "trial_used": 0,
        "monthlyLimit": 300 if plan == "pro" else 0,
        "monthlyUsed": 0,
        "upgradeRequired": False,
        "message": "",
    }


class CustomToneTests(unittest.TestCase):
    def make_request(self):
        return Request({
            "type": "http",
            "method": "POST",
            "path": "/rewrite",
            "headers": [],
            "client": ("127.0.0.1", 12000),
        })

    def make_payload(self):
        return RewriteRequest(
            user=OfficeUser(email="user@example.com"),
            text="Confirma la reunion de manana",
            tone="custom",
            custom_tone="Cercano, optimista y concreto",
        )

    @patch("app.main.consume_rewrite_credit")
    @patch("app.main.rewrite_email_text")
    @patch("app.main.check_usage_allowed", return_value=usage_for())
    def test_trial_cannot_use_custom_tone(self, _, rewrite_mock, consume_mock):
        response = rewrite(self.make_request(), self.make_payload())

        self.assertFalse(response["allowed"])
        self.assertEqual(response["status"], "pro_required")
        rewrite_mock.assert_not_called()
        consume_mock.assert_not_called()

    @patch(
        "app.main.consume_rewrite_credit",
        return_value={
            "used": 1,
            "remaining": 299,
            "trial_used": 0,
            "monthlyUsed": 1,
        },
    )
    @patch("app.main.rewrite_email_text")
    @patch("app.main.check_usage_allowed", return_value=usage_for("pro", "active"))
    def test_active_pro_sends_custom_personality_to_openai(self, _, rewrite_mock, __):
        rewrite_mock.return_value = RewriteResult(
            text="Correo mejorado",
            model="test-model",
            prompt_tokens=10,
            cached_prompt_tokens=0,
            completion_tokens=5,
            total_tokens=15,
            estimated_cost_usd=0.0001,
            pricing_label="test",
        )

        response = rewrite(self.make_request(), self.make_payload())

        self.assertTrue(response["allowed"])
        self.assertEqual(
            rewrite_mock.call_args.kwargs["custom_tone"],
            "Cercano, optimista y concreto",
        )


if __name__ == "__main__":
    unittest.main()
