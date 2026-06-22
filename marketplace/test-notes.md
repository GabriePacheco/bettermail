# BetterMail AI AppSource Test Notes

## Public URLs

- Taskpane: https://bettermailai.web.app/taskpane.html
- Taskpane cache-busted SourceLocation: https://bettermailai.web.app/taskpane.html?v=20260617-2
- Support: https://bettermailai.web.app/support
- Privacy: https://bettermailai.web.app/privacy
- Terms: https://bettermailai.web.app/terms
- Pricing: https://bettermailai.web.app/pricing
- AppSource test page: https://bettermailai.web.app/appsource-test

## Test Account

BetterMail AI does not require an initial login. It uses the Outlook user profile provided by Office.js.

## Suggested Certification Steps

1. Install the manifest in Outlook on the web.
2. Open a new message compose window.
3. Open BetterMail AI from the compose command surface.
4. Type a draft such as: `Necesito que me envies el reporte hoy.`
5. Confirm BetterMail AI generates a clearer professional version.
6. Use Replace, Insert below, Copy, and Regenerate.
7. Open a reply with an empty draft and confirm the add-in can suggest a response from the previous email context.
8. Test a difficult non-physical aggressive draft such as: `Respondeme ya o voy a escalar esto.`
9. Confirm the result is firm, professional, and does not preserve threats or insults.
10. Use the trial until exhausted and confirm the Pro call to action opens https://bettermailai.web.app/pricing.
11. Click Continue on the Pro plan and confirm the PayPhone payment box loads.
12. After approving a PayPhone transaction, confirm the page returns to `/pricing` and BetterMail Pro becomes active for the Outlook account.

## Payment Notes

BetterMail Pro checkout uses PayPhone Cajita. The allowed PayPhone web domain is `https://bettermailai.web.app` and the response URL is `https://bettermailai.web.app/pricing`.

Sandbox card data must be provided separately by the publisher if PayPhone sandbox testing is required.

## Production API Notes

- API health URL: https://bettermail-api-202646537583.us-central1.run.app/health
- Production API documentation endpoints are disabled.
- `/openapi.json`, `/docs`, `/redoc`, `/debug/env`, and `/debug/network` return 404 in production.

## Important Behavior

BetterMail AI does not send emails automatically. The user controls whether suggested text is applied to the message.
