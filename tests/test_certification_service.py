import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.certification_service import activate_certification_access


def settings(*, enabled=True, secret="BM-CERT-test-key", days=7):
    return SimpleNamespace(
        certification_access_enabled=enabled,
        certification_license_secret=secret,
        certification_access_days=days,
    )


class CertificationServiceTests(unittest.TestCase):
    def test_disabled_access_rejects_before_reading_user_data(self):
        with (
            patch("app.certification_service.get_settings", return_value=settings(enabled=False)),
            patch("app.certification_service.get_or_create_mailbox_user") as get_user,
        ):
            with self.assertRaises(HTTPException) as context:
                activate_certification_access("reviewer@example.com", "BM-CERT-test-key", 10)

        self.assertEqual(context.exception.status_code, 503)
        get_user.assert_not_called()

    def test_invalid_license_rejects_before_reading_user_data(self):
        with (
            patch("app.certification_service.get_settings", return_value=settings()),
            patch("app.certification_service.get_or_create_mailbox_user") as get_user,
        ):
            with self.assertRaises(HTTPException) as context:
                activate_certification_access("reviewer@example.com", "wrong-key", 10)

        self.assertEqual(context.exception.status_code, 401)
        get_user.assert_not_called()

    def test_existing_paid_pro_is_never_replaced(self):
        user_ref = MagicMock()
        user_data = {
            "plan": "pro",
            "status": "active",
            "subscriptionStatus": "active",
            "paymentProvider": "payphone_cajita",
            "currentPeriodEnd": datetime.now(timezone.utc) + timedelta(days=20),
        }
        with (
            patch("app.certification_service.get_settings", return_value=settings()),
            patch(
                "app.certification_service.get_or_create_mailbox_user",
                return_value=(user_ref, user_data),
            ),
            patch("app.certification_service.activate_certification_subscription") as activate,
        ):
            result = activate_certification_access(
                "reviewer@example.com", "BM-CERT-test-key", 10
            )

        self.assertTrue(result["activated"])
        self.assertIn("ya tiene BetterMail Pro", result["message"])
        activate.assert_not_called()

    def test_activation_uses_seven_day_nonpayment_subscription(self):
        user_ref = MagicMock()
        db = MagicMock()
        period_end = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        with (
            patch("app.certification_service.get_settings", return_value=settings()),
            patch(
                "app.certification_service.get_or_create_mailbox_user",
                return_value=(user_ref, {"plan": "trial", "status": "trial"}),
            ),
            patch(
                "app.certification_service.activate_certification_subscription",
                return_value={
                    "plan": "pro",
                    "status": "active",
                    "currentPeriodEnd": period_end,
                },
            ) as activate,
            patch("app.certification_service.get_db", return_value=db),
        ):
            result = activate_certification_access(
                "Reviewer@Example.com", "BM-CERT-test-key", 10
            )

        self.assertEqual(result["valid_until"], period_end)
        self.assertEqual(activate.call_args.kwargs["period_days"], 7)
        activation_payload = (
            db.collection.return_value.document.return_value.set.call_args.args[0]
        )
        self.assertNotIn("licenseKey", activation_payload)
        self.assertNotIn("email", activation_payload)
        user_ref.update.assert_called_once()


if __name__ == "__main__":
    unittest.main()
