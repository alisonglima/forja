#!/usr/bin/env node
import fs from "node:fs"; import path from "node:path";
import crypto from "node:crypto"; import { execFileSync } from "node:child_process";

const SCRIPT = "scripts/prova-kit/export-exato.mjs";
const EVIDENCIA = "p5-01-dimensoes";
const KIT = "@feimacode/open-design-agent-kit@0.4.0";
const WS = "workspace", FX = "fixtures";
const AJUDA = `Uso: node ${SCRIPT} --out DIR [--dry-run] [--help]\n\n  --out DIR    grava a evidencia em DIR/${EVIDENCIA}\n  --dry-run    imprime o plano JSON, sem executar processos nem criar arquivos\n  --help       mostra esta ajuda`;

const FIXTURES = [
  { nome: "cartao.html", w: 1080, h: 1350, titulo: "Cartao 1080 x 1350", sub: "Peca de feed em tamanho exato.", formato: "ig-portrait" },
  { nome: "story.html", w: 1080, h: 1920, titulo: "Story 1080 x 1920", sub: "Peca vertical em tamanho exato.", formato: "story" },
];

function fixture(w, h, titulo, sub) {
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>${titulo}</title><style>
html,body{margin:0;padding:0;width:${w}px;height:${h}px;overflow:hidden;background:#f2ede3}
[data-od-card]{box-sizing:border-box;width:${w}px;height:${h}px;padding:96px;background:#17324d;color:#fff;font-family:Arial,Helvetica,sans-serif;display:flex;flex-direction:column;justify-content:space-between}
h1{font-size:${Math.round(w / 9)}px;line-height:1.05;margin:0} p{font-size:${Math.round(w / 28)}px;line-height:1.35;margin:0}
.tag{font-size:${Math.round(w / 36)}px;letter-spacing:.08em;text-transform:uppercase;color:#f4c95d}
</style></head><body><section data-od-card><div class="tag">Prova K.2(a)</div><h1>${titulo}</h1><p>${sub}</p></section></body></html>`;
}

function sidecar(f) {
  return { version: 1, kind: "html", renderer: "html", status: "complete", exports: ["png"], metadata: { format: f.formato } };
}

function plano(out) {
  const workspace = path.join(out, WS);
  const kit = (...args) => ["npx", "--yes", KIT, "export", ...args, "--workspace", workspace];
  const r = (id, fonte, via, scale, arquivo, ...args) => ({ id, fonte, via, scale, arquivo, argv: kit(`${FX}/${fonte}.html`, ...args) });
  return [
    r("cartao-selector-1", "cartao", "selector", 1, "cartao-selector-1.png", "--format", "png", "--selector", "[data-od-card]", "--width", "1080", "--height", "1350", "--scale", "1"),
    r("cartao-preset", "cartao", "preset", 1, "cartao-preset.png", "--format", "png", "--preset", "ig-portrait", "--scale", "1"),
    r("cartao-width-height", "cartao", "width-height", 1, "cartao-width-height.png", "--format", "png", "--width", "1080", "--height", "1350", "--scale", "1"),
    r("story-preset", "story", "preset", 1, "story-preset.png", "--format", "png", "--preset", "story", "--scale", "1"),
    r("cartao-selector-rep", "cartao", "selector", 1, "cartao-selector-rep.png", "--format", "png", "--selector", "[data-od-card]", "--width", "1080", "--height", "1350", "--scale", "1"),
    r("cartao-scale2", "cartao", "scale2", 2, "cartao-scale2.png", "--format", "png", "--selector", "[data-od-card]", "--scale", "2"),
  ];
}

function opcoes(argv) {
  const o = { out: null, dry: false, help: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--help") o.help = true;
    else if (a === "--dry-run") o.dry = true;
    else if (a === "--out") { const v = argv[++i]; if (!v || v.startsWith("--")) return { erro: "--out exige DIR" }; o.out = v; }
    else if (a.startsWith("--out=")) o.out = a.slice(6);
    else return { erro: `argumento desconhecido: ${a}` };
  }
  return o;
}

function pngs(dir) {
  if (!fs.existsSync(dir)) return [];
  const achados = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) achados.push(...pngs(p)); else if (/\.png$/i.test(e.name)) achados.push(p);
  }
  return achados.sort();
}

function rodar(log, argv, env, cwd) {
  const inicio = Date.now(), reg = { argv, cwd, env: env.OPEN_DESIGN_BROWSER_PATH ?? null, exit: 0, ms: 0, stdout: "", stderr: "" };
  try {
    reg.stdout = execFileSync(argv[0], argv.slice(1), { cwd, env, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], maxBuffer: 16 * 1024 * 1024 });
    reg.ms = Date.now() - inicio; log.push(reg); return { ok: true, exit: 0, stdout: reg.stdout, stderr: "" };
  } catch (erro) {
    reg.exit = typeof erro.status === "number" ? erro.status : 1;
    reg.stdout = String(erro.stdout || ""); reg.stderr = String(erro.stderr || erro.message || "").trim();
    reg.ms = Date.now() - inicio; log.push(reg);
    return { ok: false, exit: reg.exit, stdout: reg.stdout, stderr: reg.stderr };
  }
}

function medir(log, png, env, cwd) {
  const res = rodar(log, ["identify", "-format", "%w|%h|%[colorspace]|%z|%[opaque]|%#", png], env, cwd);
  if (!res.ok) return null;
  const [w, h, cs, bits, op, sig] = res.stdout.trim().split("|");
  return { w: Number(w), h: Number(h), colorspace: cs.toLowerCase() === "srgb" ? "sRGB" : cs, bits: Number(bits), opaque: /^true$/i.test(op), assinatura: sig };
}

const hash = (png) => crypto.createHash("sha256").update(fs.readFileSync(png)).digest("hex");

function real(out, runs) {
  const ws = path.join(out, WS), fx = path.join(ws, FX), ev = path.join(out, EVIDENCIA);
  fs.mkdirSync(path.join(ws, ".open-design"), { recursive: true });
  fs.mkdirSync(fx, { recursive: true }); fs.mkdirSync(ev, { recursive: true });
  for (const f of FIXTURES) {
    fs.writeFileSync(path.join(fx, f.nome), fixture(f.w, f.h, f.titulo, f.sub));
    fs.writeFileSync(path.join(fx, `${f.nome}.artifact.json`), `${JSON.stringify(sidecar(f), null, 2)}\n`);
  }
  const env = { ...process.env }, log = [], registros = [], linhas = [], somas = [];
  for (const r of runs) {
    fs.rmSync(path.join(fx, "exports"), { recursive: true, force: true });
    const res = rodar(log, r.argv, env, ws), destino = path.join(ev, r.arquivo);
    const registro = { arquivo: r.arquivo, fonte: r.fonte, via: r.via, scale: r.scale, w: null, h: null, colorspace: null, bits: null, opaque: null, dpr: null, assinatura: null, sha256: null };
    if (!res.ok) registro.erro = `exit ${res.exit}: ${(res.stderr || "falha sem stderr").slice(0, 2000)}`;
    else {
      const listados = res.stdout.split(/\r?\n/).map((l) => l.trim()).filter((l) => path.isAbsolute(l) && /\.png$/i.test(l) && fs.existsSync(l));
      const origem = listados[0] ?? pngs(path.join(fx, "exports"))[0];
      if (!origem) registro.erro = "export nao listou nem gerou PNG";
      else {
        fs.copyFileSync(origem, destino);
        const m = medir(log, destino, env, ws);
        if (!m) registro.erro = "identify falhou";
        else {
          Object.assign(registro, m, { dpr: Number((m.w / 1080).toFixed(4)), sha256: hash(destino) });
          linhas.push(`${r.arquivo} ${m.w}x${m.h} ${m.assinatura}`); somas.push(`${registro.sha256}  ${r.arquivo}`);
        }
      }
    }
    registros.push(registro);
  }
  fs.writeFileSync(path.join(ev, "dimensoes.json"), `${JSON.stringify(registros, null, 2)}\n`);
  fs.writeFileSync(path.join(ev, "dimensoes.txt"), `${linhas.join("\n")}\n`);
  fs.writeFileSync(path.join(ev, "sha256sums.txt"), `${somas.join("\n")}\n`);
  fs.writeFileSync(path.join(ev, "comandos.log"), `${log.map((x) => JSON.stringify(x)).join("\n")}\n`);
}

function main() {
  const o = opcoes(process.argv.slice(2));
  if (o.erro) { console.error(`erro: ${o.erro}\n${AJUDA}`); return 2; }
  if (o.help) { console.log(AJUDA); return 0; }
  if (!o.out) { console.error(`erro: --out DIR e obrigatorio\n${AJUDA}`); return 2; }
  const out = path.resolve(o.out), runs = plano(out);
  if (o.dry) {
    const sidecars = FIXTURES.map((f) => `${WS}/${FX}/${f.nome}.artifact.json`);
    console.log(JSON.stringify({ script: process.argv[1] ?? SCRIPT, evidencia: EVIDENCIA, workspace: WS, sidecars, comandos: runs.map((r) => r.argv.join(" ")) }, null, 2));
    return 0;
  }
  try { real(out, runs); console.log(`evidencia gravada em ${path.join(out, EVIDENCIA)}`); return 0; }
  catch (erro) { console.error(`erro: ${erro.message}`); return 1; }
}

process.exitCode = main();
