/**
 * Recepción de leads de quierorenting.es — lado servidor.
 *
 * POR QUÉ EXISTE ESTE FICHERO
 * Hasta ahora el popup enviaba el lead desde el navegador, y para poder hacerlo
 * llevaba dentro del HTML la clave de Web3Forms y el token del bot de Telegram.
 * Cualquiera que abriese el código fuente los leía.
 *
 * Con ese token NO se podía leer el historial de leads: los avisos son mensajes
 * SALIENTES del bot y `getUpdates` solo devuelve los entrantes. Conviene dejarlo
 * escrito porque es el error que se comete al valorar esta fuga. Lo que sí
 * permitía, y sobra para tomárselo en serio, es escribir en el chat de avisos
 * haciéndose pasar por el sistema —leads falsos, enlaces de phishing— y borrar o
 * editar con `deleteMessage`/`editMessageText` los leads legítimos ya entregados.
 * Aquí las claves viven en variables de entorno y no salen nunca del servidor.
 *
 * Además arregla dos cosas que venían de serie:
 *  - El aviso a Telegram se mandaba con los datos del cliente EN LA URL
 *    (?text=Nombre...Telefono...). Una URL queda en registros, en proxies y en
 *    el historial; los datos personales van en el cuerpo de la petición. Aquí se
 *    manda por POST con el cuerpo en JSON.
 *  - El popup enseñaba "recibido" a los 550 ms pasara lo que pasara, con los
 *    errores tragados en un catch vacío. Si el envío fallaba, el cliente se iba
 *    convencido de que le iban a llamar y el lead no existía en ninguna parte.
 *    Aquí la respuesta dice la verdad y el popup se comporta en consecuencia.
 *
 * Se despliega como función serverless de Vercel: al haber una carpeta /api en
 * la raíz del proyecto estático, Vercel la publica en /api/lead sin necesidad de
 * build. Formato CommonJS a propósito: no hay package.json en este proyecto, así
 * que un `export default` no se interpretaría como módulo.
 */

/** Orígenes desde los que se acepta un envío. */
const ORIGENES = [
  "https://quierorenting.es",
  "https://www.quierorenting.es",
];

/** Un despliegue de vista previa de este mismo proyecto también vale. */
const ORIGEN_PREVIA = /^https:\/\/quiero-renting-[a-z0-9-]+\.vercel\.app$/;

/**
 * Límite por IP: 5 envíos cada 10 minutos.
 *
 * Vive en memoria del proceso, así que se pierde cuando Vercel recicla la
 * instancia y no se comparte entre instancias. No es un límite fuerte y no
 * pretende serlo: sirve para cortar la ráfaga de un script, que es el caso real,
 * y cuesta cero. Un límite de verdad necesitaría almacenamiento compartido, que
 * hoy este proyecto no tiene.
 */
const VENTANA_MS = 10 * 60 * 1000;
const MAX_POR_VENTANA = 5;
const visitas = new Map();

function demasiadosEnvios(ip) {
  const ahora = Date.now();
  const previas = (visitas.get(ip) || []).filter((t) => ahora - t < VENTANA_MS);
  previas.push(ahora);
  visitas.set(ip, previas);

  // Poda: sin esto el Map crece sin límite mientras viva la instancia.
  if (visitas.size > 500) {
    for (const [clave, marcas] of visitas) {
      if (!marcas.some((t) => ahora - t < VENTANA_MS)) visitas.delete(clave);
    }
  }
  return previas.length > MAX_POR_VENTANA;
}

/** Recorta y limita la longitud. Todo lo que entra del exterior pasa por aquí. */
function texto(valor, max) {
  if (typeof valor !== "string") return "";
  return valor.trim().slice(0, max);
}

/**
 * Teléfono español. Mismo criterio que movilease.es (`leadFormSchema`) para que
 * un número aceptado en una web no sea rechazado en la otra.
 */
const TELEFONO = /^[+\d][\d\s.-]{6,20}$/;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function leerCuerpo(req) {
  // Vercel ya deja el JSON parseado en req.body cuando el content-type lo indica,
  // pero no en todos los casos; si no está, se lee el flujo a mano.
  if (req.body && typeof req.body === "object") return Promise.resolve(req.body);
  return new Promise((resolve) => {
    let bruto = "";
    req.on("data", (trozo) => {
      bruto += trozo;
      if (bruto.length > 20000) req.destroy(); // cuerpo desproporcionado: se corta
    });
    req.on("end", () => {
      try {
        resolve(JSON.parse(bruto || "{}"));
      } catch {
        resolve(null);
      }
    });
    req.on("error", () => resolve(null));
  });
}

async function avisarPorCorreo(clave, lead) {
  const r = await fetch("https://api.web3forms.com/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      access_key: clave,
      subject: (lead.sospechoso ? "[REVISAR] " : "") + "Nuevo lead QuieroRenting — " + lead.nombre,
      from_name: "QuieroRenting Web",
      reply_to: lead.email || "sin-email@quierorenting.es",
      Nombre: lead.nombre,
      "Teléfono": lead.telefono,
      Email: lead.email || "(no indicado)",
      Coche: lead.coche || "(no indicado)",
      Fecha: lead.fecha,
      "Página": lead.pagina,
      Origen: "quierorenting.es",
      // Prueba del consentimiento. El RGPD no pide solo recogerlo: pide poder
      // demostrar después que se recogió (art. 7.1). Si solo vive en una casilla
      // marcada en un navegador que ya se cerró, no hay nada que enseñar.
      Consentimiento: "Aceptada la política de privacidad el " + lead.fecha,
    }),
  });
  if (!r.ok) throw new Error("web3forms " + r.status);
  return true;
}

async function avisarPorTelegram(token, chatId, lead) {
  // POST con cuerpo, no GET con los datos en la URL.
  const r = await fetch("https://api.telegram.org/bot" + token + "/sendMessage", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text:
        (lead.sospechoso ? "[REVISAR - posible bot]\n" : "") +
        "Nuevo cliente — QuieroRenting\n" +
        "Nombre: " + lead.nombre + "\n" +
        "Teléfono: " + lead.telefono + "\n" +
        "Email: " + (lead.email || "No indicado") + "\n" +
        (lead.coche ? "Coche: " + lead.coche + "\n" : "") +
        "Fecha: " + lead.fecha + "\n" +
        "Página: " + lead.pagina + "\n" +
        "Consentimiento: aceptado",
      disable_web_page_preview: true,
    }),
  });
  if (!r.ok) throw new Error("telegram " + r.status);
  return true;
}

/**
 * Vuelca el lead en HubSpot: contacto y negociacion asociada.
 *
 * Este formulario solo pide nombre y telefono —el email es opcional— y HubSpot
 * deduplica contactos por email. Sin buscar antes, la misma persona que
 * pregunta dos veces aparece dos veces. Por eso se busca primero por email y
 * por telefono. La busqueda por telefono compara la cadena tal cual, asi que un
 * numero escrito con y sin prefijo no casa; aun asi quita la mayoria.
 *
 * La etapa del embudo no se codifica: si no vienen HUBSPOT_PIPELINE_ID y
 * HUBSPOT_DEALSTAGE_ID se pregunta a HubSpot por su embudo por defecto y se usa
 * su primera etapa. Asi funciona sin tener que copiar identificadores a mano.
 *
 * Como los demas avisos, esto NO puede tumbar la respuesta al cliente: se llama
 * dentro del Promise.allSettled y cualquier fallo se queda en el registro.
 */
var etapaHubSpot = null;   // el embudo se pregunta una vez por proceso

async function hsLlamar(token, ruta, metodo, cuerpo) {
  var r = await fetch("https://api.hubapi.com" + ruta, {
    method: metodo,
    headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
    signal: AbortSignal.timeout(8000),
  });
  if (!r.ok) {
    var detalle = await r.text().catch(function () { return ""; });
    throw new Error("hubspot " + metodo + " " + ruta + " " + r.status + " " + detalle.slice(0, 300));
  }
  return r.json().catch(function () { return {}; });
}

async function hsEtapa(token) {
  if (process.env.HUBSPOT_PIPELINE_ID && process.env.HUBSPOT_DEALSTAGE_ID) {
    return { pipeline: process.env.HUBSPOT_PIPELINE_ID, dealstage: process.env.HUBSPOT_DEALSTAGE_ID };
  }
  if (etapaHubSpot) return etapaHubSpot;
  var datos = await hsLlamar(token, "/crm/v3/pipelines/deals", "GET");
  var embudo = (datos.results || [])[0];
  if (!embudo || !embudo.stages || embudo.stages.length === 0) return null;
  var etapas = embudo.stages.slice().sort(function (a, b) {
    return (a.displayOrder || 0) - (b.displayOrder || 0);
  });
  etapaHubSpot = { pipeline: embudo.id, dealstage: etapas[0].id };
  return etapaHubSpot;
}

/**
 * Las formas en que puede estar guardado un mismo telefono en HubSpot.
 *
 * Su busqueda compara la cadena tal cual, y la gente escribe el numero como le
 * parece: "654371940", "+34677664324", "610 55 42 76". Sin esto, la misma
 * persona que vuelve a preguntar entra como contacto nuevo, que es justo lo que
 * hay que evitar.
 */
function hsVariantesTelefono(telefono) {
  var limpio = String(telefono).replace(/[\s.()-]/g, "");
  var digitos = limpio.replace(/\D/g, "");
  var nueve = digitos.slice(-9);
  var salida = [telefono, limpio, digitos, nueve];
  // El +34 solo se da por hecho con nueve digitos, que es el numero espanol.
  if (digitos.length === 9) salida.push("+34" + nueve);
  return salida.filter(function (v, i, a) { return v && a.indexOf(v) === i; });
}

/** El formato con el que se ESCRIBE, para que deje de bailar. */
function hsTelefonoNormalizado(telefono) {
  var limpio = String(telefono).replace(/[\s.()-]/g, "");
  if (limpio.charAt(0) === "+") return limpio;
  var digitos = limpio.replace(/\D/g, "");
  return digitos.length === 9 ? "+34" + digitos : String(telefono).trim();
}

async function avisarAHubSpot(token, lead) {
  var grupos = [];
  if (lead.email) grupos.push({ filters: [{ propertyName: "email", operator: "EQ", value: lead.email }] });
  // HubSpot admite como mucho cinco grupos, y el del email ya ocupa uno.
  if (lead.telefono) {
    hsVariantesTelefono(lead.telefono).slice(0, lead.email ? 4 : 5).forEach(function (v) {
      grupos.push({ filters: [{ propertyName: "phone", operator: "EQ", value: v }] });
    });
  }

  var contactoId = null;
  if (grupos.length) {
    // Los grupos se combinan con O: vale que coincida el email o el telefono.
    var busqueda = await hsLlamar(token, "/crm/v3/objects/contacts/search", "POST", {
      filterGroups: grupos, properties: ["email", "phone"], limit: 1,
    });
    if (busqueda.results && busqueda.results[0]) contactoId = busqueda.results[0].id;
  }

  var props = { firstname: lead.nombre, phone: hsTelefonoNormalizado(lead.telefono) };
  if (lead.email) props.email = lead.email;

  if (contactoId) {
    // Solo se mandan los campos con dato: una segunda solicitud sin email no
    // debe borrar el email que ya tuviera la ficha.
    await hsLlamar(token, "/crm/v3/objects/contacts/" + contactoId, "PATCH", { properties: props });
  } else {
    props.lifecyclestage = "lead";
    var creado = await hsLlamar(token, "/crm/v3/objects/contacts", "POST", { properties: props });
    contactoId = creado.id;
  }
  if (!contactoId) throw new Error("hubspot sin contacto");

  var etapa = await hsEtapa(token);
  if (!etapa) return true;   // el contacto ya esta dentro; sin embudo no hay negociacion

  // El que manda el formulario de la ficha es exacto; el de la URL es un
  // apano para cuando no viene.
  var coche = lead.coche || cocheDeLaPagina(lead.pagina);
  await hsLlamar(token, "/crm/v3/objects/deals", "POST", {
    properties: {
      dealname: lead.nombre + (coche ? " \u2014 " + coche : " \u2014 solicitud web"),
      pipeline: etapa.pipeline,
      dealstage: etapa.dealstage,
      description: [
        coche ? "Coche: " + coche : null,
        "Pagina: " + lead.pagina,
        "Origen: formulario de quierorenting.es",
        lead.sospechoso ? "AVISO: relleno el campo trampa, revisar" : null,
        "Consentimiento: aceptada la politica de privacidad el " + lead.fecha,
      ].filter(Boolean).join("\n"),
    },
    // 3 es deal_to_contact en el catalogo de asociaciones de HubSpot.
    associations: [{
      to: { id: contactoId },
      types: [{ associationCategory: "HUBSPOT_DEFINED", associationTypeId: 3 }],
    }],
  });
  return true;
}

/**
 * Saca un nombre legible del coche a partir de la pagina desde la que escribio.
 * "/renting-bmw-x1/" -> "Bmw X1". No hay catalogo en el servidor, y para el
 * titulo de la negociacion esto es suficiente: lo importante es que el comercial
 * vea de un vistazo por que coche preguntan.
 */
function cocheDeLaPagina(pagina) {
  var m = /renting-([a-z0-9-]+)/i.exec(String(pagina || ""));
  if (!m) return null;
  var partes = m[1].split("-").filter(Boolean);
  // Las landings genericas (renting-barato, renting-suv, renting-coches-madrid)
  // no son un coche.
  var genericas = ["barato", "suv", "hibrido", "automatico", "furgoneta", "coches"];
  if (!partes.length || genericas.indexOf(partes[0]) !== -1) return null;
  // Las siglas van en mayuscula entera: "Mercedes Glc" o "Bmw X1" cantan mucho
  // en el titulo de una negociacion. Se toma por sigla lo que lleva un numero o
  // mide tres letras o menos, salvo las marcas que se escriben como palabra.
  var palabras = ["kia", "co"];
  return partes
    .map(function (p) {
      var sigla = /\d/.test(p) || (p.length <= 3 && palabras.indexOf(p) === -1);
      return sigla ? p.toUpperCase() : p.charAt(0).toUpperCase() + p.slice(1);
    })
    .join(" ");
}

/**
 * Aviso corto y aparte cuando un lead NO ha llegado a HubSpot.
 *
 * Esta web no guarda los leads en ninguna base de datos, asi que si HubSpot
 * falla el unico rastro seria el registro del servidor, que nadie mira. El
 * aviso va al mismo Telegram donde ya se leen los leads. Solo cuando falla: si
 * todo va bien no hay ruido.
 */
async function avisarFalloHubSpot(token, chatId, lead) {
  try {
    await fetch("https://api.telegram.org/bot" + token + "/sendMessage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chatId,
        text: `⚠️ NO HA ENTRADO EN HUBSPOT
El lead de ${lead.nombre} (${lead.telefono}) esta guardado y avisado, pero no se ha podido crear en HubSpot. Hay que darlo de alta a mano o revisar la clave.`,
        disable_web_page_preview: true,
      }),
    });
  } catch (e) {
    /* si tampoco sale este aviso, no hay nada mas que hacer desde aqui */
  }
}

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");

  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ ok: false, error: "Método no permitido" });
  }

  // Solo desde las webs propias. No es una barrera fuerte —una cabecera se
  // falsifica— pero descarta el tráfico automático que no se molesta en fingirla.
  const origen = req.headers.origin || "";
  const referente = req.headers.referer || "";
  // En `vercel dev` el origen es localhost. Se acepta SOLO ahí: VERCEL_ENV vale
  // "production" o "preview" en el servidor de verdad, así que esta puerta no
  // existe fuera de la máquina de desarrollo.
  const enLocal = !process.env.VERCEL_ENV;
  const permitido =
    ORIGENES.includes(origen) ||
    ORIGEN_PREVIA.test(origen) ||
    (enLocal && /^http:\/\/localhost:\d+$/.test(origen)) ||
    (!origen && ORIGENES.some((o) => referente.startsWith(o)));
  if (!permitido) {
    return res.status(403).json({ ok: false, error: "Origen no permitido" });
  }

  const ip = (req.headers["x-forwarded-for"] || "").split(",")[0].trim() || "desconocida";
  if (demasiadosEnvios(ip)) {
    return res.status(429).json({
      ok: false,
      error: "Has enviado varias solicitudes seguidas. Espera unos minutos o llámanos.",
    });
  }

  const cuerpo = await leerCuerpo(req);
  if (!cuerpo || typeof cuerpo !== "object") {
    return res.status(400).json({ ok: false, error: "Solicitud no válida" });
  }

  // Trampa para robots: un campo oculto que una persona nunca rellena.
  //
  // OJO CON DESCARTAR A LA LIGERA. El campo se llamaba "website", y algunos
  // gestores de contraseñas y autorrellenos del navegador completan solos un
  // campo con ese nombre. Un cliente real con el autorrelleno puesto habría
  // visto "solicitud recibida" mientras su lead se tiraba a la basura: el
  // mismo fallo que este cambio venía a corregir, pero al revés.
  //
  // Así que ahora: nombre que ningún autorrelleno reconoce, y solo se descarta
  // en silencio lo que trae un enlace, que es la firma del spam automático.
  // Cualquier otra cosa se entrega marcada, porque perder un cliente cuesta
  // mucho más que recibir un mensaje molesto.
  const trampa = texto(cuerpo.confirmar, 200) || texto(cuerpo.website, 200);
  const pareceSpam = /https?:|www\.|<a\s|\[url/i.test(trampa);
  if (trampa && pareceSpam) {
    // Se responde que todo ha ido bien a propósito: así el robot no aprende
    // cuál de sus intentos ha sido descartado.
    return res.status(200).json({ ok: true });
  }
  const sospechoso = Boolean(trampa);

  const nombre = texto(cuerpo.nombre, 120);
  const telefono = texto(cuerpo.telefono, 25);
  const email = texto(cuerpo.email, 160);
  const pagina = texto(cuerpo.pagina, 300);
  // Lo manda el formulario de las fichas, que si sabe de que coche se
  // pregunta. Es mejor que deducirlo de la URL: ni la portada ni las
  // landings genericas llevan el coche en la direccion.
  const coche = texto(cuerpo.coche, 80);
  const consiente = cuerpo.rgpd === true || cuerpo.rgpd === "on" || cuerpo.rgpd === "true";

  if (nombre.length < 2) return res.status(400).json({ ok: false, error: "Introduce tu nombre" });
  if (!TELEFONO.test(telefono)) return res.status(400).json({ ok: false, error: "Introduce un teléfono válido" });
  if (email && !EMAIL.test(email)) return res.status(400).json({ ok: false, error: "El email no es válido" });
  // El consentimiento se comprueba también aquí: una casilla marcada en el
  // navegador no demuestra nada, se puede saltar. Sin consentimiento no hay
  // base para tratar el dato, así que no se envía a ninguna parte.
  if (!consiente) return res.status(400).json({ ok: false, error: "Debes aceptar la política de privacidad" });

  const claveCorreo = process.env.WEB3FORMS_API_KEY;
  const tokenTelegram = process.env.TELEGRAM_BOT_TOKEN;
  const chatTelegram = process.env.TELEGRAM_CHAT_ID;
  const tokenHubSpot = process.env.HUBSPOT_TOKEN;

  if (!claveCorreo && !tokenTelegram) {
    // Sin ningún canal configurado el lead se perdería en silencio, que es
    // justo lo que este cambio venía a evitar. Mejor decirlo.
    console.error("[lead] no hay ni WEB3FORMS_API_KEY ni TELEGRAM_BOT_TOKEN");
    return res.status(503).json({
      ok: false,
      error: "No podemos recoger la solicitud ahora mismo. Llámanos y te atendemos al momento.",
    });
  }

  const lead = {
    // Marca visible en el aviso: el lead llega igual, pero se ve de un vistazo
    // que rellenó el campo trampa y conviene mirarlo con lupa.
    sospechoso,
    nombre,
    telefono,
    email,
    coche,
    pagina,
    fecha: new Date().toLocaleString("es-ES", { timeZone: "Europe/Madrid" }),
  };

  const canales = [];
  if (claveCorreo) canales.push(avisarPorCorreo(claveCorreo, lead));
  if (tokenTelegram && chatTelegram) canales.push(avisarPorTelegram(tokenTelegram, chatTelegram, lead));
  // Sin HUBSPOT_TOKEN el canal esta apagado y no se toca la red: el codigo
  // puede estar desplegado antes de que exista el token.
  if (tokenHubSpot) canales.push(avisarAHubSpot(tokenHubSpot, lead));

  const resultados = await Promise.allSettled(canales);
  // Si el canal de HubSpot estaba encendido y ha fallado, se avisa aparte.
  if (tokenHubSpot && resultados.length === canales.length) {
    const hs = resultados[canales.length - 1];
    if (hs && hs.status === "rejected" && tokenTelegram && chatTelegram) {
      await avisarFalloHubSpot(tokenTelegram, chatTelegram, lead);
    }
  }
  const entregados = resultados.filter((r) => r.status === "fulfilled").length;

  resultados
    .filter((r) => r.status === "rejected")
    .forEach((r) => console.error("[lead] canal fallido:", r.reason && r.reason.message));

  // Basta con que UN canal haya entregado: el lead ya está en manos del negocio.
  // Si no llegó por ninguno, se dice, y el popup ofrece el teléfono como salida.
  if (entregados === 0) {
    return res.status(502).json({
      ok: false,
      error: "No hemos podido registrar tu solicitud. Llámanos y lo resolvemos al momento.",
    });
  }

  return res.status(200).json({ ok: true });
};
