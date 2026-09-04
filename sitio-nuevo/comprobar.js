#!/usr/bin/env node
/**
 * Comprobador de quierorenting.es.  SOLO LEE, no toca ningun fichero.
 *
 *     node comprobar.js
 *
 * Existe porque esta web son 37 ficheros HTML sueltos, mantenidos a mano, sin
 * build y sin linter. Nada avisa cuando algo se desvia, y cuando se reviso a
 * fondo aparecio esto:
 *
 *  - 89 enlaces de WhatsApp con un precio dentro del mensaje, y de los 67 que
 *    nombraban un solo coche, NINGUNO coincidia con el catalogo de la home.
 *  - 19 fichas de modelo sin <h1>, justo las paginas que venden.
 *  - Un <div style="display:none"> con 19 enlaces solo para Google.
 *  - La clave de Web3Forms y el token del bot de Telegram en el HTML publico.
 *  - Un error de comillas que rompia el <script> del banner de cookies entero.
 *
 * Todo eso llevaba meses publicado sin que nada chillara. Este fichero chilla.
 *
 * La fuente de verdad del precio es el array CARS de index.html. Si un precio
 * aparece en cualquier otro sitio, tiene que coincidir con el.
 */
"use strict";

const fs = require("fs");
const path = require("path");

const BASE = __dirname;
const problemas = [];
const avisos = [];

function fallo(donde, texto) { problemas.push({ donde, texto }); }
function aviso(donde, texto) { avisos.push({ donde, texto }); }

// ---------------------------------------------------------------- paginas
const paginas = ["index.html"].concat(
  fs.readdirSync(BASE, { withFileTypes: true })
    .filter((d) => d.isDirectory() && fs.existsSync(path.join(BASE, d.name, "index.html")))
    .map((d) => path.join(d.name, "index.html"))
);
const carpetas = new Set(
  fs.readdirSync(BASE, { withFileTypes: true }).filter((d) => d.isDirectory()).map((d) => d.name)
);

// -------------------------------------------------------------- catalogo
const home = fs.readFileSync(path.join(BASE, "index.html"), "utf8");
const bruto = home.match(/const\s+CARS\s*=\s*(\[[\s\S]*?\]);/);
if (!bruto) {
  console.error("No encuentro el array CARS en index.html. Sin el no se puede comprobar nada.");
  process.exit(2);
}
const CARS = eval(bruto[1]);
const precioDe = new Map(CARS.map((c) => [(c.b + " " + c.m).toLowerCase(), c.p]));
const precioMinimo = Math.min(...CARS.map((c) => c.p).filter((p) => p > 0));

/** Busca en un texto el nombre de UN solo coche del catalogo. */
function cocheMencionado(texto) {
  const t = texto.toLowerCase();
  const hits = [...precioDe.entries()].filter(([nombre]) => t.includes(nombre));
  return hits.length === 1 ? hits[0] : null;
}

/** "1.407" -> 1407 */
const aNumero = (s) => Number(String(s).replace(/\./g, ""));

// ------------------------------------------------------------ los cheques
const h1Vistos = new Map();

for (const rel of paginas) {
  const t = fs.readFileSync(path.join(BASE, rel), "utf8");
  const soloHtml = t
    .replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<!--[\s\S]*?-->/g, "");

  // 1. Credenciales. Lo mas caro de todo lo que aparecio.
  if (/[0-9]{8,10}:AA[A-Za-z0-9_-]{30,}/.test(t)) fallo(rel, "hay un token de Telegram en el HTML");
  for (const p of ["api.telegram.org", "api.web3forms.com", "W3F_KEY", "TG_TOKEN", "access_key"]) {
    if (t.includes(p)) fallo(rel, `el navegador vuelve a hablar con un servicio directamente: "${p}"`);
  }

  // 2. Enlaces ocultos. Google lo llama texto oculto y lo sanciona.
  if (/<div[^>]*style="[^"]*display:\s*none[^"]*"[^>]*>[\s\S]{0,4000}?<a\s/i.test(soloHtml)) {
    aviso(rel, "hay un contenedor oculto con enlaces dentro");
  }

  // 3. Un unico <h1>, y distinto en cada pagina.
  const h1 = [...soloHtml.matchAll(/<h1[^>]*>([\s\S]*?)<\/h1>/gi)].map((m) =>
    m[1].replace(/<[^>]*>/g, "").trim());
  if (h1.length === 0) fallo(rel, "no tiene <h1>");
  else if (h1.length > 1) fallo(rel, `tiene ${h1.length} <h1>, debe haber uno`);
  else {
    const previo = h1Vistos.get(h1[0]);
    if (previo) fallo(rel, `su <h1> es idéntico al de ${previo}: "${h1[0].slice(0, 60)}"`);
    else h1Vistos.set(h1[0], rel);
  }

  // 4. Etiquetas de bloque equilibradas. Un </div> de menos descoloca la pagina
  //    entera y aqui no hay build que lo detecte.
  for (const e of ["div", "nav", "section", "footer", "ul", "li"]) {
    const abre = (soloHtml.match(new RegExp("<" + e + "(?=[\\s>/])", "gi")) || []).length;
    const cierra = (soloHtml.match(new RegExp("</" + e + "\\s*>", "gi")) || []).length;
    if (abre !== cierra) fallo(rel, `<${e}> descuadrado: ${abre} abren, ${cierra} cierran`);
  }

  // 5. Los <script> parsean. Un error de sintaxis mata el bloque ENTERO en
  //    silencio: asi es como el banner de cookies llevaba meses sin salir.
  //    OJO: los bloques de datos estructurados llevan JSON, no JavaScript, y
  //    hay que validarlos como JSON o todo sale marcado como roto.
  [...t.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/gi)].forEach((m, i) => {
    const attrs = m[1] || "";
    if (/\bsrc=/.test(attrs)) return;                       // externo, no hay cuerpo
    const tipo = (attrs.match(/type=["']([^"']+)["']/) || [])[1] || "";
    if (/ld\+json|application\/json/i.test(tipo)) {
      try { JSON.parse(m[2]); }
      catch (e) { fallo(rel, `los datos estructurados nº${i + 1} no son JSON válido: ${e.message}`); }
      return;
    }
    if (tipo && !/javascript|module/i.test(tipo)) return;    // plantilla u otra cosa
    try { new Function(m[2]); }
    catch (e) { fallo(rel, `el <script> nº${i + 1} no parsea: ${e.message}`); }
  });

  // 6. Precios. Ningun sitio puede decir una cifra distinta a la del catalogo.
  const sitios = [
    ["<title>", (t.match(/<title>([^<]*)</) || [])[1] || ""],
    ["la meta description", (t.match(/name="description" content="([^"]*)"/) || [])[1] || ""],
  ];
  [...t.matchAll(/wa\.me\/[^"']+/g)].forEach((m) => {
    let d; try { d = decodeURIComponent(m[0]); } catch (e) { return; }
    sitios.push(["un enlace de WhatsApp", d]);
  });

  for (const [donde, texto] of sitios) {
    const pm = texto.match(/desde\s+([\d.]+)\s*€/);
    if (!pm) continue;
    const cifra = aNumero(pm[1]);
    const coche = cocheMencionado(texto);
    if (coche) {
      if (coche[1] !== cifra) {
        fallo(rel, `${donde} dice ${pm[1]} € para el ${coche[0]}, y el catálogo dice ${coche[1]} €`);
      }
      continue;
    }
    // Una página de categoría o de ciudad no nombra un coche: su "desde X €"
    // es el más barato del catálogo. Si es MENOR que el más barato que hay,
    // se está anunciando un precio que no existe en ninguna parte.
    if (cifra < precioMinimo) {
      fallo(rel, `${donde} anuncia "desde ${pm[1]} €" y el coche más barato del catálogo está en ${precioMinimo} €`);
    }
  }

  // 7. Los enlaces internos llevan a algun sitio.
  [...soloHtml.matchAll(/href="\/([a-z0-9-]+)\/"/g)].forEach((m) => {
    if (!carpetas.has(m[1])) fallo(rel, `enlaza a /${m[1]}/ y esa carpeta no existe`);
  });

  // 8. Promesas que no se pueden sostener.
  if (/no se comparten con terceros/i.test(soloHtml)) {
    fallo(rel, 'dice "no se comparten con terceros", y el aviso del lead sale hacia Web3Forms y Telegram');
  }
}

// 9. El formulario exige aceptar una politica que tiene que existir.
for (const ruta of ["politica-de-privacidad", "politica-de-cookies", "aviso-legal"]) {
  const citada = paginas.some((p) =>
    fs.readFileSync(path.join(BASE, p), "utf8").includes(`/${ruta}/`));
  if (citada && !carpetas.has(ruta)) {
    fallo("todo el sitio", `se enlaza /${ruta}/ y la página no existe: da 404`);
  }
}

// ------------------------------------------------------------------ salida
const linea = (x) => `  ${x.donde}\n      ${x.texto}`;
if (problemas.length) {
  console.log(`\nFALLOS (${problemas.length}):\n`);
  problemas.forEach((p) => console.log(linea(p)));
}
if (avisos.length) {
  console.log(`\nPARA MIRAR (${avisos.length}):\n`);
  avisos.forEach((a) => console.log(linea(a)));
}
if (!problemas.length && !avisos.length) {
  console.log(`\n  ${paginas.length} páginas y ${CARS.length} coches comprobados. Todo cuadra.\n`);
} else {
  console.log(`\n  ${paginas.length} páginas, ${CARS.length} coches.\n`);
}
process.exit(problemas.length ? 1 : 0);
