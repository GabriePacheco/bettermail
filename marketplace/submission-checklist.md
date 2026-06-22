# BetterMail AI AppSource Submission Checklist

Use this file when filling the Microsoft Partner Center offer.

## Offer Basics

- Product name: BetterMail AI
- Publisher/provider: BetterMail AI
- Product type: Office Add-in / Outlook add-in
- Primary language: English
- Secondary language: Spanish
- Category: Productivity
- Support contact: gabriel.pacheco.developer@gmail.com

## Public URLs

- Landing page: https://bettermailai.web.app/
- Taskpane: https://bettermailai.web.app/taskpane.html
- Pricing: https://bettermailai.web.app/pricing
- Support: https://bettermailai.web.app/support
- Privacy: https://bettermailai.web.app/privacy
- Terms: https://bettermailai.web.app/terms
- Security: https://bettermailai.web.app/security
- Certification test page: https://bettermailai.web.app/appsource-test
- API health: https://bettermail-api-202646537583.us-central1.run.app/health

## Manifest

- Upload: `manifest.xml`
- Backup copy: `marketplace/manifest-production.xml`
- SourceLocation: `https://bettermailai.web.app/taskpane.html?v=20260617-2`
- SupportUrl: `https://bettermailai.web.app/support`
- Hosts: Outlook only
- Form factor: desktop compose
- No mobile support declared in Sprint 1
- No ItemSend or blocking event handlers

## Listing Text

- Short description: `marketplace/app-description-short.md`
- Long description: `marketplace/app-description-long.md`
- Keywords: `marketplace/keywords.md`
- Certification notes: `marketplace/test-notes.md`

## Recommended Screenshots

Use the polished store screenshots first. They are 1366 x 768 images built from real product screenshots with a clean frame and basic demo-data masking.

- `marketplace/screenshots/store/01-store-rewrite-professional.png`
- `marketplace/screenshots/store/02-store-suggested-replies.png`
- `marketplace/screenshots/store/03-store-usage-and-pro.png`
- `marketplace/screenshots/store/04-store-pricing-page.png`
- `marketplace/screenshots/store/05-store-secure-checkout.png`

Keep the raw screenshots only as internal references.

## Validation To Run Before Submission

From `E:\Gabriel\bettermail\frontend`:

```powershell
npm.cmd run build
npm.cmd run lint
```

From `E:\Gabriel\bettermail`:

```powershell
.\venv\Scripts\python.exe -m compileall app
$env:NODE_OPTIONS='--use-system-ca'
npx.cmd --yes office-addin-manifest validate -p manifest.xml
```

Expected backend production behavior:

- `/health` returns 200
- `/docs` returns 404
- `/redoc` returns 404
- `/openapi.json` returns 404
- `/debug/env` returns 404
- `/debug/network` returns 404

## Known Notes For Microsoft Review

- BetterMail AI does not send emails automatically.
- The user must review and apply generated text manually.
- The add-in reads only the current draft/context needed for the requested action.
- Payment is handled by PayPhone Cajita; BetterMail AI does not store card data.
- PayPhone allowed domain: `https://bettermailai.web.app`
- PayPhone response URL: `https://bettermailai.web.app/pricing`
