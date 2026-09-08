# Payment & Subscription Mechanism — Mayar Integration

How **cariinkerja.id** sells subscriptions through the **Mayar** payment gateway. This
is a concrete, reproduce-it reference for the exact mechanism in this Django + Celery +
React codebase — real file paths, real function names, exact code. A future engineer (or
AI) should be able to rebuild the same flow in a similar Django stack from this doc
alone.

> **Mayar** is an Indonesian payment-link gateway. You don't handle cards. You ask Mayar
> to mint a hosted checkout URL, redirect the user to it, and learn the result
> asynchronously via webhook (plus polling fallbacks).

---

## 0. Where everything lives

| Concern | Path |
|---|---|
| Mayar HTTP adapter | `core/payments/mayar.py` |
| Activation / cancellation | `core/payments/subscriptions.py` |
| Models, pricing | `billing/models.py` |
| Upgrade proration | `billing/upgrades.py` |
| Celery polling | `core/tasks.py` |
| REST: checkout, plans, me, stream, upgrade-quote, cancel, recheck | `api/v1/billing_api.py` |
| REST: Mayar webhook | `api/v1/payments_api.py` |
| Routes | `api/v1/urls.py` |
| Redis pub/sub | `core/realtime.py` |
| Frontend data layer | `frontend/src/features/billing/{api,hooks,types,utils}.ts` |
| Frontend SSE | `frontend/src/app/realtime.ts` |
| Frontend UI | `frontend/src/routes/plans.index.tsx`, `frontend/src/features/billing/components/*` |

**The keystone:** every path that can mark a payment paid — webhook, two pollers, manual
recheck — calls the **same idempotent** `activate_subscription()` in
`core/payments/subscriptions.py`. That single property makes the redundant reliability
paths safe.

---

## 1. The Mayar adapter — `core/payments/mayar.py`

The whole gateway integration is **three functions + two status sets**. Base URL and key
come from settings. `httpx` for HTTP, 15s timeout, raises `MayarError` on any failure.

```python
PAID_STATUSES   = {"paid", "success", "completed"}
FAILED_STATUSES = {"failed", "expired", "cancelled", "canceled"}

class MayarError(Exception): ...

def _base_url() -> str:
    return getattr(settings, "MAYAR_BASE_URL", "") or "https://api.mayar.id/hl/v1"

def _headers() -> dict:
    api_key = settings.MAYAR_API_KEY
    if not api_key:
        raise MayarError("MAYAR_API_KEY not configured.")
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
```

### 1.1 Create payment link — `POST {BASE}/payment/create`

```python
def create_payment_link(*, name, amount, email, description, redirect_url, mobile=""):
    payload = {
        "name": name,
        "amount": amount,                 # int IDR, no decimals
        "email": email,
        "description": description,
        "redirectUrl": redirect_url,      # note camelCase key Mayar expects
    }
    if mobile:
        payload["mobile"] = mobile
    resp = httpx.post(f"{_base_url()}/payment/create", headers=_headers(),
                      json=payload, timeout=15)
    if resp.status_code >= 400:
        raise MayarError(f"Mayar {resp.status_code}: {resp.text}")
    data = resp.json().get("data") or {}
    link = data.get("link")
    transaction_id = data.get("id") or data.get("transaction_id")
    if not link or not transaction_id:
        raise MayarError(f"Mayar response missing link/id: {resp.json()}")
    return {"link": link, "transaction_id": str(transaction_id)}
```

Mayar wraps everything under `data`. The transaction id comes back as `data.id` (fall
back to `data.transaction_id`). It's stored on the subscription as `payment_ref` and is
the lookup key for webhooks/polls.

### 1.2 Get payment status — `GET {BASE}/payment/{id}`

```python
def get_payment_status(payment_id) -> dict:
    resp = httpx.get(f"{_base_url()}/payment/{payment_id}", headers=_headers(), timeout=15)
    if resp.status_code >= 400:
        raise MayarError(f"Mayar {resp.status_code}: {resp.text}")
    data = resp.json().get("data") or {}
    return {"status": str(data.get("status") or "").lower(), "raw": data}
```

Status is **lowercased** so it matches `PAID_STATUSES` / `FAILED_STATUSES` regardless of
how Mayar cases it.

### 1.3 Verify webhook — `X-Callback-Token` header

```python
def verify_webhook(request) -> bool:
    expected = getattr(settings, "MAYAR_WEBHOOK_TOKEN", "") or ""
    if not expected:
        return False                       # not configured → reject
    received = request.headers.get("X-Callback-Token") or request.headers.get("x-callback-token")
    return bool(received) and received == expected
```

> Plain `==`. For hardening, consider `hmac.compare_digest`. Mayar sends the configured
> static token in `X-Callback-Token`.

---

## 2. Settings / environment

Read in `core/settings.py`, declared in `.env.example`:

```sh
# --- Mayar (payments) ---
MAYAR_API_KEY=
MAYAR_WEBHOOK_TOKEN=
MAYAR_BASE_URL=https://api.mayar.club/hl/v1
PAYMENT_REDIRECT_URL=http://localhost:5173/plans
```

| Var | Purpose | Notes |
|---|---|---|
| `MAYAR_API_KEY` | Bearer auth for Mayar API | required; `MayarError` if empty |
| `MAYAR_WEBHOOK_TOKEN` | shared secret for `verify_webhook` | required for webhook to pass |
| `MAYAR_BASE_URL` | API base | **mismatch to know:** `.env.example` ships `…api.mayar.club/hl/v1`; code fallback when unset is `…api.mayar.id/hl/v1`. Set it explicitly to the correct host for your account. |
| `PAYMENT_REDIRECT_URL` | where Mayar returns the user after pay | points at the SPA `/plans` |

---

## 3. Models — `billing/models.py`

Money is always **integer IDR** (`PositiveIntegerField`, "no decimals").

### `Plan`
| Field | Type | Notes |
|---|---|---|
| `name` | char(80) | |
| `price` | uint | IDR |
| `preference_limit` | uint8 | how many job-search Preferences the plan unlocks (default 1) |
| `is_active` | bool | only active plans are listed/sellable |

Default ordering `["price"]` (cheapest first — relevant to the discount logic).

### `Subscription`
| Field | Type | Notes |
|---|---|---|
| `profile` | FK → profiles.Profile (CASCADE) | owner |
| `plan` | FK → Plan (**PROTECT**) | can't delete a plan with subs |
| `status` | `SubscriptionStatus` | default `PENDING` |
| `started_at` / `expires_at` | datetime? | set at activation |
| `payment_provider` | char(16) | default `"mayar"` |
| `payment_ref` | char(128) | Mayar transaction id — **indexed** |
| `payment_link` | url | Mayar hosted checkout URL (lets the user resume) |
| `amount_paid` | uint | IDR actually charged (post-discount, post-credit) |
| `replaces` | self-FK (SET_NULL) | the old sub an upgrade supersedes |

Indexes: `(profile, status)`, `(payment_ref)`, `(status, expires_at)`.

`amount_paid` — not `plan.price` — is the source of truth for proration, because a
discounted user paid less than list.

### `SubscriptionStatus` + state machine

```
PENDING ──paid──────────► ACTIVE ──time──► EXPIRED
   │                         │
   └──failed/expired/cancel──┤──upgrade──► REPLACED (old sub, retired now)
                             ▼
                         CANCELLED
```

```python
class SubscriptionStatus(models.TextChoices):
    PENDING = "PENDING"; ACTIVE = "ACTIVE"; EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"; REPLACED = "REPLACED"
```

`EXPIRED` is not auto-written by the payment flow — it's the meaning of
`expires_at < now`; the Celery crawl pipeline (`crawl_running_preferences`) gates on an
ACTIVE sub with `expires_at > now`.

---

## 4. Pricing — `effective_price()` + Open-to-Work discount

```python
OPEN_TO_WORK_DISCOUNT_PRICE = 49000

def effective_price(plan, profile, cheapest_id=None):
    if profile is None or not profile.linkedin_discount_eligible:
        return plan.price                              # rule 0: not eligible
    if cheapest_id is None:
        cheapest_id = (Plan.objects.filter(is_active=True)
                       .order_by("price").values_list("id", flat=True).first())
    if plan.id != cheapest_id:
        return plan.price                              # rule 1: only the cheapest plan
    if plan.price <= OPEN_TO_WORK_DISCOUNT_PRICE:
        return plan.price                              # rule 2: already at/below cap
    return OPEN_TO_WORK_DISCOUNT_PRICE                 # rule 3: cap to 49 000
```

`profile.linkedin_discount_eligible` derives from `profile.open_to_work` (set during
LinkedIn ingest). Worked examples for an eligible user:

| Cheapest plan | Buying | Charged | Rule |
|---|---|---|---|
| 50 000 | 50 000 (cheapest) | **49 000** | 3 — capped |
| 50 000 | 75 000 (2nd) | 75 000 | 1 — not the cheapest |
| 40 000 | 40 000 (cheapest) | 40 000 | 2 — already below cap |

`GET /plans/` (`billing_api.list`) computes `cheapest_id` once and passes it to the
serializer so each plan shows both `price` and `effective_price`.

---

## 5. Checkout — `billing_api.create` (`POST /api/v1/subscriptions/checkout/`)

Request body: `{ "plan_id": "<id>" }`. Step by step (real code):

1. **Resolve profile** (`request.user.profile`) → 404 if missing.
2. **Payment gate** `_payment_gate(profile)` → **409** if blocked:
   - `linkedin_ingested_at` set but `linkedin_quality_ok` false → code `linkedin_quality`.
   - any Preference in `WAITING_ADMIN` → code `waiting_admin`.
3. **Upgrade vs downgrade** — if an ACTIVE sub exists on a different plan
   (`get_active_subscription`):
   - `plan.price <= active.plan.price` → **400** `{code: "downgrade"}`.
   - else `is_upgrade = True`.
4. **Atomic block with `select_for_update()`** on the newest `PENDING` sub:
   - same plan → return it (HTTP **200**, resume — no duplicate link).
   - different plan → **409** with `pending_subscription_id` / `pending_plan_id` / `payment_link`.
5. **Create the PENDING `Subscription`** (still inside the txn), `payment_provider="mayar"`:
   - upgrade → `quote = compute_upgrade_quote(profile, plan, current_sub=active_sub)`
     (catch `UpgradeNotAllowed` → 400), set `replaces=active_sub`, `amount = quote["charge"]`,
     description `Upgrade {old}→{new} (+{bonus_days:.1f}d bonus)`.
   - new → `amount = effective_price(plan, profile)`, description `"{plan} subscription
     (1 month)"` (+ `" (Open-to-Work discount)"` if `amount < plan.price`).
6. **Mint the link** `create_payment_link(name=full_name|email, amount, email, description,
   redirect_url=PAYMENT_REDIRECT_URL, mobile=profile.phone)`.
   **On `MayarError` → `sub.delete()` and return 502** (no orphan PENDING).
7. **Persist** `payment_link`, `payment_ref` (= transaction id), `amount_paid`.
8. **Schedule fallback poll**:
   `poll_subscription_after_checkout.apply_async(args=[sub.id], countdown=30)`.
9. **Return 201** `{ subscription_id, payment_link }`. Frontend does
   `window.location.href = payment_link`.

Routes (`api/v1/urls.py`, all under `/api/v1/`):

```
plans/                              GET   billing_api.list          (AllowAny)
subscriptions/me/                   GET   billing_api.detail
subscriptions/checkout/             POST  billing_api.create
subscriptions/upgrade-quote/        GET   billing_api.upgrade_quote
subscriptions/cancel-pending/       POST  billing_api.cancel_pending
subscriptions/<pk>/recheck/         POST  billing_api.recheck
subscriptions/stream/               GET   billing_api.stream        (token via ?token=)
payment-gate/                       GET   billing_api.payment_gate
payments/mayar/webhook/             POST  payments_api.webhook      (AllowAny + token)
```

---

## 6. Webhook — `payments_api.webhook` (`POST /api/v1/payments/mayar/webhook/`)

`AllowAny` (Mayar isn't authenticated to our app); secured by the callback token.

```python
@api_view(["POST"]); @permission_classes([AllowAny])
def webhook(request):
    if not verify_webhook(request):                       # X-Callback-Token vs MAYAR_WEBHOOK_TOKEN
        return Response({"detail": "Invalid token."}, status=401)
    event = request.data.get("event") or ""
    data  = request.data.get("data") or {}
    payment_ref = str(data.get("id") or data.get("transaction_id") or "")
    if not payment_ref:
        return Response({"detail": "Missing transaction id."}, status=400)
    sub = Subscription.objects.filter(payment_ref=payment_ref).first()
    if sub is None:
        return Response({"detail": "Subscription not found."}, status=404)

    if event in {"payment.received", "payment.success", "PAYMENT_RECEIVED"}:
        try: activate_subscription(sub)
        except Exception: return Response({"detail": "Internal error."}, status=500)
    elif event in {"payment.failed", "payment.expired"}:
        try: cancel_pending_subscription(sub)
        except Exception: return Response({"detail": "Internal error."}, status=500)
    else:
        logger.warning("unhandled event=%r …")            # still 200

    return Response({"ok": True})
```

Status codes — 401 bad token, 400 missing ref, 404 unknown sub, 500 on internal failure
(so Mayar retries), 200 `{ok:true}` otherwise (including unhandled events, which are just
logged — keeps Mayar from retrying forever).

---

## 7. Activation — `core/payments/subscriptions.py`

**The convergence point. Idempotent.**

```python
ACTIVATION_DAYS = 30
TOTAL_SECONDS   = ACTIVATION_DAYS * 86400   # 2_592_000

def activate_subscription(sub) -> bool:
    if sub.status == SubscriptionStatus.ACTIVE:
        return False                                   # idempotent no-op
    now = timezone.now()
    bonus_seconds = 0
    replaces_id = sub.replaces_id

    if replaces_id:                                    # ── UPGRADE ──
        old = Subscription.objects.select_related("plan").filter(pk=replaces_id).first()
        if old and old.expires_at and sub.plan.price:
            seconds_remaining = max(0.0, (old.expires_at - now).total_seconds())
            credit_value  = old.amount_paid * seconds_remaining / TOTAL_SECONDS
            bonus_seconds = int(credit_value * TOTAL_SECONDS / sub.plan.price)
        Subscription.objects.filter(pk=replaces_id, status=SubscriptionStatus.ACTIVE).update(
            status=SubscriptionStatus.REPLACED, expires_at=now, updated_on=now)

    sub.status     = SubscriptionStatus.ACTIVE
    sub.started_at = now
    sub.expires_at = now + timedelta(days=ACTIVATION_DAYS, seconds=bonus_seconds)
    sub.save(update_fields=["status", "started_at", "expires_at", "updated_on"])

    if not replaces_id:                                # ── NEW SUB ONLY ──
        pending = Preference.objects.filter(profile=sub.profile,
                                            status=PreferenceStatus.WAITING_PAYMENT)
        pref_ids = list(pending.values_list("id", flat=True))
        pending.update(status=PreferenceStatus.RUNNING, updated_on=now)
        crawlable = Preference.objects.filter(id__in=pref_ids).exclude(crawl_urls=[]) \
                                      .values_list("id", flat=True)
        for pid in crawlable:
            crawl_and_assess_preference.delay(pid)     # queue the paid work

    user_id = getattr(getattr(sub.profile, "user", None), "id", None)
    if user_id is not None:
        publish(user_channel(user_id), {
            "event": "subscription.activated", "subscription_id": sub.id,
            "status": sub.status, "expires_at": sub.expires_at.isoformat(),
            "plan": sub.plan.name, "replaces_id": replaces_id,
            "bonus_seconds": bonus_seconds,
        })
    return True
```

- **Idempotent** — first line bails if already ACTIVE. This is why 4 sources can call it.
- **New sub** → unlock `WAITING_PAYMENT` Preferences to `RUNNING`, then enqueue
  `crawl_and_assess_preference` for those with `crawl_urls`.
- **Upgrade** → compute bonus from old sub's unused value, retire old sub
  (`status=ACTIVE` guard prevents a double-upgrade race), append bonus seconds, do **not**
  re-unlock (Preferences already RUNNING).
- **Always publish** `subscription.activated` to the user's Redis channel.

Cancellation mirror (idempotent):

```python
def cancel_pending_subscription(sub) -> bool:
    if sub.status != SubscriptionStatus.PENDING:
        return False
    sub.status = SubscriptionStatus.CANCELLED
    sub.save(update_fields=["status", "updated_on"])
    return True
```

---

## 8. Upgrade proration — `billing/upgrades.py`

Philosophy: **charge full new-plan list price; convert old plan's unused value into bonus
time on the new one.** No refunds, no credit balance — a longer `expires_at`.

```python
ACTIVATION_DAYS = 30
TOTAL_SECONDS   = ACTIVATION_DAYS * 86400

def compute_upgrade_quote(profile, new_plan, *, current_sub=None, at=None):
    now = at or timezone.now()
    current_sub = current_sub or get_active_subscription(profile)
    if current_sub is None or current_sub.status != SubscriptionStatus.ACTIVE:
        raise UpgradeNotAllowed("no_active_sub", "No active subscription to upgrade from.")
    if new_plan.id == current_sub.plan_id:
        raise UpgradeNotAllowed("same_plan", "Already on this plan.")
    if new_plan.price <= current_sub.plan.price:
        raise UpgradeNotAllowed("downgrade", "Downgrade is not available.")

    seconds_remaining = max(0.0, (current_sub.expires_at - now).total_seconds()) if current_sub.expires_at else 0.0
    credit_value  = current_sub.amount_paid * seconds_remaining / TOTAL_SECONDS
    bonus_seconds = credit_value * TOTAL_SECONDS / new_plan.price if new_plan.price else 0.0
    charge        = effective_price(new_plan, profile)
    return {
        "current_plan_id": current_sub.plan_id, "new_plan_id": new_plan.id,
        "seconds_remaining": int(seconds_remaining),
        "days_remaining": round(seconds_remaining / 86400, 2),
        "amount_paid_old": current_sub.amount_paid,
        "credit_value": int(round(credit_value)),
        "bonus_seconds": int(bonus_seconds),
        "bonus_days": round(bonus_seconds / 86400, 2),
        "charge": charge,
        "new_expires_at_estimate": (now + timedelta(days=ACTIVATION_DAYS, seconds=int(bonus_seconds))).isoformat(),
    }
```

`UpgradeNotAllowed(code, detail)` codes: `no_active_sub`, `same_plan`, `downgrade` — all
surfaced as 400 by the views.

**Worked example:** old plan paid 50 000, 15 days (1 296 000 s) left, new plan 100 000.
`credit_value = 50000 * 1 296 000 / 2 592 000 = 25 000`;
`bonus_seconds = 25 000 * 2 592 000 / 100 000 = 648 000 s = 7.5 d`. User pays 100 000,
new sub expires in 37.5 days.

**Dual compute (keep in sync):** the formula lives in *two* places — `compute_upgrade_quote`
(to *preview* before paying) and `activate_subscription` (to *apply* after paying, with the
current clock). They must agree; activation recomputes because time has passed.

---

## 9. Reliability — webhook + 2 pollers + manual recheck

All converge on the idempotent `activate_subscription`.

### (1) Webhook — primary, instant (§6).

### (2) Post-checkout poll — `poll_subscription_after_checkout` (`core/tasks.py`)
Self-rescheduling, kicked off at checkout (`countdown=30`):
- stop if sub left PENDING, if no `payment_ref`, or if past `created_on + 10min` window.
- `get_payment_status` → paid → activate & stop; failed → cancel & stop; pending →
  `self.apply_async(countdown=30)`.
- `MayarError` → `self.retry(countdown=30, max_retries=None)` (retry until window closes).
- Constants: `CHECKOUT_POLL_INTERVAL_SECONDS=30`, `CHECKOUT_POLL_WINDOW_MINUTES=10`.

### (3) Periodic sweep — `poll_pending_subscriptions` (`core/tasks.py`)
Long-tail net. All PENDING subs created within `POLL_WINDOW_HOURS=48` with a `payment_ref`;
each → `get_payment_status` → activate / cancel; returns
`{activated, cancelled, errors}`. **Schedule via Django admin** (django_celery_beat
`DatabaseScheduler`) — not in code.

### (4) Manual recheck — `billing_api.recheck` (`POST /subscriptions/<pk>/recheck/`)
Owner-only. Already ACTIVE → return current. Not PENDING / no ref → 409. Else
`get_payment_status` → if in `PAID_STATUSES` → `activate_subscription`. `MayarError` → 502.
Frontend's "Saya sudah bayar, refresh" button.

---

## 10. Realtime / SSE — `core/realtime.py` + `billing_api.stream`

Activation truth reaches the browser by server-push, not by trusting the Mayar redirect.

```python
# core/realtime.py
def user_channel(user_id: int) -> str: return f"user:{user_id}:events"
def publish(channel, payload):          _client().publish(channel, json.dumps(payload, default=str))
```

`billing_api.stream` is a plain Django `StreamingHttpResponse` (`text/event-stream`):
- auth via **`?token=` query param** (EventSource can't set headers) → DRF `Token` lookup,
  403 if invalid.
- subscribes to `user:{id}:events` on Redis pub/sub, yields `data: {json}\n\n`, sends
  `: ping` every `SSE_PING_SECONDS=15`. Sets `Cache-Control: no-cache`,
  `X-Accel-Buffering: no`.

> Each open SSE connection holds a sync worker — fine for plans-page concurrency; revisit
> (gthread/async) before scaling.

---

## 11. Frontend — `frontend/src/features/billing/*`

Hooks (`hooks.ts`) over TanStack Query:

| Hook | Endpoint | Note |
|---|---|---|
| `usePlans()` | `GET /plans/` | `["plans"]` |
| `useMySubscription()` | `GET /subscriptions/me/` | `["subscription","me"]`, `retry:false` |
| `usePaymentGate()` | `GET /payment-gate/` | `["payment-gate"]` |
| `useUpgradeQuotes(ids)` | `GET /subscriptions/upgrade-quote/` | batched via `useQueries` |
| `useCheckoutMutation()` | `POST /subscriptions/checkout/` | `onSuccess: window.location.href = data.payment_link` |
| `useRecheckSubscriptionMutation()` | `POST /subscriptions/<id>/recheck/` | `setQueryData(["subscription","me"])` + toast |
| `useCancelPendingMutation()` | `POST /subscriptions/cancel-pending/` | invalidates `["subscription","me"]` |

`api/v1` base + `Authorization: Token <token>` set in `frontend/src/lib/api.ts`.

**Checkout = full-page redirect** (`window.location.href = payment_link`) to Mayar's
hosted page; `checkout-redirecting-overlay.tsx` shows during it.

**SSE** (`app/realtime.ts`): `useUserEvents` opens
`EventSource(.../subscriptions/stream/?token=<token>)`. `useRealtimeQueryInvalidation`
(mounted in `features/auth/components/auth-gate.tsx`) handles `subscription.activated` by
invalidating `["subscription","me"]`, `["plans"]`, `["payment-gate"]` and toasting
"Langganan aktif. Pencocokan harian sudah jalan." The UI **never trusts the redirect-back**
— it waits for this event or the user clicks recheck.

UI orchestration: `routes/plans.index.tsx` renders the plan grid + banners. Components:
`plan-card.tsx` (shows `price`/`effective_price`, upgrade credit + bonus days),
`upgrade-confirm-dialog.tsx` (preview quote before checkout),
`current-subscription-banner.tsx` (PENDING → resume link / recheck / cancel),
`payment-gate-banner.tsx` (locked reason).

---

## 12. End-to-end

```
SPA /plans ──checkout──► billing_api.create ──create_payment_link──► Mayar
   │  201 {subscription_id, payment_link}                              │
   └─ window.location.href = payment_link ─► Mayar hosted page ◄───────┘
                                                  │ user pays
        ┌─────────────────────────────────────────┼──────────────────────────┐
        ▼                          ▼               ▼                           ▼
  payments_api.webhook   poll_subscription   poll_pending_subscriptions   billing_api.recheck
  (X-Callback-Token)     _after_checkout     (beat, 48h sweep)            (user button)
        └──────────────────────────┴───────────────┴───────────────────────────┘
                                    │  all call ↓ (idempotent)
                          activate_subscription(sub)
                          PENDING→ACTIVE, expiry, unlock Prefs, crawl, publish
                                    │  Redis user:{id}:events
                                    ▼
                   billing_api.stream (SSE ?token=) ──► app/realtime.ts
                   invalidate subscription/plans/payment-gate ──► refetch + toast
```

---

## 13. Reproduce it in a new Django project

1. **Adapter** — `core/payments/mayar.py`: `create_payment_link`, `get_payment_status`,
   `verify_webhook`, `MayarError`, `PAID/FAILED_STATUSES`. Settings: 4 env vars (§2).
2. **Models** — `Plan`, `Subscription` (status enum, `payment_ref` indexed,
   `payment_provider`, `amount_paid`, `replaces`); migrate.
3. **Pricing** — `effective_price()` + your discount rule (§4); test all branches.
4. **Activation** — `activate_subscription` + `cancel_pending_subscription` (§7). Test
   idempotency (call twice → 2nd is no-op) and new-vs-upgrade branches.
5. **Checkout view** — txn + `select_for_update` existing-PENDING guard + downgrade reject
   + provider-failure `sub.delete()` → 502 + schedule post-checkout poll (§5).
6. **Webhook view** — `AllowAny`, token verify, lookup by `payment_ref`, event→action map,
   500-on-failure for retries (§6).
7. **Celery** — both pollers (§9); register the 48h sweep in beat (DatabaseScheduler).
8. **Upgrade quote** view + `compute_upgrade_quote` (§8), formula synced with activation.
9. **Realtime** — Redis `publish`/`user_channel` + SSE `stream` with `?token=` (§10).
10. **Recheck** view (§9.4).
11. **Frontend** — checkout→redirect, SSE invalidation, pending banner, upgrade dialog (§11).

## 14. Gotchas

- **Idempotency is load-bearing.** Webhook + 2 pollers + recheck can all fire for one
  payment, concurrently. `activate_subscription` must be a clean no-op when already ACTIVE,
  and the old-sub retirement is guarded `status=ACTIVE` to stop double-upgrade races.
- **Integer IDR everywhere.** Never floats for money.
- **`amount_paid`, not `plan.price`,** drives proration (discounted users paid less).
- **Roll back the orphan.** Mayar call fails after the PENDING row exists → `sub.delete()`
  + 502; an orphan PENDING with no link breaks the existing-PENDING guard.
- **Reject downgrade & same-plan** before charging (`UpgradeNotAllowed`).
- **Webhook is public** (`AllowAny`); its only auth is `X-Callback-Token`. Return 5xx on
  internal failure (Mayar retries), 200 on unhandled events (don't make it retry forever).
- **`MAYAR_BASE_URL` host mismatch:** `.env.example` ships `api.mayar.club`, code fallback
  is `api.mayar.id`. Set it explicitly.
- **SSE token in query string** (EventSource limitation) — treat it like any bearer token.
- **Don't trust the post-pay redirect.** Activation truth = the `subscription.activated`
  SSE event (or recheck).
- **Bound the sweep** to 48h so it never scans all history.
- **Keep the bonus formula in sync** across `compute_upgrade_quote` (preview) and
  `activate_subscription` (apply).
```
