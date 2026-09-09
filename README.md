# quierorenting.es

La web de Quiero Renting: **HTML estático escrito a mano**, sin framework y sin
build. Cada carpeta es una URL: `renting-bmw-x3/index.html` se sirve en
`/renting-bmw-x3/`.

## Cómo se publica

**Haciendo push a `master`.** El repositorio está conectado al proyecto
`quiero-renting` de Vercel, que despliega solo en cada push.

En Vercel, el **Root Directory del proyecto es `sitio-nuevo`**, no la raíz del
repositorio. De ahí salen tres consecuencias que conviene tener presentes:

- La web vive en `sitio-nuevo/`. Lo que hay en la raíz (los scripts de Python)
  no se publica.
- `sitio-nuevo/api/lead.js` es una **función de servidor** de Vercel, la que
  recibe los formularios. Vercel la detecta porque está en `api/` dentro del
  root directory. Si algún día se mueve esa carpeta, el formulario deja de
  recibir leads sin avisar de nada.
- `sitio-nuevo/vercel.json` lleva las redirecciones de los modelos retirados.

Si alguna vez hace falta desplegar a mano, se hace **desde la raíz del
repositorio**, no desde `sitio-nuevo/`:

```bash
npx vercel deploy --prod --yes --scope adri-daganzos-projects
```

## Antes de subir nada

```bash
node sitio-nuevo/comprobar.js
```

Comprueba que las páginas y los coches cuadran entre sí. No hay build que avise
de un error, así que esto es lo único que hay.

## Secretos

Ninguno vive en el repositorio. `api/lead.js` lee `WEB3FORMS_API_KEY`,
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` y las de HubSpot de las variables de
entorno del proyecto de Vercel. **No las escribas en el código**: este
repositorio es público.
