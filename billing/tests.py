from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from billing.models import Plan, Subscription, SubscriptionStatus
from profiles.models import Profile


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
