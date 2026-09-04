# -*- coding: utf-8 -*-
"""Sube el acabado de quierorenting.es al nivel de MoviLease.

El paso anterior cambio el color. Esto cambia el acabado, que es lo que
separa "la misma paleta" de "la misma marca":

  1. TIPOGRAFIA. Se unifica en la pareja de MoviLease —Space Grotesk para
     titulares, Inter para texto—. Hoy la home usa Sora + DM Sans y las 36
     landings NO cargan ninguna fuente: van con la del sistema, que es la
     razon de fondo por la que se ven planas al lado de la home.

     Los titulares se bajan a peso 700. Estaban a 800 y 900, y Space Grotesk
     no llega ahi: dejarlos obliga al navegador a engordar el trazo el mismo,
     y un bold sintetico se ve barato justo en lo que mas se mira.

  2. CAPA PREMIUM. Un bloque de CSS al final de cada hoja, no una reescritura
     de las reglas existentes: gana por orden de cascada y no puede corromper
     nada de lo que ya funcionaba. Aporta sombras tenidas de azul marca en
     lugar de negras, degradado sutil en los botones, y elevacion al pasar por
     encima animando solo transform y box-shadow.

  3. MOVIMIENTO ACCESIBLE. La web no tenia ni una excepcion de
     prefers-reduced-motion. Si se anaden transiciones hay que anadirla: es la
     norma en movilease.es y aqui faltaba desde el principio.

    python premium_movilease.py

Se puede reejecutar: la capa lleva marca y no se duplica.
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sitio-nuevo")
MARCA = "CAPA-PREMIUM-MOVILEASE"

FUENTES = ("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700"
           "&family=Inter:wght@400;500;600;700&display=swap")

ENLACE_FUENTES = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="%s" rel="stylesheet">' % FUENTES
)

FAMILIAS = [
    ("'Sora',sans-serif", "'Space Grotesk',sans-serif"),
    ("'DM Sans',sans-serif", "'Inter',sans-serif"),
    ("DM Sans,sans-serif", "'Inter',sans-serif"),
    ("-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif",
     "'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"),
]

BOTONES_AZULES = (".nav-cta,.btn-primary,.card-btn,.cc-btn,.oferta-btn,"
                  ".modal-cta,.lp-btn,.car-btn")
TARJETAS = ".card,.why-card,.faq-item,.cc-card,.oferta-card"

CAPA = """
/* ===== %s =====================================================
   Va al final de la hoja a proposito: gana por cascada sin reescribir
   ninguna de las reglas que ya funcionaban.
   ============================================================== */
:root{
  --ml-ease:cubic-bezier(.16,1,.3,1);
  --ml-sh-md:0 2px 6px rgba(11,42,94,.06),0 18px 44px rgba(11,42,94,.11);
  --ml-sh-blue:0 1px 2px rgba(11,42,94,.16),0 10px 28px rgba(0,104,255,.26);
  --ml-sh-blue-h:0 2px 4px rgba(11,42,94,.18),0 16px 40px rgba(0,104,255,.34);
  --ml-sh-wa:0 1px 2px rgba(11,42,94,.16),0 10px 28px rgba(37,211,102,.28)
}
body{-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}

/* Peso 700 y no mas: Space Grotesk no tiene 800 ni 900, y pedirselos
   solo consigue que el navegador falsifique la negrita. */
h1,h2,h3,.hero-title,.sec-header h2,.nav-logo,.logo,.footer-logo{
  font-family:'Space Grotesk','Sora',sans-serif;font-weight:700;letter-spacing:-.025em
}

/* Sombra tenida del azul de marca en vez de negra, y un degradado vertical
   muy leve: es lo que separa un boton plano de uno con cuerpo. */
%s{
  background-image:linear-gradient(180deg,rgba(255,255,255,.16),rgba(255,255,255,0));
  box-shadow:var(--ml-sh-blue);
  transition:transform .35s var(--ml-ease),box-shadow .35s var(--ml-ease)
}
%s{transform:translateY(-1px);box-shadow:var(--ml-sh-blue-h)}
%s{transform:translateY(0)}

/* El boton de WhatsApp conserva su verde, asi que su sombra se tine de
   verde: una sombra azul bajo un boton verde se ve como un error. */
.cta-wa,.wa-float,.btn-whatsapp{
  box-shadow:var(--ml-sh-wa);
  transition:transform .35s var(--ml-ease),box-shadow .35s var(--ml-ease)
}
.cta-wa:hover,.wa-float:hover,.btn-whatsapp:hover{transform:translateY(-1px)}

/* Elevacion al pasar por encima. Solo transform y box-shadow: cualquier
   otra propiedad provocaria reflow en una rejilla de 99 tarjetas. */
%s{transition:transform .45s var(--ml-ease),box-shadow .45s var(--ml-ease),border-color .45s var(--ml-ease)}
%s{transform:translateY(-4px);box-shadow:var(--ml-sh-md)}

.footer-ml img{height:38px}
.footer-ml{gap:9px;margin-bottom:18px}

/* La web no tenia ni una excepcion de movimiento reducido. Si se anaden
   transiciones, hay que anadirla. */
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{
    animation-duration:.01ms!important;animation-iteration-count:1!important;
    transition-duration:.01ms!important;scroll-behavior:auto!important
  }
}
""" % (
    MARCA,
    BOTONES_AZULES,
    ",".join(s + ":hover" for s in BOTONES_AZULES.split(",")),
    ",".join(s + ":active" for s in BOTONES_AZULES.split(",")),
    TARJETAS,
    ",".join(s + ":hover" for s in TARJETAS.split(",")),
)


def main():
    ficheros = []
    for base, _, nombres in os.walk(RAIZ):
        for n in nombres:
            if n.endswith(".html"):
                ficheros.append(os.path.join(base, n))
    ficheros.sort()

    con_fuente = con_capa = 0
    for ruta in ficheros:
        with open(ruta, encoding="utf-8") as f:
            html = original = f.read()

        # 1. Enlace de fuentes: se sustituye el de la home, se inyecta en las
        #    landings, que no tenian ninguno.
        if "fonts.googleapis.com/css2" in html:
            html = re.sub(r"https://fonts\.googleapis\.com/css2\?[^\"']+", FUENTES, html)
        elif "Space+Grotesk" not in html:
            m = re.search(r'<meta name="viewport"[^>]*>', html)
            if m:
                html = html[:m.end()] + "\n" + ENLACE_FUENTES + html[m.end():]
                con_fuente += 1

        # 2. Familias y pesos imposibles.
        for viejo, nuevo in FAMILIAS:
            html = html.replace(viejo, nuevo)
        html = html.replace("font-weight:300", "font-weight:400")

        # Ninguna de las dos familias que se cargan llega a 800, asi que las
        # 309 declaraciones a 800 y 900 que habia no daban mas negrita: daban
        # negrita falsificada por el navegador, que engorda el trazo a lo
        # bruto y emborrona los remates. Se topa todo en 700, que es el maximo
        # real. Un titular a 700 de verdad se ve mejor que uno a 900 fingido.
        html = re.sub(r"font-weight:(?:800|900)\b", "font-weight:700", html)

        # 3. Capa premium. Se retira la anterior antes de poner la nueva, para
        #    poder reejecutar el script sin acumular copias.
        html = re.sub(r"\n/\* ===== %s.*?(?=</style>)" % MARCA, "", html, flags=re.S)
        if "</style>" in html:
            html = html.replace("</style>", CAPA + "</style>", 1)
            con_capa += 1

        if html != original:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(html)

    print("ficheros procesados      : %d" % len(ficheros))
    print("landings que ya cargan    : %d (antes iban con fuente del sistema)" % con_fuente)
    print("capa premium anadida a    : %d" % con_capa)


if __name__ == "__main__":
    main()
