# -*- coding: utf-8 -*-
"""Pone al dia los precios escritos a mano de quierorenting.es.

Cada pagina repite su precio en el title, la meta, el og:, dos JSON-LD, el
bloque de precio visible, el texto y los enlaces de WhatsApp. Y ademas lleva
tarjetas de "coches relacionados" con el precio de OTROS coches, algunos ya
retirados. Por eso no vale un reemplazo global: hay que separar lo que es el
precio de la pagina de lo que es el precio de un tercero.

La fuente de verdad es el array CARS de sitio-nuevo/index.html, lo mismo que
usa comprobar.js. Si un modelo tiene varias versiones, manda la mas barata.

Por defecto va EN SECO: dice que cambiaria y no escribe nada. Para escribir,
    python arreglar_precios.py --aplicar

Tres trampas que ya han costado caro:

  - Los precios de mas de 999 EUR se escriben con punto de miles en el texto
    ("1.407€") y sin punto en el JSON-LD ("price": "1407"). La version
    anterior leia cifras de tres o cuatro digitos sueltas: en una tarjeta con
    "1.407€" cogia el "407" de detras del punto y lo habria convertido en
    "1.1407€", y el title "desde 1.366€" ni lo reconocia, asi que las cuatro
    paginas de mas de 999 EUR (GLE, GLE 350d, GLC y Grecale) no se habrian
    actualizado nunca. Aqui una cifra se lee entera, con o sin punto, y se
    escribe con punto en el texto visible y sin punto en el JSON-LD.
  - Solo se toca un numero cuando va en contexto de precio: pegado a EUR (o a
    su forma codificada en una URL de WhatsApp), a "/mes", detras de "desde",
    o como valor de "price"/"lowPrice"/"highPrice". Un 299 de "299 CV" no es
    un precio, y la version anterior lo habria cambiado si coincidia.
  - La tarjeta de un coche que no esta en CARS se BORRA: es como se quitan los
    retirados. Por eso ALIAS tiene que cubrir todas las paginas cuyo nombre no
    coincide con el de CARS, o se borrarian tarjetas de coches a la venta. En
    seco se listan los coches cuyas tarjetas se borrarian: miralo antes.
"""
import os
import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
B = "sitio-nuevo"


def sl(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", s.lower()))


# slug que saldria de CARS -> nombre real de la carpeta de la pagina
ALIAS = {"renting-mercedes-benz-glc-coupe": "renting-mercedes-glc",
         "renting-mercedes-benz-gle-coupe": "renting-mercedes-gle",
         "renting-mercedes-benz-citan": "renting-mercedes-citan",
         "renting-mercedes-benz-gla": "renting-mercedes-gla",
         "renting-mercedes-benz-gle-350d-coupe": "renting-mercedes-gle-350d"}

PRECIO = {}
for b, m, p in re.findall(r"\{b:'([^']*)',m:'([^']*)'.*?p:(\d+)", open(os.path.join(B, "index.html"), encoding="utf-8").read()):
    s = ALIAS.get("renting-" + sl(b) + "-" + sl(m), "renting-" + sl(b) + "-" + sl(m))
    PRECIO[s] = min(PRECIO.get(s, 10**9), int(p))

NUM = r"(\d{1,2}\.\d{3}|\d{3,4})"
# Sin digito ni punto pegado delante... salvo que ese digito sea el final de un
# espacio codificado en URL: en los enlaces de WhatsApp el precio va detras de
# "%20" y el "0" de "%20" dejaba fuera todos los precios de los mensajes.
LIBRE = r"(?:(?<=%20)|(?<=%2C)|(?<=%A0)|(?<![\d.]))"
FIN = r"(?![\d.])"
# Texto visible: la cifra pegada a EUR, a EUR codificado en URL, a "/mes" o "euros".
VISIBLE = re.compile(LIBRE + NUM + FIN + r"(\s*(?:€|%E2%82%AC|&euro;|/mes|euros?))")
# "desde 359" aunque el simbolo vaya luego o no vaya.
DESDE = re.compile(r"(desde\s*)" + NUM + FIN, re.IGNORECASE)
# JSON-LD: "price": "1407"
JSONLD = re.compile(r'("(?:price|lowPrice|highPrice)"\s*:\s*"?)' + r"(\d{1,2}\.?\d{3}|\d{3,4})" + FIN)


def valor(txt):
    return int(txt.replace(".", ""))


def visible(n):
    return "{:,}".format(n).replace(",", ".") if n >= 1000 else str(n)


def reemplazar(txt, viejo, nuevo):
    """Cambia viejo por nuevo solo donde es un precio. Devuelve (texto, cuantos)."""
    cuenta = [0]

    def vis(mt):
        if valor(mt.group(1)) != viejo:
            return mt.group(0)
        cuenta[0] += 1
        return visible(nuevo) + mt.group(2)

    def des(mt):
        if valor(mt.group(2)) != viejo:
            return mt.group(0)
        cuenta[0] += 1
        return mt.group(1) + visible(nuevo)

    def jld(mt):
        if valor(mt.group(2)) != viejo:
            return mt.group(0)
        cuenta[0] += 1
        return mt.group(1) + str(nuevo)

    txt = VISIBLE.sub(vis, txt)
    txt = DESDE.sub(des, txt)
    txt = JSONLD.sub(jld, txt)
    return txt, cuenta[0]


def tarjetas(h):
    """Rangos [inicio,fin) de cada <div class="card">, casando las etiquetas."""
    out, i = [], 0
    pat = re.compile(r"<div\b|</div>")
    while True:
        i = h.find('<div class="card">', i)
        if i < 0:
            return out
        depth, j = 0, i
        while True:
            m = pat.search(h, j)
            if not m:
                return out
            if m.group(0) == "</div>":
                depth -= 1
                j = m.end()
                if depth == 0:
                    break
            else:
                depth += 1
                j = m.end()
        out.append((i, j))
        i = j


SECO = "--aplicar" not in sys.argv
tocadas, borradas_de = [], {}
cambiadas = borradas = actualizadas = 0
for d in sorted(os.listdir(B)):
    ruta = os.path.join(B, d, "index.html")
    if not os.path.isfile(ruta):
        continue
    h = open(ruta, encoding="utf-8").read()
    orig = h
    # 1) las tarjetas, de atras hacia delante para no descuadrar los indices
    for ini, fin in reversed(tarjetas(h)):
        card = h[ini:fin]
        enl = re.search(r'href="(?:https://quierorenting\.es)?/(renting-[a-z0-9-]+)/"', card)
        slug = enl.group(1) if enl else None
        if slug in PRECIO:
            nc = card
            for mt in VISIBLE.finditer(card):
                v = valor(mt.group(1))
                if v != PRECIO[slug]:
                    nc, _ = reemplazar(nc, v, PRECIO[slug])
            if nc != card:
                actualizadas += 1
            h = h[:ini] + nc + h[fin:]
        else:
            h = h[:ini] + h[fin:]
            borradas += 1
            borradas_de.setdefault(slug, []).append(d)
    # 2) el precio propio de la pagina, ya sin tarjetas por medio
    mine = ALIAS.get(d, d)
    if mine in PRECIO:
        t = re.search(r"<title>[^<]*?desde\s*" + NUM + FIN, h, re.IGNORECASE)
        if t:
            viejo = valor(t.group(1))
            nuevo = PRECIO[mine]
            if viejo != nuevo:
                trozos = tarjetas(h)
                fuera, pos, n = [], 0, 0
                for ini, fin in trozos:
                    parte, k = reemplazar(h[pos:ini], viejo, nuevo)
                    fuera.append(parte)
                    fuera.append(h[ini:fin])
                    pos, n = fin, n + k
                parte, k = reemplazar(h[pos:], viejo, nuevo)
                fuera.append(parte)
                h = "".join(fuera)
                cambiadas += 1
                print("  %s: %s -> %s (%d sitios)" % (d, visible(viejo), visible(nuevo), n + k))
    if h != orig:
        tocadas.append(d)
        if not SECO:
            open(ruta, "w", encoding="utf-8").write(h)

print(f"paginas con su precio corregido: {cambiadas}")
print(f"tarjetas de coches relacionados actualizadas: {actualizadas}")
print(f"tarjetas de coches retirados borradas: {borradas}")
for s, ps in sorted(borradas_de.items(), key=lambda x: str(x[0])):
    print(f"  tarjetas de {s} borradas en {len(ps)} paginas")
print(("EN SECO, no se ha escrito nada. " if SECO else "") + f"paginas que cambian ({len(tocadas)}): {tocadas}")
