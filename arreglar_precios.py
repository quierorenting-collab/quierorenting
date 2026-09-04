# -*- coding: utf-8 -*-
"""Pone al dia los precios escritos a mano de quierorenting.es.

Cada pagina repite su precio en el title, la meta, el og:, dos JSON-LD, el
bloque de precio visible, el texto y los enlaces de WhatsApp. Y ademas lleva
tarjetas de "coches relacionados" con el precio de OTROS coches, algunos ya
retirados. Por eso no vale un reemplazo global: hay que separar lo que es el
precio de la pagina de lo que es el precio de un tercero.
"""
import json, os, re, sys, unicodedata
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
B = "sitio-nuevo"

def sl(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", s.lower()))

ALIAS = {"renting-mercedes-benz-glc-coupe": "renting-mercedes-glc",
         "renting-mercedes-benz-gle-coupe": "renting-mercedes-gle",
         "renting-mercedes-benz-citan": "renting-mercedes-citan"}
PRECIO = {}
for b, m, p in re.findall(r"\{b:'([^']*)',m:'([^']*)'.*?p:(\d+)", open("cars_nuevo.js", encoding="utf-8").read()):
    s = ALIAS.get("renting-" + sl(b) + "-" + sl(m), "renting-" + sl(b) + "-" + sl(m))
    PRECIO[s] = min(PRECIO.get(s, 10**9), int(p))

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
                depth -= 1; j = m.end()
                if depth == 0: break
            else:
                depth += 1; j = m.end()
        out.append((i, j)); i = j

def cambiar(txt, viejo, nuevo):
    """Solo el numero suelto: 289 no debe tocar 2890 ni 1289."""
    return re.sub(r"(?<!\d)%d(?!\d)" % viejo, str(nuevo), txt)

cambiadas = borradas = actualizadas = 0
for d in sorted(os.listdir(B)):
    ruta = os.path.join(B, d, "index.html")
    if not os.path.isfile(ruta): continue
    h = open(ruta, encoding="utf-8").read(); orig = h
    # 1) las tarjetas, de atras hacia delante para no descuadrar los indices
    for ini, fin in reversed(tarjetas(h)):
        card = h[ini:fin]
        enl = re.search(r'href="(?:https://quierorenting\.es)?/(renting-[a-z0-9-]+)/"', card)
        slug = enl.group(1) if enl else None
        if slug in PRECIO:
            viejos = {int(x) for x in re.findall(r"(?<!\d)(\d{3,4})(?=\s*€|%E2%82%AC)", card)}
            nc = card
            for v in viejos: nc = cambiar(nc, v, PRECIO[slug])
            if nc != card: actualizadas += 1
            h = h[:ini] + nc + h[fin:]
        else:
            h = h[:ini] + h[fin:]; borradas += 1
    # 2) el precio propio de la pagina, ya sin tarjetas por medio
    mine = ALIAS.get(d, d)
    if mine in PRECIO:
        t = re.search(r"<title>[^<]*?desde\s*(\d+)\s*€", h)
        if t:
            viejo = int(t.group(1)); nuevo = PRECIO[mine]
            if viejo != nuevo:
                trozos = tarjetas(h); fuera = []; pos = 0
                for ini, fin in trozos:
                    fuera.append(cambiar(h[pos:ini], viejo, nuevo)); fuera.append(h[ini:fin]); pos = fin
                fuera.append(cambiar(h[pos:], viejo, nuevo))
                h = "".join(fuera); cambiadas += 1
    if h != orig:
        open(ruta, "w", encoding="utf-8").write(h)
print(f"paginas con su precio corregido: {cambiadas}")
print(f"tarjetas de coches relacionados actualizadas: {actualizadas}")
print(f"tarjetas de coches retirados borradas: {borradas}")
