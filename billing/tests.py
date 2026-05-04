from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from billing.models import Plan, Subscription, SubscriptionStatus
from billing.upgrades import UpgradeNotAllowed, compute_upgrade_quote
from core.payments.subscriptions import activate_subscription
from profiles.consts import Status as PreferenceStatus
from profiles.models import Preference, Profile


def _mock_link(transaction_id="tx-1", link="https://pay.mayar.id/abc"):
    return {"link": link, "transaction_id": transaction_id}


class CheckoutLockTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", "u@example.com", "secret")
        self.profile = Profile.objects.create(user=self.user, full_name="U")
        token, _ = Token.objects.get_or_create(user=self.user)
        self.api = APIClient()
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.checkout_url = reverse("api-v1-subscription-checkout")
        self.cancel_url = reverse("api-v1-subscription-cancel-pending")
        self.plan_a = Plan.objects.create(name="A", price=10000, preference_limit=1)
        self.plan_b = Plan.objects.create(name="B", price=20000, preference_limit=2)

    @patch("core.api.v1.views.poll_subscription_after_checkout")
    @patch("core.api.v1.views.create_payment_link")
    def test_first_checkout_creates_pending(self, link, _poll):
        link.return_value = _mock_link("tx-a", "https://pay/a")
        resp = self.api.post(
            self.checkout_url, {"plan_id": self.plan_a.id}, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(
            Subscription.objects.filter(
                profile=self.profile, status=SubscriptionStatus.PENDING
            ).count(),
            1,
        )

    @patch("core.api.v1.views.poll_subscription_after_checkout")
    @patch("core.api.v1.views.create_payment_link")
    def test_same_plan_reclick_idempotent(self, link, _poll):
        link.return_value = _mock_link("tx-a", "https://pay/a")
        first = self.api.post(
            self.checkout_url, {"plan_id": self.plan_a.id}, format="json"
        )
        self.assertEqual(first.status_code, 201)
        first_id = first.data["subscription_id"]

        second = self.api.post(
            self.checkout_url, {"plan_id": self.plan_a.id}, format="json"
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["subscription_id"], first_id)
        self.assertEqual(second.data["payment_link"], "https://pay/a")
        self.assertEqual(Subscription.objects.filter(profile=self.profile).count(), 1)
        self.assertEqual(link.call_count, 1)

    @patch("core.api.v1.views.poll_subscription_after_checkout")
    @patch("core.api.v1.views.create_payment_link")
    def test_different_plan_blocked_with_409(self, link, _poll):
        link.return_value = _mock_link("tx-a", "https://pay/a")
        first = self.api.post(
            self.checkout_url, {"plan_id": self.plan_a.id}, format="json"
        )
        self.assertEqual(first.status_code, 201)

        second = self.api.post(
            self.checkout_url, {"plan_id": self.plan_b.id}, format="json"
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.data["pending_plan_id"], self.plan_a.id)
        self.assertEqual(second.data["payment_link"], "https://pay/a")
        self.assertEqual(Subscription.objects.filter(profile=self.profile).count(), 1)
        self.assertEqual(link.call_count, 1)

    @patch("core.api.v1.views.poll_subscription_after_checkout")
    @patch("core.api.v1.views.create_payment_link")
    def test_cancel_pending_unlocks_checkout(self, link, _poll):
        link.side_effect = [
            _mock_link("tx-a", "https://pay/a"),
            _mock_link("tx-b", "https://pay/b"),
        ]
        first = self.api.post(
            self.checkout_url, {"plan_id": self.plan_a.id}, format="json"
        )
        self.assertEqual(first.status_code, 201)

        cancel = self.api.post(self.cancel_url)
        self.assertEqual(cancel.status_code, 200)
        self.assertEqual(
            Subscription.objects.filter(
                profile=self.profile, status=SubscriptionStatus.PENDING
            ).count(),
            0,
        )
        self.assertEqual(
            Subscription.objects.filter(
                profile=self.profile, status=SubscriptionStatus.CANCELLED
            ).count(),
            1,
        )

        third = self.api.post(
            self.checkout_url, {"plan_id": self.plan_b.id}, format="json"
        )
        self.assertEqual(third.status_code, 201)
        self.assertEqual(
            Subscription.objects.filter(
                profile=self.profile, status=SubscriptionStatus.PENDING
            ).count(),
            1,
        )

    def test_cancel_pending_when_none_returns_404(self):
        resp = self.api.post(self.cancel_url)
        self.assertEqual(resp.status_code, 404)


class MySubscriptionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", "u@example.com", "secret")
        self.profile = Profile.objects.create(user=self.user, full_name="U")
        token, _ = Token.objects.get_or_create(user=self.user)
        self.api = APIClient()
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.url = reverse("api-v1-subscription-me")
        self.plan = Plan.objects.create(name="A", price=10000, preference_limit=1)

    def test_active_preferred_over_newer_cancelled(self):
        active = Subscription.objects.create(
            profile=self.profile, plan=self.plan, status=SubscriptionStatus.ACTIVE
        )
        Subscription.objects.create(
            profile=self.profile, plan=self.plan, status=SubscriptionStatus.CANCELLED
        )
        resp = self.api.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], active.id)
        self.assertEqual(resp.data["status"], SubscriptionStatus.ACTIVE)

    def test_pending_preferred_over_newer_cancelled(self):
        pending = Subscription.objects.create(
            profile=self.profile, plan=self.plan, status=SubscriptionStatus.PENDING
        )
        Subscription.objects.create(
            profile=self.profile, plan=self.plan, status=SubscriptionStatus.CANCELLED
        )
        resp = self.api.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], pending.id)

    def test_only_cancelled_returns_404(self):
        Subscription.objects.create(
            profile=self.profile, plan=self.plan, status=SubscriptionStatus.CANCELLED
        )
        resp = self.api.get(self.url)
        self.assertEqual(resp.status_code, 404)

    def test_active_preferred_over_expired(self):
        Subscription.objects.create(
            profile=self.profile, plan=self.plan, status=SubscriptionStatus.EXPIRED
        )
        active = Subscription.objects.create(
            profile=self.profile, plan=self.plan, status=SubscriptionStatus.ACTIVE
        )
        resp = self.api.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], active.id)


class PaymentGateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", "u@example.com", "secret")
        self.profile = Profile.objects.create(user=self.user, full_name="U")
        token, _ = Token.objects.get_or_create(user=self.user)
        self.api = APIClient()
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.gate_url = reverse("api-v1-payment-gate")
        self.checkout_url = reverse("api-v1-subscription-checkout")
        self.plan = Plan.objects.create(name="A", price=10000, preference_limit=1)

    def test_gate_open_when_no_preferences_and_not_ingested(self):
        resp = self.api.get(self.gate_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, {"locked": False})

    def test_gate_locked_on_waiting_admin_preference(self):
        Preference.objects.create(
            profile=self.profile,
            title="x",
            status=PreferenceStatus.WAITING_ADMIN,
        )
        resp = self.api.get(self.gate_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["locked"])
        self.assertEqual(resp.data["code"], "waiting_admin")
        self.assertIn("admin", resp.data["detail"].lower())

    def test_gate_locked_on_sparse_linkedin(self):
        self.profile.linkedin_ingested_at = timezone.now()
        self.profile.linkedin_quality_ok = False
        self.profile.linkedin_quality_reason = "headline only, no experiences"
        self.profile.save()
        resp = self.api.get(self.gate_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["locked"])
        self.assertEqual(resp.data["code"], "linkedin_quality")
        self.assertEqual(resp.data["detail"], "headline only, no experiences")

    def test_gate_quality_takes_precedence_over_waiting_admin(self):
        self.profile.linkedin_ingested_at = timezone.now()
        self.profile.linkedin_quality_ok = False
        self.profile.linkedin_quality_reason = "sparse"
        self.profile.save()
        Preference.objects.create(
            profile=self.profile,
            title="x",
            status=PreferenceStatus.WAITING_ADMIN,
        )
        resp = self.api.get(self.gate_url)
        self.assertEqual(resp.data["code"], "linkedin_quality")

    def test_gate_open_when_only_waiting_payment(self):
        Preference.objects.create(
            profile=self.profile,
            title="x",
            status=PreferenceStatus.WAITING_PAYMENT,
        )
        resp = self.api.get(self.gate_url)
        self.assertEqual(resp.data, {"locked": False})

    def test_gate_open_when_quality_ok_false_but_not_ingested(self):
        self.profile.linkedin_quality_ok = False
        self.profile.save()
        resp = self.api.get(self.gate_url)
        self.assertEqual(resp.data, {"locked": False})

    @patch("core.api.v1.views.poll_subscription_after_checkout")
    @patch("core.api.v1.views.create_payment_link")
    def test_checkout_blocked_on_waiting_admin(self, link, _poll):
        Preference.objects.create(
            profile=self.profile,
            title="x",
            status=PreferenceStatus.WAITING_ADMIN,
        )
        resp = self.api.post(
            self.checkout_url, {"plan_id": self.plan.id}, format="json"
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data["code"], "waiting_admin")
        self.assertEqual(Subscription.objects.filter(profile=self.profile).count(), 0)
        link.assert_not_called()

    @patch("core.api.v1.views.poll_subscription_after_checkout")
    @patch("core.api.v1.views.create_payment_link")
    def test_checkout_blocked_on_linkedin_quality(self, link, _poll):
        self.profile.linkedin_ingested_at = timezone.now()
        self.profile.linkedin_quality_ok = False
        self.profile.linkedin_quality_reason = "too sparse"
        self.profile.save()
        resp = self.api.post(
            self.checkout_url, {"plan_id": self.plan.id}, format="json"
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data["code"], "linkedin_quality")
        self.assertEqual(resp.data["detail"], "too sparse")
        link.assert_not_called()


class UpgradeQuoteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", "u@example.com", "secret")
        self.profile = Profile.objects.create(user=self.user, full_name="U")
        self.basic = Plan.objects.create(name="Basic", price=99000, preference_limit=1)
        self.pro = Plan.objects.create(name="Pro", price=159000, preference_limit=3)

    def _active_basic(self, *, amount_paid=99000, days_remaining=20):
        now = timezone.now()
        return Subscription.objects.create(
            profile=self.profile,
            plan=self.basic,
            status=SubscriptionStatus.ACTIVE,
            started_at=now - timedelta(days=30 - days_remaining),
            expires_at=now + timedelta(days=days_remaining),
            amount_paid=amount_paid,
        )

    def test_quote_mid_period_basic_to_pro(self):
        sub = self._active_basic(amount_paid=99000, days_remaining=20)
        q = compute_upgrade_quote(self.profile, self.pro, current_sub=sub)
        # credit = 99000 * 20/30 = 66000; bonus_seconds = 66000 * 30*86400/159000
        expected_credit = 99000 * 20 / 30
        expected_bonus_seconds = int(expected_credit * 30 * 86400 / 159000)
        self.assertEqual(q["charge"], 159000)
        self.assertAlmostEqual(q["credit_value"], round(expected_credit), delta=2)
        self.assertAlmostEqual(q["bonus_seconds"], expected_bonus_seconds, delta=2)
        self.assertGreater(q["bonus_days"], 12.0)
        self.assertLess(q["bonus_days"], 13.0)

    def test_quote_open_to_work_basic_credit_uses_amount_paid(self):
        sub = self._active_basic(amount_paid=49000, days_remaining=20)
        q = compute_upgrade_quote(self.profile, self.pro, current_sub=sub)
        # credit derived from 49k not 99k
        expected_credit = 49000 * 20 / 30
        self.assertAlmostEqual(q["credit_value"], round(expected_credit), delta=2)
        # OTW does not reapply on upgrade — Pro charged at full price
        self.assertEqual(q["charge"], 159000)

    def test_quote_near_expiry_bonus_near_zero(self):
        sub = self._active_basic(amount_paid=99000, days_remaining=0)
        sub.expires_at = timezone.now() - timedelta(seconds=1)
        sub.save(update_fields=["expires_at"])
        q = compute_upgrade_quote(self.profile, self.pro, current_sub=sub)
        self.assertEqual(q["bonus_seconds"], 0)
        self.assertEqual(q["credit_value"], 0)

    def test_quote_no_active_sub_raises(self):
        with self.assertRaises(UpgradeNotAllowed) as ctx:
            compute_upgrade_quote(self.profile, self.pro)
        self.assertEqual(ctx.exception.code, "no_active_sub")

    def test_quote_downgrade_raises(self):
        sub = self._active_basic()
        sub.plan = self.pro
        sub.save()
        with self.assertRaises(UpgradeNotAllowed) as ctx:
            compute_upgrade_quote(self.profile, self.basic, current_sub=sub)
        self.assertEqual(ctx.exception.code, "downgrade")

    def test_quote_same_plan_raises(self):
        sub = self._active_basic()
        with self.assertRaises(UpgradeNotAllowed) as ctx:
            compute_upgrade_quote(self.profile, self.basic, current_sub=sub)
        self.assertEqual(ctx.exception.code, "same_plan")


class UpgradeQuoteEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", "u@example.com", "secret")
        self.profile = Profile.objects.create(user=self.user, full_name="U")
        token, _ = Token.objects.get_or_create(user=self.user)
        self.api = APIClient()
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.url = reverse("api-v1-subscription-upgrade-quote")
        self.basic = Plan.objects.create(name="Basic", price=99000, preference_limit=1)
        self.pro = Plan.objects.create(name="Pro", price=159000, preference_limit=3)

    def test_quote_400_no_active_sub(self):
        resp = self.api.get(self.url, {"plan_id": self.pro.id})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "no_active_sub")

    def test_quote_400_downgrade(self):
        Subscription.objects.create(
            profile=self.profile,
            plan=self.pro,
            status=SubscriptionStatus.ACTIVE,
            started_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=20),
            amount_paid=159000,
        )
        resp = self.api.get(self.url, {"plan_id": self.basic.id})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "downgrade")

    def test_quote_ok_basic_to_pro(self):
        Subscription.objects.create(
            profile=self.profile,
            plan=self.basic,
            status=SubscriptionStatus.ACTIVE,
            started_at=timezone.now() - timedelta(days=10),
            expires_at=timezone.now() + timedelta(days=20),
            amount_paid=99000,
        )
        resp = self.api.get(self.url, {"plan_id": self.pro.id})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["charge"], 159000)
        self.assertEqual(resp.data["new_plan_id"], self.pro.id)


class UpgradeCheckoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", "u@example.com", "secret")
        self.profile = Profile.objects.create(user=self.user, full_name="U")
        token, _ = Token.objects.get_or_create(user=self.user)
        self.api = APIClient()
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.checkout_url = reverse("api-v1-subscription-checkout")
        self.basic = Plan.objects.create(name="Basic", price=99000, preference_limit=1)
        self.pro = Plan.objects.create(name="Pro", price=159000, preference_limit=3)
        self.active = Subscription.objects.create(
            profile=self.profile,
            plan=self.basic,
            status=SubscriptionStatus.ACTIVE,
            started_at=timezone.now() - timedelta(days=10),
            expires_at=timezone.now() + timedelta(days=20),
            amount_paid=99000,
        )

    @patch("core.api.v1.views.poll_subscription_after_checkout")
    @patch("core.api.v1.views.create_payment_link")
    def test_upgrade_charges_full_pro_price_and_links_replaces(self, link, _poll):
        link.return_value = _mock_link("tx-up", "https://pay/up")
        resp = self.api.post(self.checkout_url, {"plan_id": self.pro.id}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(link.call_count, 1)
        kwargs = link.call_args.kwargs
        self.assertEqual(kwargs["amount"], 159000)
        self.assertIn("Upgrade", kwargs["description"])
        sub = Subscription.objects.get(pk=resp.data["subscription_id"])
        self.assertEqual(sub.replaces_id, self.active.id)
        self.assertEqual(sub.amount_paid, 159000)
        self.assertEqual(sub.status, SubscriptionStatus.PENDING)

    @patch("core.api.v1.views.poll_subscription_after_checkout")
    @patch("core.api.v1.views.create_payment_link")
    def test_downgrade_blocked_with_400(self, link, _poll):
        # swap active to Pro, request Basic
        self.active.plan = self.pro
        self.active.amount_paid = 159000
        self.active.save()
        resp = self.api.post(
            self.checkout_url, {"plan_id": self.basic.id}, format="json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "downgrade")
        link.assert_not_called()

    @patch("core.api.v1.views.poll_subscription_after_checkout")
    @patch("core.api.v1.views.create_payment_link")
    def test_upgrade_idempotent_same_plan(self, link, _poll):
        link.return_value = _mock_link("tx-up", "https://pay/up")
        first = self.api.post(
            self.checkout_url, {"plan_id": self.pro.id}, format="json"
        )
        self.assertEqual(first.status_code, 201)
        second = self.api.post(
            self.checkout_url, {"plan_id": self.pro.id}, format="json"
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["subscription_id"], first.data["subscription_id"])
        self.assertEqual(link.call_count, 1)


class ActivateUpgradeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", "u@example.com", "secret")
        self.profile = Profile.objects.create(user=self.user, full_name="U")
        self.basic = Plan.objects.create(name="Basic", price=99000, preference_limit=1)
        self.pro = Plan.objects.create(name="Pro", price=159000, preference_limit=3)

    @patch("core.payments.subscriptions.crawl_and_assess_preference")
    def test_activate_upgrade_grants_bonus_and_replaces_old(self, crawl):
        now = timezone.now()
        old = Subscription.objects.create(
            profile=self.profile,
            plan=self.basic,
            status=SubscriptionStatus.ACTIVE,
            started_at=now - timedelta(days=10),
            expires_at=now + timedelta(days=20),
            amount_paid=99000,
        )
        # preference already RUNNING under old plan
        Preference.objects.create(
            profile=self.profile, title="x", status=PreferenceStatus.RUNNING
        )
        new = Subscription.objects.create(
            profile=self.profile,
            plan=self.pro,
            status=SubscriptionStatus.PENDING,
            replaces=old,
            amount_paid=159000,
        )
        activate_subscription(new)
        new.refresh_from_db()
        old.refresh_from_db()
        self.assertEqual(new.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(old.status, SubscriptionStatus.REPLACED)
        # old expires_at truncated to ~now
        self.assertLess(abs((old.expires_at - timezone.now()).total_seconds()), 5)
        # new expires_at ~ now + 30d + bonus (12.45d for 99k/20d/159k)
        elapsed = (new.expires_at - timezone.now()).total_seconds()
        # 30 days + ~12.45 days = ~42.45 days = ~3.668M seconds
        self.assertGreater(elapsed, 30 * 86400 + 11 * 86400)
        self.assertLess(elapsed, 30 * 86400 + 14 * 86400)
        # crawl task NOT queued (preferences already RUNNING)
        crawl.delay.assert_not_called()

    @patch("core.payments.subscriptions.crawl_and_assess_preference")
    def test_activate_fresh_unchanged(self, crawl):
        Preference.objects.create(
            profile=self.profile,
            title="x",
            status=PreferenceStatus.WAITING_PAYMENT,
            crawl_url="https://example.com",
            crawl_source="INDEED",
        )
        sub = Subscription.objects.create(
            profile=self.profile,
            plan=self.pro,
            status=SubscriptionStatus.PENDING,
            amount_paid=159000,
        )
        activate_subscription(sub)
        sub.refresh_from_db()
        self.assertEqual(sub.status, SubscriptionStatus.ACTIVE)
        # fresh = exactly 30 days ±2s
        elapsed = (sub.expires_at - timezone.now()).total_seconds()
        self.assertAlmostEqual(elapsed, 30 * 86400, delta=5)
        crawl.delay.assert_called_once()
