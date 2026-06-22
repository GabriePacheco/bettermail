import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.billing_service import (
    _expire_subscription,
    _record_renewal_failure,
    cancel_subscription,
    process_due_subscriptions,
)
from app.models import OfficeUser
from app.payphone_service import build_token_charge_payload, is_payphone_charge_approved
from app.usage_service import check_usage_allowed


NOW = datetime.now(timezone.utc)


class Snapshot:
    def __init__(self, document_id, data):
        self.id = document_id
        self.reference = MagicMock()
        self.reference.id = document_id
        self._data = data
        self.exists = True

    def to_dict(self):
        return dict(self._data)


class BillingLifecycleTests(unittest.TestCase):
    def test_payphone_approval_requires_both_approved_indicators(self):
        self.assertTrue(
            is_payphone_charge_approved({
                "statusCode": 3,
                "transactionStatus": "Approved",
            })
        )
        self.assertFalse(
            is_payphone_charge_approved({
                "statusCode": 3,
                "transactionStatus": "Declined",
            })
        )

    def test_token_payload_reuses_encrypted_card_holder(self):
        with patch("app.payphone_service.encrypt_card_holder") as encrypt:
            payload = build_token_charge_payload(
                card_token="card-token",
                card_holder=None,
                encrypted_card_holder="encrypted-holder",
                document_id="0102030405",
                phone_number="593999999999",
                email="demo@example.com",
                amount=499,
                client_transaction_id="renewal-1",
                reference="Renewal",
            )

        self.assertEqual(payload["cardHolder"], "encrypted-holder")
        encrypt.assert_not_called()

    def test_cancel_pending_subscription_keeps_usage_until_period_end(self):
        user_ref = MagicMock()
        data = {
            "plan": "pro",
            "status": "active",
            "subscriptionStatus": "cancel_pending",
            "monthlyUsed": 12,
            "monthlyLimit": 300,
            "trialUsed": 24,
            "trialLimit": 24,
            "currentPeriodEnd": NOW + timedelta(days=5),
        }
        with patch(
            "app.usage_service.get_or_create_mailbox_user",
            return_value=(user_ref, data),
        ):
            result = check_usage_allowed(OfficeUser(email="demo@example.com"), 24)

        self.assertTrue(result["allowed"])
        self.assertEqual(result["usage_bucket"], "monthly")

    def test_past_due_subscription_uses_grace_period(self):
        data = {
            "plan": "pro",
            "status": "active",
            "subscriptionStatus": "past_due",
            "monthlyUsed": 12,
            "monthlyLimit": 300,
            "trialUsed": 24,
            "trialLimit": 24,
            "currentPeriodEnd": NOW - timedelta(hours=1),
            "gracePeriodEnd": NOW + timedelta(days=2),
            "paymentActionRequired": True,
        }
        with patch(
            "app.usage_service.get_or_create_mailbox_user",
            return_value=(MagicMock(), data),
        ):
            result = check_usage_allowed(OfficeUser(email="demo@example.com"), 24)

        self.assertTrue(result["allowed"])
        self.assertEqual(result["plan"], "pro")

    def test_expired_pro_does_not_fall_back_to_a_new_trial(self):
        data = {
            "plan": "pro",
            "status": "expired",
            "subscriptionStatus": "expired",
            "monthlyUsed": 25,
            "monthlyLimit": 300,
            "trialUsed": 0,
            "trialLimit": 24,
            "currentPeriodEnd": NOW - timedelta(days=1),
        }
        with patch(
            "app.usage_service.get_or_create_mailbox_user",
            return_value=(MagicMock(), data),
        ):
            result = check_usage_allowed(OfficeUser(email="demo@example.com"), 24)

        self.assertFalse(result["allowed"])
        self.assertEqual(result["status"], "subscription_expired")
        self.assertTrue(result["upgradeRequired"])

    def test_cancel_marks_subscription_for_period_end(self):
        db = MagicMock()
        user_ref = MagicMock()
        subscription_ref = MagicMock()
        subscription_ref.id = "sub_demo"
        subscription = {
            "subscriptionId": "sub_demo",
            "email": "demo@example.com",
            "emailHash": "hash",
            "status": "active",
            "currentPeriodEnd": NOW + timedelta(days=10),
        }
        expected = {"subscriptionStatus": "cancel_pending"}

        with (
            patch("app.billing_service.get_db", return_value=db),
            patch(
                "app.billing_service.get_or_create_mailbox_user",
                return_value=(user_ref, {"subscriptionId": "sub_demo"}),
            ),
            patch(
                "app.billing_service._find_current_subscription",
                return_value=(subscription_ref, subscription),
            ),
            patch("app.billing_service.get_billing_status", return_value=expected),
        ):
            result = cancel_subscription(
                OfficeUser(email="demo@example.com"),
                24,
                "test",
            )

        self.assertEqual(result, expected)
        subscription_update = subscription_ref.update.call_args.args[0]
        self.assertTrue(subscription_update["cancelAtPeriodEnd"])
        self.assertFalse(subscription_update["autoRenew"])
        user_update = user_ref.update.call_args.args[0]
        self.assertEqual(user_update["subscriptionStatus"], "cancel_pending")

    def test_rejected_payment_expires_after_maximum_attempts(self):
        db = MagicMock()
        subscription_ref = MagicMock()
        subscription_ref.id = "sub_demo"
        subscription = {
            "subscriptionId": "sub_demo",
            "email": "demo@example.com",
            "emailHash": "hash",
            "renewalFailureCount": 2,
            "gracePeriodEnd": NOW + timedelta(days=1),
        }
        settings = SimpleNamespace(
            billing_grace_days=3,
            billing_max_renewal_attempts=3,
        )

        with (
            patch("app.billing_service.get_settings", return_value=settings),
            patch("app.billing_service._expire_subscription") as expire,
        ):
            result = _record_renewal_failure(
                db=db,
                subscription_ref=subscription_ref,
                subscription=subscription,
                trial_limit=24,
                reason="payment_declined",
            )

        self.assertEqual(result, "expired")
        expire.assert_called_once()

    def test_renewal_dry_run_reports_due_without_charging(self):
        due = Snapshot("sub_due", {
            "subscriptionId": "sub_due",
            "email": "demo@example.com",
            "emailHash": "hash",
            "status": "active",
            "autoRenew": True,
            "currentPeriodEnd": NOW - timedelta(minutes=1),
        })
        collection = MagicMock()
        collection.stream.return_value = iter([due])
        db = MagicMock()
        db.collection.return_value = collection
        settings = SimpleNamespace(payphone_recurring_enabled=True)

        with (
            patch("app.billing_service.get_db", return_value=db),
            patch("app.billing_service.get_settings", return_value=settings),
            patch("app.billing_service._renew_payphone_subscription") as renew,
        ):
            result = process_due_subscriptions(
                trial_limit=24,
                limit=100,
                dry_run=True,
            )

        self.assertEqual(result["due"], 1)
        self.assertEqual(result["renewed"], 0)
        renew.assert_not_called()

    def test_expiration_does_not_unblock_an_admin_blocked_user(self):
        db = MagicMock()
        subscription_ref = MagicMock()
        subscription_ref.id = "sub_demo"
        user_ref = MagicMock()
        subscription = {
            "subscriptionId": "sub_demo",
            "email": "demo@example.com",
            "emailHash": "hash",
        }

        with patch(
            "app.billing_service.get_or_create_mailbox_user",
            return_value=(user_ref, {"status": "blocked"}),
        ):
            _expire_subscription(
                db=db,
                subscription_ref=subscription_ref,
                subscription=subscription,
                trial_limit=24,
                reason="test",
            )

        subscription_update = subscription_ref.update.call_args.args[0]
        user_update = user_ref.update.call_args.args[0]
        self.assertEqual(subscription_update["status"], "expired")
        self.assertEqual(user_update["status"], "blocked")
        self.assertEqual(user_update["subscriptionStatus"], "expired")


if __name__ == "__main__":
    unittest.main()
