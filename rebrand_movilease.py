# -*- coding: utf-8 -*-
"""Aplica la identidad de MoviLease a los 37 HTML de quierorenting.es.

Por que un script y no ediciones a mano: cada pagina lleva su propia copia del
CSS inline —no hay hoja compartida—, asi que un cambio de color toca los 37
ficheros. A mano es garantizar que dos paginas se queden en verde.

    python rebrand_movilease.py

Que hace, en orden:

  1. COLOR. Sustituye la paleta verde por la azul de MoviLease. Conviven dos
     verdes distintos: la home va por variables CSS (--green) y las 36
     landings llevan #18a05a escrito a pelo, 483 veces. Se mapean los dos.
  2. LOGO. Anade el lockup real de MoviLease al pie de las 37 paginas: en
     color sobre los pies claros de las landings, en blanco sobre el pie
     oscuro de la home. El "by MoviLease" del menu ya estaba y se queda como
     texto: a 18 px el lockup completo con su bajada no se leeria.
  3. CIFRAS SIN RESPALDO. Quita "+10.000 clientes", la valoracion 4.9, las
     resenas firmadas y los aggregateRating del JSON-LD. La empresa esta
     empezando y esas cifras no se sostienen; ademas, una resena inventada en
     datos estructurados es motivo de accion manual de Google.
  4. DATOS OBSOLETOS. "+30 marcas" se quedo viejo al podar el catalogo contra
     el Drive. Se sustituye por el recuento real, leido del propio array CARS
     de la pagina, para que no vuelva a desfasarse.

Lo que NO toca, a proposito:

  - El verde de WhatsApp (#25d366 y su hover #25d444). Es color de marca ajena
    y su unico uso son los botones de WhatsApp.
  - Los ambares de las insignias, el morado de la etiqueta PHEV y el cian de
    los degradados: no forman parte de la identidad verde.
  - El reclamo "desde 264 EUR/mes". Es un mensaje comercial establecido y no
    me corresponde cambiarlo, aunque el coche mas barato del catalogo este hoy
    en 263 EUR. Queda avisado en el informe final.
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sitio-nuevo")

# --- 1. COLOR -------------------------------------------------------------
# El rol de cada verde se ha deducido de donde se usa, no del tono: por eso
# #4ade80 (verde claro, siempre sobre fondo oscuro) va al azul claro y no al
# azul de marca. El azul de marca sobre oscuro se queda en 3,1:1 y no pasa AA;
# #5AA0FF llega a 5,6:1. Es la misma regla que rige en movilease.es.
COLORES = {
    "#18a05a": "#0068ff",  # verde principal de las landings -> azul de marca
    "#16a34a": "#0068ff",  # verde principal de la home
    "#15803d": "#0052cc",  # verde oscuro de hover -> azul oscurecido
    "#1ebe5a": "#2e86ff",  # verde vivo de realce
    "#0f4c2a": "#0b2a5e",  # verde muy oscuro -> --dark de MoviLease
    "#2d6a4f": "#16407f",  # verde medio oscuro -> --dark-3
    "#4ade80": "#5aa0ff",  # verde claro SOBRE OSCURO -> --blue-light
    "#dcfce7": "#dceaff",  # tinte claro de fondo
    "#f0fdf4": "#f0f6ff",  # tinte clarisimo de fondo
    "#f0f4f2": "#f1f4f9",  # blanco roto verdoso -> blanco roto azulado
    "#f8faf9": "#f8fafd",  # casi blanco verdoso
    "#0d9488": "#2358b4",  # teal que cerraba el degradado del verde
}
_RE_HEX = re.compile("|".join(re.escape(k) for k in COLORES), re.I)

# Los mismos verdes escritos como rgba(), que el mapa de hex no ve.
RGB_VERDES = {
    (74, 222, 128): (90, 160, 255),
    (22, 163, 74): (0, 104, 255),
    (24, 160, 90): (0, 104, 255),
    (30, 190, 90): (46, 134, 255),
    (15, 76, 42): (11, 42, 94),
    (45, 106, 79): (22, 64, 127),
}


def _rgba(m):
    clave = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if clave not in RGB_VERDES:
        return m.group(0)  # negros, blancos y el verde de WhatsApp se quedan
    r, g, b = RGB_VERDES[clave]
    return "rgba(%d,%d,%d,%s" % (r, g, b, m.group(4))


def recolorea(html):
    html = _RE_HEX.sub(lambda m: COLORES[m.group(0).lower()], html)
    html = re.sub(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,([^)]*)", _rgba, html)
    # Los nombres de variable tambien mienten si se quedan: --green:#0068ff es
    # una trampa para el siguiente que abra el fichero. De mas larga a mas
    # corta, o "--green-d" se convertiria en "--blue-d" a medias.
    for viejo, nuevo in (("--green-xl", "--blue-xl"), ("--green-l", "--blue-l"),
                         ("--green-d", "--blue-d"), ("--green", "--blue")):
        html = html.replace(viejo, nuevo)
    return html


# --- 2. LOGO --------------------------------------------------------------
CSS_LOGO = (
    "\n.footer-ml{display:inline-flex;flex-direction:column;align-items:center;"
    "gap:7px;margin:0 auto 16px;text-decoration:none}"
    "\n.footer-ml span{font-size:10.5px;font-weight:600;letter-spacing:.09em;"
    "text-transform:uppercase;color:#9ca3af}"
    "\n.footer-ml img{display:block;height:34px;width:auto}"
    "\n.footer-ml:hover img{opacity:.85}\n"
)


def bloque_logo(blanco):
    fichero = "movilease-logo-blanco.png" if blanco else "movilease-logo.png"
    # Ruta absoluta desde la raiz, no la URL de quierorenting.es que usan las
    # fotos: asi el logo tambien carga en las vistas previas de Vercel.
    return ('<a class="footer-ml" href="https://movilease.es" target="_blank" '
            'rel="noopener"><span>Una marca de</span>'
            '<img src="/fotos/%s" alt="MoviLease" width="220" height="47" '
            'loading="lazy"></a>' % fichero)


def mete_logo(html, es_home):
    if "footer-ml" in html:
        return html, False  # ya estaba: el script se puede repetir sin duplicar
    if es_home:
        antes = ('<p class="footer-logo">quierorenting<span class="by-ml">by '
                 "<b>MoviLease</b></span></p>")
        despues = ('<p class="footer-logo">quierorenting</p>\n  '
                   + bloque_logo(blanco=True))
    else:
        antes = '<footer class="footer">'
        despues = '<footer class="footer">\n  ' + bloque_logo(blanco=False)
    if antes not in html:
        return html, False
    html = html.replace(antes, despues, 1)
    html = html.replace("</style>", CSS_LOGO + "</style>", 1)
    return html, True


# --- 3. CIFRAS SIN RESPALDO ----------------------------------------------
def limpia_jsonld(html):
    """Quita aggregateRating y review de los bloques de datos estructurados.

    Se parsea y se vuelve a serializar en vez de recortar con expresiones
    regulares porque borrar una clave a base de regex deja comas colgando y un
    JSON-LD invalido es peor que uno con datos de mas: Google lo descarta
    entero, incluido el catalogo de ofertas que si es real.
    """
    quitados = []

    def _rep(m):
        try:
            datos = json.loads(m.group(2))
        except ValueError:
            return m.group(0)
        encontrados = []

        def poda(o):
            if isinstance(o, dict):
                for k in ("aggregateRating", "review"):
                    if k in o:
                        o.pop(k)
                        encontrados.append(k)
                for v in o.values():
                    poda(v)
            elif isinstance(o, list):
                for v in o:
                    poda(v)

        poda(datos)
        if not encontrados:
            return m.group(0)
        quitados.extend(encontrados)
        return m.group(1) + "\n" + json.dumps(datos, ensure_ascii=False, indent=2) + "\n" + m.group(3)

    html = re.sub(r"(<script[^>]*application/ld\+json[^>]*>)(.*?)(</script>)",
                  _rep, html, flags=re.S)
    return html, quitados


def limpia_home(html):
    """Sustituciones que solo existen en la home."""
    hechas = []

    def cambia(antes, despues, etiqueta):
        nonlocal html
        if antes in html:
            html = html.replace(antes, despues)
            hechas.append(etiqueta)

    # Recuento real, leido del propio catalogo, para que no se vuelva a
    # quedar desfasado a mano.
    marcas = re.findall(r"\{b:'([^']+)'", html)
    n_coches, n_marcas = len(marcas), len(set(marcas))

    cambia("+10.000 clientes en toda España. ", "Disponibilidad real en toda España. ", "meta description")
    cambia("Sin entrada. +10.000 clientes. Gestión", "Sin entrada. Gestión", "og:description")
    cambia("Sin entrada, todo incluido. +10.000 clientes satisfechos.",
           "Sin entrada, todo incluido. Gestión en 48 h.", "twitter:description")
    cambia(" · +10.000 clientes satisfechos", " · Gestión en 48 h", "texto del pie")

    # La prueba social del hero eran cinco iniciales, cinco estrellas y la
    # cifra de clientes: las tres cosas dependen de la misma afirmacion.
    nuevo_hero = ("<span>Seguro a todo riesgo, mantenimiento e impuestos "
                  "incluidos en la cuota</span>")
    html2 = re.sub(r'<div class="hero-faces">.*?<span>\+10\.000 clientes felices con su renting</span>',
                   nuevo_hero, html, flags=re.S)
    if html2 != html:
        html, _ = html2, hechas.append("prueba social del hero")

    # Las cifras que se van no se sustituyen por el tamano del catalogo: 29
    # modelos es un dato veraz pero que juega en contra, porque lo que vende
    # aqui es lo que entra en la cuota, no cuantos coches hay en la lista. Se
    # sustituyen por ventajas del servicio, todas comprobables en la propia
    # pagina y ninguna dependiente de cuantos clientes haya.
    cambia('<div class="stat"><span class="stat-number">+10.000</span><span class="stat-label">Clientes</span></div>',
           '<div class="stat"><span class="stat-number">24 h</span><span class="stat-label">Asistencia en carretera</span></div>',
           "estadistica de clientes")
    cambia('<div class="stat"><span class="stat-number">4.9 ★</span><span class="stat-label">Valoración</span></div>',
           '<div class="stat"><span class="stat-number">100%</span><span class="stat-label">Gestión online</span></div>',
           "estadistica de valoracion")
    cambia('<div class="stat"><span class="stat-number">+30</span><span class="stat-label">Marcas</span></div>',
           '<div class="stat"><span class="stat-number">Todo</span><span class="stat-label">Incluido</span></div>',
           "estadistica de marcas")
    cambia("+30 marcas disponibles", "Asistencia 24 h incluida", "barra de confianza")

    cambia('<p class="why-title">+10.000 clientes</p><p class="why-text">Somos una de las empresas de renting para particulares con mejor valoración de España. 4.9⭐</p>',
           '<p class="why-title">Para particulares</p><p class="why-text">No hace falta ser empresa ni autónomo. El renting también es para particulares, y es lo que llevamos haciendo desde el principio.</p>',
           "tarjeta de por que")

    # Seccion entera de testimonios: cinco resenas firmadas con nombre,
    # ciudad y coche, una de ellas de un cliente "de hace 3 anos".
    html2 = re.sub(r'\n<section class="testi-section">.*?\n</section>', "", html, flags=re.S)
    if html2 != html:
        html, _ = html2, hechas.append("seccion de testimonios")

    return html, hechas, n_coches, n_marcas


# --- ejecucion ------------------------------------------------------------
def main():
    ficheros = []
    for base, _, nombres in os.walk(RAIZ):
        for n in nombres:
            if n.endswith(".html"):
                ficheros.append(os.path.join(base, n))
    ficheros.sort()

    total_logo = 0
    jsonld_quitados = []
    resumen_home = []
    n_coches = n_marcas = 0

    for ruta in ficheros:
        with open(ruta, encoding="utf-8") as f:
            html = original = f.read()
        es_home = os.path.dirname(ruta) == RAIZ

        html = recolorea(html)
        html, quitados = limpia_jsonld(html)
        jsonld_quitados.extend(quitados)
        if es_home:
            html, resumen_home, n_coches, n_marcas = limpia_home(html)
        html, puesto = mete_logo(html, es_home)
        total_logo += 1 if puesto else 0

        if html != original:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(html)

    print("ficheros procesados : %d" % len(ficheros))
    print("logo anadido al pie : %d" % total_logo)
    print("JSON-LD podado      : %s" % (", ".join(sorted(set(jsonld_quitados))) or "nada"))
    print("catalogo real       : %d modelos, %d marcas" % (n_coches, n_marcas))
    print("cambios en la home  :")
    for h in resumen_home:
        print("   - %s" % h)


if __name__ == "__main__":
    main()
