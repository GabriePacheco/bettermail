# BetterMail AI Frontend

Frontend React/Vite de BetterMail AI. Contiene el panel del add-in de Outlook, landing, paginas publicas y pagina de planes/checkout para Firebase Hosting.

## Entradas

- `index.html`: carga la landing publica.
- `taskpane.html`: carga el taskpane principal del add-in.
- `pricing.html`: carga la pagina de planes y checkout.

Vite compila las entradas con `base: "/"` para Firebase Hosting. El script `npm run build:frontend` usa `FRONTEND_BASE=/static/` como fallback temporal para copiar el build a `app/static`.

## Taskpane de Outlook

Archivo principal: `src/pages/Taskpane.jsx`.

Funciones principales:

- Lee el borrador y el correo citado desde Outlook con Office.js mediante `useOfficeEmail`.
- Usa modo vista previa cuando no existe `window.Office`, con datos de ejemplo.
- Detecta si debe reescribir el borrador (`rewrite_draft`) o sugerir una respuesta usando contexto (`suggest_reply`).
- Permite elegir tono: profesional, claro, amable, firme, ejecutivo, breve y elegante.
- Llama a la API para consultar uso, planes y reescribir texto.
- Permite reemplazar el borrador, insertar el texto debajo, copiarlo o regenerarlo.
- Muestra estado de plan y abre la pagina de pricing para activar Pro.

## Pricing y checkout

Archivo principal: `src/pages/PricingPage.jsx`.

Flujos soportados:

- Sin `order_id`: muestra seleccion de planes y crea una orden con `POST /billing/checkout`.
- Con `order_id`: carga la orden con `GET /billing/checkout/{order_id}` y renderiza la Cajita de PayPhone si la orden trae configuracion.
- Retorno desde PayPhone: lee `id`, `clientTransactionId` y `ctoken`/`cardToken` de la URL, confirma con `POST /billing/payphone/confirm` y muestra el estado activo.
- Si PayPhone no esta disponible, muestra un estado de pago pendiente/no disponible para que el usuario vuelva a iniciar el checkout.

## Cliente API

Archivo: `src/api/bettermailApi.js`.

Variables requeridas:

```env
VITE_API_BASE_URL=
VITE_PUBLIC_BASE_URL=
VITE_APP_SHARED_SECRET=
```

Todas las llamadas usan JSON y envian `x-app-secret` con `VITE_APP_SHARED_SECRET`. Tambien se acepta `VITE_API_KEY` como fallback local. Este valor queda compilado en el JavaScript del frontend y debe tratarse solo como una barrera ligera, no como un secreto real.

Endpoints usados por el front:

- `POST /usage/status`
- `GET /plans`
- `POST /rewrite`
- `POST /billing/checkout`
- `GET /billing/checkout/{order_id}`
- `POST /billing/payphone/confirm`
- `POST /billing/status`

## Desarrollo

```bash
npm install
npm run dev
```

Para generar los estaticos que sirve FastAPI:

```bash
npm run build:frontend
```

Resultado esperado:

- `app/static/index.html`
- `app/static/taskpane.html`
- `app/static/pricing.html`
- assets compilados bajo `app/static/assets`

## Componentes y utilidades

- `components/TonePills.jsx`: selector compacto de tonos.
- `components/EmailCard.jsx`: area editable del texto generado.
- `components/ActionButtons.jsx`: acciones sobre el texto generado.
- `components/PlanFooter.jsx`: resumen de uso y CTA Pro.
- `hooks/useOfficeEmail.js`: integracion con Outlook, lectura/escritura del body HTML y modo preview.
- `hooks/useOfficeTheme.js`: sincroniza colores con tema de Office o preferencia del sistema.
- `utils/emailHtml.js`: extraccion y reconstruccion del HTML del correo.
