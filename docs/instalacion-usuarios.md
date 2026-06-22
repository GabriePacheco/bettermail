# Instalacion de BetterMail AI

## Instalacion publica desde Microsoft AppSource

Esta sera la ruta recomendada cuando Microsoft apruebe la aplicacion.

1. Abre Outlook en la web o el cliente de escritorio.
2. Crea un correo nuevo.
3. Abre **Aplicaciones** en la barra del mensaje.
4. Selecciona **Obtener complementos**.
5. Busca `BetterMail AI` y selecciona **Agregar**.
6. Vuelve al correo, abre **Aplicaciones** y selecciona **BetterMail AI**.
7. Opcionalmente, fija el panel para mantenerlo visible.

BetterMail AI no necesita una cuenta adicional. Identifica la cuenta activa de Outlook y ofrece el trial disponible para esa cuenta.

## Instalacion de prueba con manifest

Esta ruta es solo para pruebas internas o certificacion antes de AppSource.

1. Descomprime `BetterMail-AI-1.0.0.zip`.
2. Abre Outlook en la web con la cuenta de prueba.
3. Abre **Aplicaciones** y luego **Obtener complementos**.
4. Busca la opcion para agregar una aplicacion personalizada desde un archivo.
5. Selecciona `manifest.xml` dentro del paquete.
6. Acepta la advertencia de instalacion personalizada.
7. Crea un correo nuevo y abre BetterMail AI desde **Aplicaciones**.

Si la organizacion bloquea aplicaciones personalizadas, un administrador de Microsoft 365 debe cargar `manifest.xml` desde **Integrated apps** en el centro de administracion.

## Requisitos

- Outlook moderno con conexion a Internet.
- Acceso HTTPS a `https://bettermailai.web.app`.
- Acceso HTTPS a `https://bettermail-api-202646537583.us-central1.run.app`.
- Navegador Edge o Chrome actualizado para Outlook web.

## Soporte

- Pagina: https://bettermailai.web.app/support
- Email: gabriel.pacheco.developer@gmail.com

