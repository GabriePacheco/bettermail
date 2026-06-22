# BetterMail AI Internal Admin

## Access

The internal panel is available at:

`https://bettermailai.web.app/internal-admin`

Secret Manager:

`https://console.cloud.google.com/security/secret-manager/secret/bettermail-admin-api-secret/versions?project=teleasnews`

It is intentionally absent from public navigation and has `noindex` headers. The URL is not an authentication mechanism; every API request still requires `ADMIN_API_SECRET`.

Use the local helper to open the panel and copy the secret without printing it:

```powershell
cd E:\Gabriel\bettermail
.\scripts\open-admin.ps1
```

The secret remains only in the page memory after it is pasted. The panel does not use cookies, `localStorage` or `sessionStorage` for the secret.

If the local Google Cloud CLI cannot validate the corporate certificate, the helper opens Secret Manager instead of disabling TLS.

## Available actions

- Look up a user by exact Outlook email.
- Review trial, Pro usage, subscription status and billing metadata.
- Activate Pro manually for 30 days without charging.
- Block or unblock access.
- Schedule cancellation at the end of the current period.
- Expire Pro immediately.
- Review recent administrative audit events.

## Safety rules

- Always enter a reason before a mutation.
- Never paste the admin secret into chat, screenshots, tickets or source files.
- Do not use manual activation for an already active subscription.
- Use immediate expiration only for confirmed support, fraud or refund cases.
- The panel never exposes card tokens, card numbers, security codes, email content or PayPhone secrets.

## API routes

- `POST /billing/admin/user`
- `POST /billing/admin/manual-activate`
- `POST /billing/admin/block`
- `POST /billing/admin/unblock`
- `POST /billing/admin/cancel`
- `POST /billing/admin/expire`

All routes require the `X-Admin-Secret` header and are rate limited.
