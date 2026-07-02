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

## Temporary Pro Certification Access

- Activation page: https://bettermailai.web.app/appsource-test
- Use the same email address as the Outlook account running the add-in.
- Certification license key: `[PASTE THE CURRENT PARTNER CENTER CERTIFICATION KEY]`
- Access duration: 7 days.
- The certification entitlement does not charge a card and does not renew automatically.
- Close and reopen the BetterMail AI taskpane after activation.
- The certification key is separate from all administrative credentials and may be rotated after review.

## Suggested Certification Steps

1. Install the manifest in Outlook on the web.
2. Open a new message compose window.
3. Open BetterMail AI from the compose command surface.
4. Type a draft such as: `Necesito que me envies el reporte hoy.`
5. Confirm BetterMail AI generates a clearer professional version.
6. Use Replace, Insert below, Copy, and Regenerate.
7. Change the selected tone and confirm the current generated suggestion remains visible.
8. Use Replace on a draft with an Outlook signature and confirm the signature remains intact.
9. Open a reply with an empty draft and confirm the add-in can suggest a response from the previous email context.
10. Activate temporary Pro using the certification page and license above.
11. Reopen the taskpane, select `My tone / Mi tono`, define a custom personality, and generate a suggestion.
12. Confirm the selected tone remains the default after the taskpane is reopened.
13. Test a difficult non-physical aggressive draft such as: `Respondeme ya o voy a escalar esto.`
14. Confirm the result is firm, professional, and does not preserve threats or insults.

## Payment Notes

BetterMail Pro checkout uses PayPhone Cajita. The allowed PayPhone web domain is `https://bettermailai.web.app` and the response URL is `https://bettermailai.web.app/pricing`.

Sandbox card data must be provided separately by the publisher if PayPhone sandbox testing is required.

Temporary Pro certification access is the supplied license-key path for reviewing paid features without executing a real payment.

## Production API Notes

- API health URL: https://bettermail-api-202646537583.us-central1.run.app/health
- Production API documentation endpoints are disabled.
- `/openapi.json`, `/docs`, `/redoc`, `/debug/env`, and `/debug/network` return 404 in production.

## Important Behavior

BetterMail AI does not send emails automatically. The user controls whether suggested text is applied to the message.
