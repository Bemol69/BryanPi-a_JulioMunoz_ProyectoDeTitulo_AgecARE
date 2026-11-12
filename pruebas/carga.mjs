// Prueba de carga de AgeCare: cientos de usuarios simultáneos usando el sitio y la Consola.
//
// Cada «usuario virtual» hace un recorrido real:
//   · Familia (80 %): se registra → crea un familiar → busca cuidadoras → abre un perfil →
//     contacta (abre un chat) → manda mensajes → revisa sus chats.
//   · Cuidadora (15 %): se registra → completa su perfil → revisa reseñas, mensajes y chats.
//   · Staff (5 %): entra a la Consola → lista cuidadoras → ranking → métricas de fidelización.
//
// Uso (con las dos APIs levantadas; necesita Node 18 o superior, sin instalar nada):
//   node pruebas/carga.mjs --usuarios 300                 # ola de registros: todos crean su cuenta a la vez (peor caso)
//   node pruebas/carga.mjs --usuarios 300 --modo uso      # uso normal: ya tienen cuenta y navegan, buscan y chatean
//   node pruebas/carga.mjs --usuarios 500 --sitio http://127.0.0.1:8001/api/v1 --consola http://127.0.0.1:8000/api/v1/admin
//
// Imprime una tabla por acción (p50 / p95 / p99 en milisegundos y errores) y guarda el detalle en
// pruebas/resultados/. Crea cuentas de prueba: ejecútalo contra un ambiente de pruebas, no contra producción.
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { randomBytes } from "node:crypto";

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, all) => {
  if (a.startsWith("--")) acc.push([a.slice(2), all[i + 1] && !all[i + 1].startsWith("--") ? all[i + 1] : "true"]);
  return acc;
}, []));
const USERS = Number(args.usuarios ?? 300);
const SITE = args.sitio ?? "http://127.0.0.1:8001/api/v1";
const CONSOLE = args.consola ?? "http://127.0.0.1:8000/api/v1/admin";
const RAMP_S = Number(args.rampa ?? 3);
const LABEL = args.etiqueta ?? "";
const MODE = args.modo ?? "registro"; // "registro" | "uso"

const samples = new Map();
const errors = new Map();
const push = (map, key, value) => { if (!map.has(key)) map.set(key, []); map.get(key).push(value); };

async function call(name, method, url, { headers = {}, body } = {}, expect = [200, 201, 204]) {
  const t0 = performance.now();
  try {
    const res = await fetch(url, {
      method,
      headers: { ...(body ? { "Content-Type": "application/json" } : {}), ...headers },
      body: body ? JSON.stringify(body) : undefined,
    });
    const text = await res.text();
    push(samples, name, performance.now() - t0);
    if (!expect.includes(res.status)) push(errors, name, `${res.status} ${text.slice(0, 80)}`);
    let json = null;
    try { json = text ? JSON.parse(text) : null; } catch { /* sin cuerpo JSON */ }
    return { status: res.status, json };
  } catch (e) {
    push(samples, name, performance.now() - t0);
    push(errors, name, e.cause?.code ?? e.message);
    return null;
  }
}

const tag = () => randomBytes(5).toString("hex");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function registrar(kind, measured = true) {
  const t = tag();
  const body = { full_name: `${kind === "family" ? "Familia" : "Cuidadora"} Carga ${t}`, email: `carga.${t}@${kind === "family" ? "familia" : "cuidado"}.cl`,
                 password: "Carga12345!", account_type: kind };
  const name = `registro (${kind === "family" ? "familia" : "cuidadora"})`;
  if (measured) return call(name, "POST", `${SITE}/auth/register`, { body });
  const res = await fetch(`${SITE}/auth/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return { status: res.status, json: await res.json().catch(() => null) };
}

async function familia(session) {
  const t = tag();
  const r = session ?? await registrar("family");
  if (!r || r.status !== 201) return;
  const h = { Authorization: `Bearer ${r.json.access_token}` };
  const p = await call("crear familiar", "POST", `${SITE}/patients`, { headers: h, body: {
    full_name: `Abuela ${t}`, birth_date: "1945-03-02", conditions: ["Hipertensión"], notes: "Prueba de carga" } });
  await call("listar familiares", "GET", `${SITE}/patients`, { headers: h });
  if (p?.json?.patient_id) await call("ficha del familiar", "GET", `${SITE}/patients/${p.json.patient_id}`, { headers: h });
  const s = await call("buscar cuidadoras", "GET", `${SITE}/marketplace/caregivers?page_size=20`, { headers: h });
  const items = s?.json?.items ?? [];
  if (!items.length) return;
  const cid = items[Math.floor(Math.random() * items.length)].profile_id;
  await call("perfil de cuidadora", "GET", `${SITE}/marketplace/caregivers/${cid}`, { headers: h });
  const c = await call("contactar (abre chat)", "POST", `${SITE}/marketplace/caregivers/${cid}/contact`, {
    headers: h, body: { message: "Hola, ¿tienes disponibilidad esta semana?" } });
  const conv = c?.json?.conversation_id;
  if (conv) {
    for (const text of ["¿Podemos hablar mañana?", "Gracias, quedamos así."]) {
      await call("enviar mensaje", "POST", `${SITE}/chats/${conv}/messages`, { headers: h, body: { body: text } });
    }
    await call("abrir chat", "GET", `${SITE}/chats/${conv}`, { headers: h });
  }
  await call("listar chats", "GET", `${SITE}/chats`, { headers: h });
}

async function cuidadora(session) {
  const r = session ?? await registrar("caregiver");
  if (!r || r.status !== 201) return;
  const h = { Authorization: `Bearer ${r.json.access_token}` };
  await call("completar perfil", "PUT", `${SITE}/caregiver/profile`, { headers: h, body: {
    headline: "Cuidadora con experiencia", bio: "Experiencia en cuidado de adultos mayores. ".repeat(2), years_experience: 3,
    specialties: ["Alzheimer"], languages: ["Español"], zones: ["Providencia"], is_listed: true } });
  for (const [name, path] of [["mi perfil", "/caregiver/profile"], ["mis reseñas", "/caregiver/reviews"],
                              ["mis mensajes", "/caregiver/contacts"], ["listar chats", "/chats"]]) {
    await call(name, "GET", `${SITE}${path}`, { headers: h });
  }
}

async function staff() {
  const r = await call("login Consola", "POST", `${CONSOLE}/auth/login`, { body: { email: "admin@wellq.co.uk", password: "Admin123!" } });
  if (!r || r.status !== 200) return;
  const h = { Authorization: `Bearer ${r.json.access_token}` };
  for (const [name, path] of [["Consola: cuidadoras", "/marketplace/caregivers"], ["Consola: ranking", "/marketplace/caregivers/ranking"],
                              ["Consola: métricas fidelización", "/marketing/dashboard/summary"]]) {
    await call(name, "GET", `${CONSOLE}${path}`, { headers: h });
  }
}

const pct = (sorted, p) => sorted[Math.min(sorted.length - 1, Math.floor((sorted.length * p) / 100))];

async function main() {
  // Modo «uso»: primero se crean las cuentas (sin medir), después se mide solo lo que hacen una vez dentro.
  const roles = Array.from({ length: USERS }, () => { const r = Math.random(); return r < 0.8 ? "family" : r < 0.95 ? "caregiver" : "staff"; });
  const sessions = new Array(USERS).fill(undefined);
  if (MODE === "uso") {
    process.stdout.write(`Preparando ${USERS} cuentas…`);
    let next = 0;
    await Promise.all(Array.from({ length: 8 }, async () => {
      while (next < USERS) { const i = next++; if (roles[i] !== "staff") sessions[i] = await registrar(roles[i], false); }
    }));
    console.log(" listo.");
  }
  const started = performance.now();
  await Promise.all(Array.from({ length: USERS }, async (_, i) => {
    await sleep(Math.random() * RAMP_S * 1000);
    if (roles[i] === "family") await familia(sessions[i]); else if (roles[i] === "caregiver") await cuidadora(sessions[i]); else await staff();
  }));
  const elapsed = (performance.now() - started) / 1000;

  const total = [...samples.values()].reduce((n, v) => n + v.length, 0);
  const failed = [...errors.values()].reduce((n, v) => n + v.length, 0);
  const rows = [...samples.entries()].map(([name, v]) => ({ name, v: [...v].sort((a, b) => a - b) }))
    .sort((a, b) => pct(b.v, 50) - pct(a.v, 50));
  const all = rows.flatMap((r) => r.v).sort((a, b) => a - b);
  const out = [
    `# Prueba de carga · ${USERS} usuarios simultáneos · ${MODE === "uso" ? "uso normal (ya tienen cuenta)" : "ola de registros (todos crean cuenta)"} ${LABEL}`.trim(),
    `Fecha: ${new Date().toISOString().slice(0, 16).replace("T", " ")} · duración ${elapsed.toFixed(1)} s · ${total} peticiones · ` +
      `${(total / elapsed).toFixed(0)} peticiones/s · errores ${failed} (${((100 * failed) / Math.max(total, 1)).toFixed(2)} %)`,
    "",
    "| Acción | Peticiones | Errores | p50 ms | p95 ms | p99 ms | Máx ms |",
    "|---|---:|---:|---:|---:|---:|---:|",
    ...rows.map(({ name, v }) => `| ${name} | ${v.length} | ${(errors.get(name) ?? []).length} | ${pct(v, 50).toFixed(0)} | ${pct(v, 95).toFixed(0)} | ${pct(v, 99).toFixed(0)} | ${v.at(-1).toFixed(0)} |`),
    "",
    `**Todas las peticiones:** p50 ${pct(all, 50).toFixed(0)} ms · p95 ${pct(all, 95).toFixed(0)} ms · p99 ${pct(all, 99).toFixed(0)} ms`,
  ];
  if (failed) {
    out.push("", "Errores distintos:");
    const seen = new Set();
    for (const [name, list] of errors) for (const e of list) if (!seen.has(`${name}${e}`) && seen.size < 12) { seen.add(`${name}${e}`); out.push(`- ${name}: ${e}`); }
  }
  const text = out.join("\n");
  console.log(text);
  const dir = join(dirname(fileURLToPath(import.meta.url)), "resultados");
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, `carga_${USERS}_${MODE}${LABEL ? "_" + LABEL : ""}.md`), text + "\n", "utf8");
}

main();
