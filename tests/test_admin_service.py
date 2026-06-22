import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.admin_service import _audit_metadata, admin_activate_user, block_user, unblock_user
from app.security import verify_admin_secret


class AdminServiceTests(unittest.TestCase):
    def test_audit_metadata_drops_sensitive_or_unknown_fields(self):
        result = _audit_metadata({
            "reason": "support",
            "planId": "pro_monthly",
            "cardToken": "must-not-be-logged",
            "email": "must-not-be-logged@example.com",
            "secret": "must-not-be-logged",
        })

        self.assertEqual(result, {
            "reason": "support",
            "planId": "pro_monthly",
        })

    def test_admin_secret_rejects_public_app_secret(self):
        settings = SimpleNamespace(admin_api_secret="private-admin-secret")
        with patch("app.security.get_settings", return_value=settings):
            with self.assertRaises(HTTPException) as context:
                verify_admin_secret("public-app-secret")

        self.assertEqual(context.exception.status_code, 401)

    def test_block_user_preserves_previous_status(self):
        db = MagicMock()
        user_ref = MagicMock()
        snapshot = MagicMock(exists=True)
        snapshot.to_dict.return_value = {
            "status": "active",
            "plan": "pro",
            "subscriptionStatus": "active",
        }
        user_ref.get.return_value = snapshot
        expected = {"exists": True, "status": "blocked"}

        with (
            patch("app.admin_service.get_db", return_value=db),
            patch("app.admin_service.get_user_ref", return_value=user_ref),
            patch("app.admin_service.record_admin_audit") as audit,
            patch("app.admin_service.get_admin_user", return_value=expected),
        ):
            result = block_user("demo@example.com", 24, "abuse")

        update = user_ref.update.call_args.args[0]
        self.assertEqual(update["status"], "blocked")
        self.assertEqual(update["previousStatus"], "active")
        audit.assert_called_once()
        self.assertEqual(result, expected)

    def test_manual_activation_rejects_existing_active_pro(self):
        with patch(
            "app.admin_service.get_admin_user",
            return_value={
                "exists": True,
                "plan": "pro",
                "status": "active",
                "subscriptionStatus": "active",
            },
        ):
            with self.assertRaises(HTTPException) as context:
                admin_activate_user("demo@example.com", "pro_monthly", 24)

        self.assertEqual(context.exception.status_code, 409)

    def test_unblock_pro_user_restores_active_status(self):
        db = MagicMock()
        user_ref = MagicMock()
        snapshot = MagicMock(exists=True)
        snapshot.to_dict.return_value = {
            "status": "blocked",
            "plan": "pro",
            "subscriptionStatus": "cancel_pending",
        }
        user_ref.get.return_value = snapshot
        expected = {"exists": True, "status": "active"}

        with (
            patch("app.admin_service.get_db", return_value=db),
            patch("app.admin_service.get_user_ref", return_value=user_ref),
            patch("app.admin_service.record_admin_audit") as audit,
            patch("app.admin_service.get_admin_user", return_value=expected),
        ):
            result = unblock_user("demo@example.com", 24, "reviewed")

        update = user_ref.update.call_args.args[0]
        self.assertEqual(update["status"], "active")
        audit.assert_called_once()
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
