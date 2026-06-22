# Plan actualizado: BetterMail AI listo para aprobacion de Microsoft

Ultima actualizacion: 2026-06-16

## Objetivo

Preparar BetterMail AI para envio, revision y aprobacion como Outlook Add-in en Microsoft AppSource.

La version 1.0 debe enfocarse en certificacion, confianza y estabilidad. No se deben agregar funciones fuera de lo necesario para que Microsoft pueda revisar la app, instalarla, probarla y entender claramente privacidad, soporte, terminos y pagos.

## Estado auditado del repo

Repositorio: `E:\Gabriel\bettermail`

Stack actual confirmado:

- Frontend: React/Vite en `frontend/`.
- Taskpane Outlook: Office.js en `frontend/src/pages/Taskpane.jsx`.
- Backend: FastAPI en `app/`.
- Firestore: servicios en `app/firebase_service.py`.
- IA: OpenAI desde `app/openai_service.py`.
- Billing: PayPhone Cajita iniciado en `app/billing_service.py` y `app/payphone_service.py`.
- Build estatico actual: `frontend/scripts/build-frontend.js` copia `frontend/dist` hacia `app/static`.
- Docker Cloud Run: `Dockerfile`.

Validaciones locales ejecutadas:

```powershell
cd E:\Gabriel\bettermail\frontend
npm.cmd run build
npm.cmd run lint
```

Resultado: pasan.

```powershell
cd E:\Gabriel\bettermail
python -m compileall app
```

Resultado: pasa sintacticamente.

Nota: para importar FastAPI localmente se debe usar el virtualenv del repo:

```powershell
cd E:\Gabriel\bettermail
.\venv\Scripts\python.exe -m compileall app
```

## Bloqueantes confirmados

Estos puntos bloquean o ponen en riesgo una aprobacion en Microsoft si no se corrigen:

1. No existe `manifest.xml` versionado en el repo.
2. No existe `firebase.json` ni `.firebaserc`.
3. En `APP_ENV=production`, `/debug/env` y `/debug/network` siguen expuestos.
4. En `APP_ENV=production`, `/openapi.json` queda visible aunque `/docs` y `/redoc` se ocultan.
5. El frontend compila `VITE_APP_SHARED_SECRET` dentro del JavaScript. No se debe tratar como secreto real.
6. Faltan paginas publicas reales para `/privacy`, `/terms`, `/support`, `/security`, `/contact` y `/appsource-test`.
7. El prompt de `/rewrite` no contiene reglas explicitas para transformar agresividad verbal en comunicacion profesional.
8. Faltan endpoints de billing esperados por el plan: cancelacion, reactivacion, bloqueo/desbloqueo admin y renovacion interna.
9. No existe carpeta `marketplace/` con materiales para Partner Center.
10. `API.md` esta en `.gitignore`, por lo que el documento actual no queda versionado aunque existe localmente.

## Decisiones pendientes requeridas

Antes de cerrar certificacion:

- URL Firebase definitiva: `https://bettermailai.web.app`.
- URL Cloud Run definitiva: `https://bettermail-api-202646537583.us-central1.run.app`.
- Email publico de soporte.
- ProviderName legal/comercial para el manifest.
- Confirmar si el idioma principal de AppSource sera ingles, espanol o ambos.
- Confirmar que version 1.0 no declarara mobile.
- Confirmar si PayPhone soporta cobro recurrente real con token. Si no, usar renovacion manual mensual.

## Arquitectura objetivo

### Firebase Hosting

Debe servir:

- `/` landing publica.
- `/taskpane.html` taskpane del add-in.
- `/pricing` pagina publica de plan Pro y checkout.
- `/support` soporte publico.
- `/privacy` politica de privacidad.
- `/terms` terminos/EULA.
- `/security` resumen de seguridad.
- `/contact` contacto.
- `/appsource-test` instrucciones para certificadores.
- Assets publicos: iconos, logos, capturas y archivos compilados.

### Cloud Run

Debe quedar como API:

- `/health`
- `/usage/status`
- `/rewrite`
- `/plans`
- `/billing/*`
- endpoints internos protegidos para renovacion o administracion.

No debe exponer UI publica como solucion final, salvo fallback temporal.

### Outlook Add-in

Debe usar manifest de produccion:

- `SourceLocation`: `https://bettermailai.web.app/taskpane.html`, no Cloud Run ni localhost.
- `SupportUrl`: pagina publica de soporte.
- `AppDomains`: Firebase, Cloud Run, PayPhone si aplica y dominios necesarios de Office.
- Host: Outlook solamente.
- Extension point: compose.
- Sin mobile en version 1.0.
- Sin `ItemSend` ni eventos bloqueantes.

## Sprint 1: certificacion bloqueante

Orden recomendado:

1. Crear `manifest.xml` de produccion.
2. Crear `firebase.json` y `.firebaserc`.
3. Ajustar Vite/Firebase para servir rutas publicas sin depender de Cloud Run.
4. Crear paginas `/privacy`, `/terms`, `/support`, `/security`, `/contact` y `/appsource-test`.
5. Corregir seguridad de produccion:
   - deshabilitar `/debug/env` y `/debug/network` fuera de development;
   - ocultar `/openapi.json` en produccion;
   - revisar headers de seguridad en Firebase.
6. Ajustar prompt de IA para transformar agresividad verbal no fisica en texto profesional.
7. Agregar pruebas manuales o automaticas para casos dificiles de IA.
8. Validar manifest.
9. Probar taskpane en Outlook web moderno.

### Cambios especificos de backend para Sprint 1

En `app/main.py`:

- Usar `openapi_url="/openapi.json" if settings.app_env == "development" else None`.
- Registrar endpoints `/debug/*` solo si `settings.app_env == "development"`.
- Mantener `/health` publico.
- Mantener docs/redoc solo en development.

En `app/openai_service.py`:

- Agregar reglas explicitas de transformacion segura:
  - transformar enojo, insultos y amenazas verbales no fisicas en tono firme, profesional y respetuoso;
  - no conservar amenazas;
  - no amplificar violencia;
  - no inventar hechos;
  - no hacer acusaciones legales no sustentadas;
  - rechazar solo si el usuario pide conservar o ejecutar dano real, crimen, acoso dirigido o amenaza directa.

En `app/security.py` y servicios relacionados:

- Mantener `APP_SHARED_SECRET` como barrera ligera, no como seguridad principal.
- Preparar controles reales por IP y email hash.
- Evitar exponer detalles de secretos en cualquier entorno publico.

### Cambios especificos de frontend para Sprint 1

En `frontend/src/api/bettermailApi.js`:

- Preparar `getPricingUrl` para apuntar a Firebase `/pricing`, no a `${API_BASE_URL}/static/pricing.html`.
- Mantener llamadas API hacia Cloud Run.
- Evitar mostrar errores tecnicos al usuario.

En taskpane:

- Mantener UI compacta.
- No mostrar stack traces, nombres internos, errores crudos de HTTP, OpenAI o Firestore.
- Primer uso:
  - si hay borrador, mejorar inmediatamente;
  - si hay contexto y borrador vacio, sugerir respuesta;
  - si no hay contenido, mostrar mensaje simple.

## Sprint 2: pagos y suscripcion

Estado actual:

- `POST /billing/checkout`: existe.
- `GET /billing/checkout/{order_id}`: existe.
- `POST /billing/payphone/confirm`: existe.
- `POST /billing/status` y `GET /billing/status`: existen.
- `POST /billing/manual-activate`: existe, pero debe moverse o duplicarse como endpoint admin protegido.

Agregar:

- `POST /billing/cancel`
- `POST /billing/reactivate`
- `POST /billing/admin/manual-activate`
- `POST /billing/admin/block-user`
- `POST /billing/admin/unblock-user`
- `POST /billing/internal/renew-subscriptions`

Agregar configuracion:

```env
INTERNAL_JOB_SECRET=
ADMIN_API_SECRET=
```

Reglas:

- `INTERNAL_JOB_SECRET` debe ser distinto de `APP_SHARED_SECRET`.
- Endpoints admin no deben depender del secreto compilado en frontend.
- Si PayPhone no confirma cobro recurrente real, no prometer suscripcion automatica. Usar renovacion manual cada 30 dias.

## Sprint 3: datos, observabilidad y marketplace

Firestore:

- Confirmar colecciones:
  - `mailbox_users`
  - `usage_logs`
  - `plans`
  - `payment_orders`
  - `subscriptions`
  - `billing_events`
  - `payment_methods`
  - `audit_logs`
  - `blocked_users`

Datos personales:

- Usar email normalizado y hash SHA-256 como ID principal.
- Guardar email en texto solo cuando sea necesario para soporte/billing.
- Documentar esto en privacidad.

Observabilidad:

- Registrar request ID, endpoint, status, duracion, email hash, modo, tono, resultado y categoria de error.
- No registrar texto completo del correo.
- No registrar secretos, tarjetas ni respuestas completas de IA.

Marketplace:

Crear carpeta `marketplace/` con:

- `app-description-short.md`
- `app-description-long.md`
- `keywords.md`
- `test-notes.md`
- `support-url.txt`
- `privacy-url.txt`
- `terms-url.txt`
- `screenshots/`
- `icons/`
- `manifest-production.xml`

## Paginas publicas requeridas

### `/privacy`

Debe mencionar:

- BetterMail AI por nombre.
- Email del usuario.
- Nombre mostrado si Outlook lo entrega.
- Texto del borrador enviado voluntariamente.
- Contexto del correo cuando se usa `suggest_reply`.
- Metadatos de uso: fecha, tono, modo y longitudes.
- Estado de plan y pagos.
- Google Cloud Run, Firestore, OpenAI y PayPhone.
- Que no se vende informacion personal.
- Que no se almacenan tarjetas.
- Que no se lee el buzon completo.
- Que no se envian correos automaticamente.
- Como pedir eliminacion de datos.

### `/terms`

Debe incluir:

- Uso permitido.
- Uso prohibido.
- Naturaleza asistiva de la IA.
- El usuario debe revisar antes de enviar.
- No garantia de exactitud legal.
- Trial y Pro.
- Cancelacion.
- Reembolsos si aplica.
- Limitacion de responsabilidad.
- Contacto.

### `/support`

Debe incluir:

- Que es BetterMail AI.
- Como instalarlo desde Outlook Apps.
- Como abrir el panel.
- Como reescribir un correo.
- Como reemplazar texto.
- Como consultar/cancelar plan.
- Problemas frecuentes.
- Email de soporte.

### `/security`

Debe explicar:

- La app procesa solo el contenido necesario.
- El usuario controla cuando aplicar el texto.
- La app no envia correos sola.
- Los pagos se procesan por proveedor externo.
- No se guardan tarjetas.
- Los datos viajan por HTTPS.
- Se puede solicitar eliminacion de datos.

### `/appsource-test`

Debe incluir instrucciones para Microsoft:

- Como instalar el add-in.
- Como abrirlo en compose.
- Como probar un borrador.
- Como probar respuesta con contexto.
- Como probar trial.
- Como probar Pro.
- Datos sandbox de PayPhone, si existen.
- Aclaracion de que BetterMail AI no envia correos automaticamente.

## QA minimo para certificacion

Probar:

- Outlook web moderno en Edge.
- Outlook web moderno en Chrome.
- Outlook Windows si esta disponible.
- Nuevo Outlook Windows si esta disponible.
- Modo claro.
- Modo oscuro.
- Borrador nuevo.
- Respuesta a correo existente.
- Texto vacio.
- Texto largo.
- Texto agresivo transformado a profesional.
- Trial disponible.
- Trial agotado.
- Pro activo.
- API caida.
- OpenAI error.
- Pago aprobado.
- Pago rechazado.
- Pago pendiente.

Casos de IA:

1. `Necesito que me envies el reporte hoy.`
2. `No estoy de acuerdo con la decision.`
3. `Esto es inaceptable, necesito una solucion.`
4. `Quiero romperte...`
5. `Respondeme ya o voy a escalar esto.`
6. Borrador vacio con contexto.
7. Texto con formato HTML.
8. Texto con firma.
9. Respuesta con hilo citado.
10. Correo largo de mas de 5000 caracteres.

## Comandos de validacion

Frontend:

```powershell
cd E:\Gabriel\bettermail\frontend
npm.cmd run build
npm.cmd run lint
```

Backend:

```powershell
cd E:\Gabriel\bettermail
.\venv\Scripts\python.exe -m compileall app
```

Build estatico para Cloud Run temporal:

```powershell
cd E:\Gabriel\bettermail\frontend
npm.cmd run build:frontend
```

Manifest, cuando exista:

```powershell
cd E:\Gabriel\bettermail
npx office-addin-manifest validate -p manifest.xml
```

Firebase, cuando exista `firebase.json`:

```powershell
cd E:\Gabriel\bettermail
firebase deploy --only hosting
```

## Checklist post-deploy

- `/health` responde ok.
- `/docs` no abre en produccion.
- `/redoc` no abre en produccion.
- `/openapi.json` no abre en produccion.
- `/debug/env` no abre en produccion.
- `/debug/network` no abre en produccion.
- Landing abre por HTTPS.
- Privacy abre por HTTPS.
- Terms abre por HTTPS.
- Support abre por HTTPS.
- Security abre por HTTPS.
- Taskpane abre por HTTPS.
- Pricing abre por HTTPS.
- Checkout crea orden.
- Confirmacion PayPhone funciona o muestra fallback claro.
- Manifest valida sin errores.
- SourceLocation no usa localhost.
- SupportUrl no usa localhost.
- No se declara mobile en version 1.0.

## Definicion de terminado

La preparacion esta completa cuando:

- Build frontend pasa.
- Lint frontend pasa.
- Backend compila/importa.
- Manifest valida.
- Firebase Hosting sirve taskpane, landing, pricing y paginas legales.
- Cloud Run queda como API.
- No hay debug ni OpenAPI expuestos en produccion.
- CORS esta restringido a origenes reales.
- Prompt transforma textos agresivos no fisicos en mensajes profesionales.
- Hay flujo trial y Pro.
- Hay soporte/cancelacion documentados.
- Hay carpeta `marketplace/` lista.
- Hay evidencia de QA para Outlook web moderno.
- El paquete esta listo para cargar en Partner Center.
