#!/usr/bin/env node
// L-PROVA-KIT-04: lote CSV de 3 linhas (prova K.2d). So executa e registra; nao decide.
// Interface: --out DIR [--dry-run] [--help]. Sem --dry-run nada externo roda.
import crypto from "node:crypto"; import fs from "node:fs";
import path from "node:path"; import { spawnSync } from "node:child_process";
const EVID = "p5-04-lote";
const KIT = "@feimacode/open-design-agent-kit@0.4.0";
const AJUDA = `uso: node scripts/prova-kit/lote-csv.mjs --out DIR [--dry-run] [--help]

  --out DIR    grava a evidencia em DIR/${EVID} (fixtures em DIR/fixtures)
  --dry-run    imprime o plano JSON, sem executar processos nem criar arquivos
  --help       mostra esta ajuda`;
const CSV = ["nome,cargo,titulo",
  '"Maria Aparecida de Oliveira Santos Nascimento",Coordenação,"Encontro de líderes"',
  '"João Conceição",Educação,"Ação de formação"',
  '"Ana\nPaula",Voluntariado,"Café com a comunidade"'].join("\r\n") + "\r\n";
const HTML = `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Lote CSV</title><style>
@page{size:A5;margin:0}html,body{margin:0;padding:0;background:#f4f1ea;color:#111;font-family:Arial,Helvetica,sans-serif}
[data-od-card]{box-sizing:border-box;width:100%;min-height:100vh;padding:12mm;background:#fff;display:flex;flex-direction:column;justify-content:space-between}
p{margin:0}.cargo{font-size:14pt;color:#555}.nome{font-size:30pt;line-height:1.15;white-space:pre-line;overflow-wrap:normal;hyphens:none}
.titulo{font-size:18pt;border-top:1px solid #ccc;padding-top:6mm}.rodape{font-size:9pt;color:#777}
</style></head><body><main data-od-card><p class="cargo" data-od-field="cargo">{{cargo}}</p><h1 class="nome" data-od-field="nome">{{nome}}</h1><p class="titulo" data-od-field="titulo">{{titulo}}</p><p class="rodape">Prova K.2(d) - lote CSV</p></main></body></html>`;
function sair(msg) { process.stderr.write(`erro: ${msg}\n${AJUDA}\n`); process.exit(2); }
function opcoes(argv) {
  const o = { out: null, dry: false, help: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--help" || a === "-h") o.help = true;
    else if (a === "--dry-run") o.dry = true;
    else if (a === "--out") { const v = argv[++i]; if (!v || v.startsWith("-")) sair("--out exige DIR"); o.out = v; }
    else if (a.startsWith("--out=")) o.out = a.slice(6);
    else sair(`argumento desconhecido: ${a}`);
  }
  return o;
}
function plano(out) {
  const fix = path.join(out, "fixtures"), html = path.join(fix, "lote.html"), dados = path.join(fix, "lote.csv");
  const kit = (formato, extra) => ["npx", "--yes", KIT, "export", html, "--format", formato, ...extra, "--data", dados, "--name-field", "nome"];
  return [{ argv: kit("pdf", ["--preset", "a5", "--bleed", "0"]) }, { argv: kit("png", ["--preset", "ig-portrait"]) }];
}
function listar(dir) {
  const achados = [];
  const andar = (d) => { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) andar(p); else achados.push(p); } };
  if (fs.existsSync(dir)) andar(dir);
  return achados;
}
function executar(out) {
  const ev = path.join(out, EVID), fix = path.join(out, "fixtures"), saida = path.join(out, "saida");
  fs.mkdirSync(ev, { recursive: true }); fs.mkdirSync(fix, { recursive: true });
  fs.rmSync(saida, { recursive: true, force: true }); fs.mkdirSync(saida, { recursive: true });
  fs.rmSync(path.join(ev, "erro.json"), { force: true });
  fs.writeFileSync(path.join(fix, "lote.html"), HTML, "utf8"); fs.writeFileSync(path.join(fix, "lote.csv"), CSV, "utf8");
  fs.copyFileSync(path.join(fix, "lote.csv"), path.join(ev, "lote.csv"));
  const env = { ...process.env, OPEN_DESIGN_OUTPUT_DIR: saida, OPEN_DESIGN_BROWSER_PATH: "/usr/local/bin/google-chrome-prova" };
  const logPath = path.join(ev, "comandos.log"); fs.writeFileSync(logPath, "", "utf8");
  const rodar = (argv) => {
    const t0 = Date.now();
    const r = spawnSync(argv[0], argv.slice(1), { cwd: out, env, encoding: "utf8", maxBuffer: 64 * 1024 * 1024, timeout: 600000 });
    const ms = Date.now() - t0, codigo = r.error ? 127 : (typeof r.status === "number" ? r.status : 124);
    let linha = `$ ${argv.join(" ")}\nexit=${codigo} duracao_ms=${ms}\n`;
    if (r.stdout) linha += `--- stdout ---\n${r.stdout}\n`;
    if (r.stderr) linha += `--- stderr ---\n${r.stderr}\n`;
    if (r.error) linha += `--- error ---\n${r.error.message}\n`;
    fs.appendFileSync(logPath, `${linha}\n`, "utf8");
    return { codigo, stdout: r.stdout || "", stderr: r.stderr || "" };
  };
  try {
    for (const cmd of plano(out)) {
      const r = rodar(cmd.argv);
      if (r.codigo !== 0) throw new Error(`comando falhou (exit ${r.codigo}): ${cmd.argv.join(" ")}`);
    }
    const pares = listar(saida).filter((p) => /\.(png|pdf)$/i.test(p)).map((src) => ({ src, nome: path.basename(src) })).sort((a, b) => a.nome.localeCompare(b.nome));
    if (!pares.length) throw new Error(`nenhum PNG/PDF gerado em ${saida}`);
    for (const p of pares) fs.copyFileSync(p.src, path.join(ev, p.nome));
    fs.writeFileSync(path.join(ev, "arquivos.txt"), `${pares.map((p) => p.nome).join("\n")}\n`, "utf8");
    const pdfs = pares.filter((p) => /\.pdf$/i.test(p.nome)).map((p) => path.join(ev, p.nome));
    if (!pdfs.length) throw new Error("nenhum PDF gerado");
    let info = "", texto = "";
    for (const pdf of pdfs) {
      const r = rodar(["pdfinfo", pdf]);
      info += `== ${path.basename(pdf)} ==\n${r.stdout}`;
      if (r.codigo !== 0) info += `pdfinfo exit=${r.codigo}\n${r.stderr}`;
      const t = rodar(["pdftotext", "-layout", pdf, "-"]);
      if (t.codigo !== 0) throw new Error(`pdftotext falhou (exit ${t.codigo}): ${path.basename(pdf)}`);
      texto += t.stdout;
    }
    fs.writeFileSync(path.join(ev, "lote.pdfinfo.txt"), info, "utf8");
    fs.writeFileSync(path.join(ev, "lote.pdftotext.txt"), texto, "utf8");
    const somas = [];
    for (const e of fs.readdirSync(ev, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      if (!e.isFile() || e.name === "sha256sums.txt") continue;
      const h = crypto.createHash("sha256").update(fs.readFileSync(path.join(ev, e.name))).digest("hex");
      somas.push(`${h}  ${e.name}`);
    }
    fs.writeFileSync(path.join(ev, "sha256sums.txt"), `${somas.join("\n")}\n`, "utf8");
    process.stdout.write(`evidencia gravada em ${ev}\n`);
  } catch (erro) {
    const texto = erro && erro.message ? erro.message : String(erro);
    fs.writeFileSync(path.join(ev, "erro.json"), `${JSON.stringify({ erro: texto }, null, 2)}\n`, "utf8");
    throw erro;
  }
}
function main() {
  const o = opcoes(process.argv.slice(2));
  if (o.help) { process.stdout.write(`${AJUDA}\n`); return 0; }
  if (!o.out) { process.stderr.write(`erro: --out DIR e obrigatorio\n${AJUDA}\n`); return 2; }
  const out = path.resolve(o.out), comandos = plano(out);
  if (o.dry) {
    const env = `OPEN_DESIGN_OUTPUT_DIR=${path.join(out, "saida")}`;
    process.stdout.write(`${JSON.stringify({ script: path.resolve(process.argv[1] || "scripts/prova-kit/lote-csv.mjs"), evidencia: EVID, comandos: comandos.map((c) => `${env} ${c.argv.join(" ")}`) }, null, 2)}\n`);
    return 0;
  }
  try { executar(out); return 0; } catch (erro) { process.stderr.write(`erro: ${erro.message || erro}\n`); return 1; }
}
process.exitCode = main();
