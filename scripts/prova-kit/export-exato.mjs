#!/usr/bin/env node
import fs from "node:fs"; import path from "node:path";
import crypto from "node:crypto"; import { execFileSync } from "node:child_process";

const SCRIPT = "scripts/prova-kit/export-exato.mjs";
const EVIDENCIA = "p5-01-dimensoes";
const KIT = "@feimacode/open-design-agent-kit@0.4.0";
const AJUDA = `Uso: node ${SCRIPT} --out DIR [--dry-run] [--help]\n\n  --out DIR    grava a evidencia em DIR/${EVIDENCIA}\n  --dry-run    imprime o plano JSON, sem executar processos nem criar arquivos\n  --help       mostra esta ajuda`;

function fixture(w, h, titulo, sub) {
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>${titulo}</title><style>
html,body{margin:0;padding:0;width:${w}px;height:${h}px;overflow:hidden;background:#f2ede3}
[data-od-card]{box-sizing:border-box;width:${w}px;height:${h}px;padding:96px;background:#17324d;color:#fff;font-family:Arial,Helvetica,sans-serif;display:flex;flex-direction:column;justify-content:space-between}
h1{font-size:${Math.round(w / 9)}px;line-height:1.05;margin:0} p{font-size:${Math.round(w / 28)}px;line-height:1.35;margin:0}
.tag{font-size:${Math.round(w / 36)}px;letter-spacing:.08em;text-transform:uppercase;color:#f4c95d}
</style></head><body><section data-od-card><div class="tag">Prova K.2(a)</div><h1>${titulo}</h1><p>${sub}</p></section></body></html>`;
}

function plano(out) {
  const fx = (nome) => path.join(out, "fixtures", nome);
  const kit = (...args) => ["npx", "--yes", KIT, "export", ...args];
  const r = (id, fonte, via, scale, arquivo, ...args) => ({ id, fonte, via, scale, arquivo, argv: kit(...args) });
  return [
    r("cartao-selector-1", "cartao", "selector", 1, "cartao-selector-1.png", fx("cartao.html"), "--format", "png", "--selector", "[data-od-card]", "--width", "1080", "--height", "1350", "--scale", "1"),
    r("cartao-preset", "cartao", "preset", 1, "cartao-preset.png", fx("cartao.html"), "--format", "png", "--preset", "ig-portrait", "--scale", "1"),
    r("cartao-width-height", "cartao", "width-height", 1, "cartao-width-height.png", fx("cartao.html"), "--format", "png", "--width", "1080", "--height", "1350", "--scale", "1"),
    r("story-preset", "story", "preset", 1, "story-preset.png", fx("story.html"), "--format", "png", "--preset", "story", "--scale", "1"),
    r("cartao-selector-rep", "cartao", "selector", 1, "cartao-selector-rep.png", fx("cartao.html"), "--format", "png", "--selector", "[data-od-card]", "--width", "1080", "--height", "1350", "--scale", "1"),
    r("cartao-scale2", "cartao", "scale2", 2, "cartao-scale2.png", fx("cartao.html"), "--format", "png", "--selector", "[data-od-card]", "--scale", "2"),
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
  const inicio = Date.now(), reg = { argv, env: env.OPEN_DESIGN_OUTPUT_DIR ?? null, exit: 0, ms: 0 };
  try {
    const saida = execFileSync(argv[0], argv.slice(1), { cwd, env, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], maxBuffer: 16 * 1024 * 1024 });
    reg.ms = Date.now() - inicio; log.push(reg); return saida;
  } catch (erro) {
    reg.exit = typeof erro.status === "number" ? erro.status : 1;
    reg.ms = Date.now() - inicio; log.push(reg);
    const detalhe = String(erro.stderr || erro.message || "").trim();
    throw new Error(`comando falhou (exit ${reg.exit}): ${argv.join(" ")}${detalhe ? `\n${detalhe}` : ""}`);
  }
}

function medir(log, png, env, cwd) {
  const [w, h, cs, bits, op, sig] = rodar(log, ["identify", "-format", "%w|%h|%[colorspace]|%z|%[opaque]|%#", png], env, cwd).trim().split("|");
  return [Number(w), Number(h), cs.toLowerCase() === "srgb" ? "sRGB" : cs, Number(bits), /^true$/i.test(op), sig];
}

const hash = (png) => crypto.createHash("sha256").update(fs.readFileSync(png)).digest("hex");

function real(out, runs) {
  const fx = path.join(out, "fixtures"), ev = path.join(out, EVIDENCIA);
  fs.mkdirSync(fx, { recursive: true }); fs.mkdirSync(ev, { recursive: true });
  fs.writeFileSync(path.join(fx, "cartao.html"), fixture(1080, 1350, "Cartao 1080 x 1350", "Peca de feed em tamanho exato."));
  fs.writeFileSync(path.join(fx, "story.html"), fixture(1080, 1920, "Story 1080 x 1920", "Peca vertical em tamanho exato."));
  const log = [], registros = [], linhas = [], somas = [];
  try {
    for (const r of runs) {
      const dir = path.join(out, "runs", r.id), env = { ...process.env, OPEN_DESIGN_OUTPUT_DIR: dir };
      fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
      rodar(log, r.argv, env, out);
      const achados = pngs(dir);
      if (!achados.length) throw new Error(`nenhum PNG gerado em ${dir}`);
      const destino = path.join(ev, r.arquivo); fs.copyFileSync(achados[0], destino);
      const [w, h, colorspace, bits, opaque, assinatura] = medir(log, destino, env, out), sha256 = hash(destino);
      registros.push({ arquivo: r.arquivo, fonte: r.fonte, via: r.via, scale: r.scale, w, h, colorspace, bits, opaque, dpr: Number((w / 1080).toFixed(4)), assinatura, sha256 });
      linhas.push(`${r.arquivo} ${w}x${h} ${assinatura}`); somas.push(`${sha256}  ${r.arquivo}`);
    }
    fs.writeFileSync(path.join(ev, "dimensoes.json"), `${JSON.stringify(registros, null, 2)}\n`);
    fs.writeFileSync(path.join(ev, "dimensoes.txt"), `${linhas.join("\n")}\n`);
    fs.writeFileSync(path.join(ev, "sha256sums.txt"), `${somas.join("\n")}\n`);
  } finally {
    fs.writeFileSync(path.join(ev, "comandos.log"), `${log.map((x) => JSON.stringify(x)).join("\n")}\n`);
  }
}

function main() {
  const o = opcoes(process.argv.slice(2));
  if (o.erro) { console.error(`erro: ${o.erro}\n${AJUDA}`); return 2; }
  if (o.help) { console.log(AJUDA); return 0; }
  if (!o.out) { console.error(`erro: --out DIR e obrigatorio\n${AJUDA}`); return 2; }
  const out = path.resolve(o.out), runs = plano(out);
  if (o.dry) {
    const comandos = runs.map((r) => `OPEN_DESIGN_OUTPUT_DIR=${path.join(out, "runs", r.id)} ${r.argv.join(" ")}`);
    console.log(JSON.stringify({ script: process.argv[1] ?? SCRIPT, evidencia: EVIDENCIA, comandos }, null, 2));
    return 0;
  }
  try { real(out, runs); console.log(`evidencia gravada em ${path.join(out, EVIDENCIA)}`); return 0; }
  catch (erro) { console.error(`erro: ${erro.message}`); return 1; }
}

process.exitCode = main();
