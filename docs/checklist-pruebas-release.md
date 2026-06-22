# Checklist de pruebas antes de release

Fecha: __________  Version: __________  Responsable: __________

## Validacion automatica

- [ ] `frontend`: `npm.cmd run build`
- [ ] `frontend`: `npm.cmd run lint`
- [ ] Backend: `.\venv\Scripts\python.exe -m compileall app`
- [ ] Tests: `.\venv\Scripts\python.exe -m unittest discover -s tests -v`
- [ ] Manifest: `npx.cmd --yes office-addin-manifest validate -p manifest.xml`
- [ ] `git diff --check` no reporta errores.
- [ ] No hay secretos reales en archivos versionados.

## Produccion y seguridad

- [ ] `/health` devuelve HTTP 200.
- [ ] `/docs`, `/redoc` y `/openapi.json` devuelven HTTP 404.
- [ ] `/debug/env` y `/debug/network` devuelven HTTP 404.
- [ ] CORS acepta Firebase Hosting y rechaza origenes no autorizados.
- [ ] Las paginas publicas usan HTTPS y abren sin autenticacion.
- [ ] La pagina administrativa no aparece en la navegacion publica.
- [ ] Una clave administrativa incorrecta devuelve HTTP 401.

## Outlook

- [ ] El complemento abre a la primera en Outlook web con Edge.
- [ ] El complemento abre a la primera en Outlook web con Chrome.
- [ ] Detecta un borrador nuevo.
- [ ] Reescribe con cada tono disponible.
- [ ] Convierte texto agresivo no fisico en texto profesional.
- [ ] Genera respuesta sugerida con borrador vacio y contexto previo.
- [ ] **Reemplazar** conserva firma y cadena anterior.
- [ ] El foco vuelve al texto nuevo despues de reemplazar una respuesta.
- [ ] **Poner debajo**, **Copiar**, **Regenerar** y **Actualizar** funcionan.
- [ ] Ningun error muestra detalles de OpenAI, Firestore o HTTP.

## Uso y pagos

- [ ] El trial incrementa exactamente una vez por mejora exitosa.
- [ ] El trial agotado bloquea nuevas mejoras.
- [ ] **Hazte Pro** abre `https://bettermailai.web.app/pricing`.
- [ ] PayPhone carga la cajita con una orden nueva.
- [ ] Un pago aprobado activa Pro y reinicia el uso mensual.
- [ ] Un pago rechazado no activa Pro.
- [ ] Cancelar programa el fin del plan sin retirar el periodo pagado.
- [ ] Expirar desde administracion retira Pro inmediatamente.
- [ ] El job de renovacion en `dry_run` no realiza cobros.

## Costos y observabilidad

- [ ] Una mejora crea un `usage_logs` con conteos de tokens.
- [ ] `operational_metrics/openai_YYYY-MM-DD` incrementa una solicitud.
- [ ] El panel administrativo muestra costo, solicitudes y tokens de 30 dias.
- [ ] Las tarifas configuradas coinciden con el modelo activo.
- [ ] El costo estimado se contrasta con el panel de uso/facturacion de OpenAI.

## Material de publicacion

- [ ] `scripts/package-release.ps1` genera el ZIP sin errores.
- [ ] El ZIP contiene `manifest.xml`, instalacion, guia y checklist.
- [ ] Los cinco screenshots de tienda corresponden a la version actual.
- [ ] Support, Privacy, Terms y AppSource test no devuelven 404.
- [ ] Se actualizo `marketplace/test-notes.md` si cambio el flujo.

Resultado final: [ ] APROBADO  [ ] RECHAZADO

Observaciones:

____________________________________________________________________

