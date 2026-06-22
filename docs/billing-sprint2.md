# BetterMail AI Billing Sprint 2

## Implemented lifecycle

- PayPhone payment confirmation activates a deterministic subscription per account.
- A reusable PayPhone card token enables recurring renewal.
- Cancellation is scheduled for the end of the paid period.
- Cancellation can be reversed before the period ends.
- Rejected renewals move the subscription to `past_due`.
- `past_due` keeps access during a configurable grace period.
- Successful renewal resets monthly usage and starts a new 30-day period.
- Repeated failure or the end of the grace period expires Pro.
- Expired Pro accounts do not receive a second trial.

## API endpoints

- `POST /billing/cancel`
- `POST /billing/reactivate`
- `POST /billing/admin/manual-activate`
- `POST /billing/internal/renew-subscriptions`
- `POST /billing/status`

The admin and internal endpoints use private secrets that must never be compiled into the frontend.

## Required production configuration

```env
ADMIN_API_SECRET=<random-private-secret>
INTERNAL_JOB_SECRET=<different-random-private-secret>
PAYPHONE_RECURRING_ENABLED=false
PAYPHONE_STORE_ID=<payphone-store-id>
BILLING_GRACE_DAYS=3
BILLING_MAX_RENEWAL_ATTEMPTS=3
```

Recurring billing requires `PAYPHONE_TOKEN`, `PAYPHONE_STORE_ID` and `PAYPHONE_CODING_PASSWORD`. Keep `PAYPHONE_RECURRING_ENABLED=false` until a token charge has been validated in PayPhone sandbox. Then enable it explicitly in Cloud Run.

## Safe rollout

1. Deploy with recurring billing disabled.
2. Create both private secrets in Secret Manager and attach them to Cloud Run.
3. Call the renewal endpoint with `dry_run=true`.
4. Confirm the response only reports the expected due subscriptions.
5. Validate one PayPhone token renewal in sandbox.
6. Set `PAYPHONE_RECURRING_ENABLED=true`.
7. Create a daily Cloud Scheduler job.

Example dry run:

```powershell
$headers = @{ "X-Internal-Job-Secret" = $env:INTERNAL_JOB_SECRET }
$body = @{ limit = 100; dry_run = $true } | ConvertTo-Json
Invoke-RestMethod `
  -Method Post `
  -Uri "https://bettermail-api-202646537583.us-central1.run.app/billing/internal/renew-subscriptions" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
```

## Scheduler

Run the internal endpoint once per day. The scheduler request must include:

- Method: `POST`
- Header: `X-Internal-Job-Secret`
- Body: `{ "limit": 100, "dry_run": false }`

The renewal attempt identifier is deterministic for each subscription period and attempt number, which prevents concurrent workers from intentionally charging the same attempt twice. Provider timeouts are recorded as failures and retried on the next scheduled day.

## Operational states

- `active`: Pro is usable and renewal is enabled.
- `cancel_pending`: Pro remains usable until `currentPeriodEnd`; no renewal is attempted.
- `past_due`: renewal failed; access continues until `gracePeriodEnd`.
- `cancelled`: the user cancellation reached the end of the paid period.
- `expired`: payment could not be recovered or manual renewal is required.

## Tests

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```
