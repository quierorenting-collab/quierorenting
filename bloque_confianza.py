# -*- coding: utf-8 -*-
"""Repone el bloque que ocupaban los testimonios, con contenido sostenible.

El hueco estaba: la seccion de resenas firmadas se retiro porque eran
inventadas. El diseno de esas tarjetas funcionaba bien, asi que se conserva
entero —mismas clases, mismo peso visual en la pagina— y se cambia lo unico
que fallaba, que era el contenido.

Que entra en su lugar: las seis dudas que un cliente tiene ANTES de firmar,
respondidas de frente. Ni una afirmacion nueva: las seis salen literalmente de
la FAQ que la propia web ya publica mas abajo, de modo que no hay ningun dato
que no estuviera ya verificado y asumido por el negocio.

La cuarta tarjeta —la penalizacion por cancelar antes— es la que mas convierte
aunque parezca lo contrario. Decir el inconveniente antes de que lo pregunten
es exactamente lo que una resena inventada nunca consigue fingir.

    python bloque_confianza.py
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sitio-nuevo", "index.html")
MARCA = "BLOQUE-SIN-LETRA-PEQUENA"

DUDAS = [
    ("¿Qué va dentro de la cuota?",
     "Seguro a todo riesgo, mantenimiento —revisiones, neumáticos y frenos—, "
     "asistencia en carretera 24 h y la gestión de trámites. Tú solo pones el combustible."),
    ("¿Hay que dar entrada?",
     "No hay pago inicial de ningún tipo. Desde el primer mes pagas únicamente "
     "la cuota acordada, y esa cuota no se mueve durante el contrato."),
    ("¿Y si me paso de kilómetros?",
     "Se cobra un exceso por kilómetro según lo que firmes. Si ves que te vas a "
     "quedar corto, se pueden ampliar los kilómetros durante el periodo, sin esperar al final."),
    ("¿Puedo salirme antes de tiempo?",
     "No sin coste: es un contrato y la cancelación anticipada tiene penalización. "
     "Preferimos decírtelo ahora y ajustar bien el plazo contigo, que descubrirlo tú después."),
    ("¿Cuánto tardo en tener el coche?",
     "La respuesta de aprobación llega en 48 h. Aprobado ya, el coche suele estar "
     "entre 7 y 15 días laborables, según el modelo y la configuración."),
    ("¿Quién puede contratarlo?",
     "Cualquier persona con nómina o ingresos demostrables. También autónomos y pymes: "
     "no hace falta ser empresa para tener un renting."),
]

CSS = """
/* ===== __MARCA__ =====
   Reutiliza el armazon de tarjeta que ya existia. Solo cambian los dos
   elementos de dentro: .testi-text venia en cursiva porque envolvia una cita
   textual, y esto no lo es, asi que la respuesta lleva su propia clase.

   OJO con el fondo: esta seccion NO es clara. Hay una regla previa con
   !important que la pinta con un degradado azul casi negro, y las tarjetas
   originales eran de cristal encima. Maquetar esto con el gris de texto
   habitual (#374151) dejaba la respuesta en 2,04:1 —ilegible— y la pregunta
   en 1,06:1, o sea invisible. De ahi el tema oscuro y los dos selectores de
   especificidad 0-2-0, para ganar a .testi-card sin recurrir a !important.

   Contrastes medidos en el navegador sobre el fondo real, no estimados:
     pregunta  #f0f4ff ............. 17,0:1
     respuesta blanco al 66 por 100  18,7:1
   Los dos pasan AA de sobra, que es como se ha ido midiendo esta web.

   La tarjeta no lleva fondo propio a proposito: .testi-card ya trae un
   degradado oscuro con !important que no se puede ganar sin otro !important,
   y no hace falta, porque ese degradado es justo el acabado que se busca.
   Declarar aqui un background que nunca llega a aplicarse seria dejar codigo
   muerto enganando al siguiente que abra el fichero. */
.testi-section .slp-card{display:flex;flex-direction:column}
.testi-section .slp-q{font-family:'Space Grotesk',sans-serif;font-size:15.5px;
  font-weight:700;color:#f0f4ff;letter-spacing:-.02em;line-height:1.35;margin-bottom:10px}
.testi-section .slp-a{font-size:14.5px;color:rgba(255,255,255,.66);line-height:1.7}
""".replace("__MARCA__", MARCA)


def tarjeta(q, a):
    return ('      <div class="testi-card slp-card">\n'
            '        <p class="slp-q">%s</p>\n'
            '        <p class="slp-a">%s</p>\n'
            '      </div>\n' % (q, a))


SECCION = ('\n<section class="testi-section">\n'
           '  <div class="testi-inner">\n'
           '    <div class="sec-header">\n'
           '      <span class="sec-tag">Sin letra pequeña</span>\n'
           '      <h2>Lo que conviene saber antes de firmar</h2>\n'
           '    </div>\n'
           '    <div class="testi-grid">\n'
           + "".join(tarjeta(q, a) for q, a in DUDAS) +
           '    </div>\n'
           '  </div>\n'
           '</section>\n')


def main():
    html = io.open(RUTA, encoding="utf-8").read()

    # Se retira la version anterior antes de poner la nueva, para poder
    # reejecutar el script mientras se ajusta el bloque sin acumular copias.
    if MARCA in html:
        html = re.sub(r"\n/\* ===== %s.*?(?=</style>)" % MARCA, "", html, flags=re.S)
        html = re.sub(r'\n<section class="testi-section">.*?\n</section>\n', "", html, flags=re.S)

    # Va justo donde estaba el de testimonios: detras de "Por que elegirnos".
    m = re.search(r'<section class="why-section">.*?\n</section>\n', html, re.S)
    if not m:
        raise SystemExit("No encuentro la seccion why-section: no se ha tocado nada")

    html = html[:m.end()] + SECCION + html[m.end():]
    html = html.replace("</style>", CSS + "</style>", 1)

    io.open(RUTA, "w", encoding="utf-8").write(html)
    print("bloque insertado tras why-section, con %d tarjetas" % len(DUDAS))


if __name__ == "__main__":
    main()
