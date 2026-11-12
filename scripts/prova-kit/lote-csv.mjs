#!/usr/bin/env node
// L-PROVA-KIT-04R: lote CSV de 3 linhas (prova K.2d). So executa e registra; nao decide.
// Interface: --out DIR [--dry-run] [--help]. Sem --dry-run nada externo roda.
import crypto from "node:crypto"; import fs from "node:fs";
import path from "node:path"; import { spawnSync } from "node:child_process";
const EVID = "p5-04-lote";
const KIT = "@feimacode/open-design-agent-kit@0.4.0";
const WS = "workspace", FIX = "fixtures", ENTRY = `${FIX}/lote.html`, DADOS = `${FIX}/lote.csv`;
const SIDECAR = `${ENTRY}.artifact.json`;
const AJUDA = `uso: node scripts/prova-kit/lote-csv.mjs --out DIR [--dry-run] [--help]

  --out DIR    grava a evidencia em DIR/${EVID} (workspace em DIR/${WS})
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
const CARTAO = {
  version: 1, kind: "html", entry: "lote.html", renderer: "html",
  exports: ["html", "pdf", "png"], status: "complete", metadata: { format: "a5" },
};
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
// O kit resolve o entry a partir do cwd e exige --workspace; a saida vai para
// a pasta exports/ ao lado do entry, com sufixo do slug de --name-field.
function plano(out) {
  const ws = path.resolve(out, WS);
  const kit = (formato, extra) => ["npx", "--yes", KIT, "export", ENTRY,
    "--format", formato, ...extra, "--data", DADOS, "--name-field", "nome",
    "--workspace", ws];
  return {
    workspace: WS,
    sidecars: [path.join(WS, SIDECAR)],
    comandos: [
      kit("pdf", ["--preset", "a5", "--bleed", "0"]),
      kit("png", ["--preset", "ig-portrait"]),
    ],
  };
}
function listar(dir) {
  const achados = [];
  const andar = (d) => { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) andar(p); else achados.push(p); } };
  if (fs.existsSync(dir)) andar(dir);
  return achados;
}
function hash(p) { return crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex"); }
// Copia cada resultado logo apos a chamada (o kit reusa o mesmo nome base).
function coletar(ev, exportsDir, antes, stdout) {
  const artefato = (p) => fs.existsSync(p) && /\.(png|pdf|jpe?g)$/i.test(p);
  const fontes = [...stdout.split(/\r?\n/).map((s) => s.trim()).filter(artefato),
    ...listar(exportsDir).filter((p) => artefato(p) && !antes.has(p))];
  const vistos = new Set(), nomes = [];
  for (const src of fontes) {
    const real = fs.realpathSync(src);
    if (vistos.has(real)) continue;
    vistos.add(real);
    const base = path.basename(src), ext = path.extname(base);
    let nome = base, destino = path.join(ev, nome), n = 2;
    while (fs.existsSync(destino) && hash(destino) !== hash(src)) {
      nome = `${path.basename(base, ext)}-${n}${ext}`; destino = path.join(ev, nome); n++;
    }
    if (!fs.existsSync(destino)) fs.copyFileSync(src, destino);
    nomes.push(nome);
  }
  return nomes;
}
function executar(out) {
  const ev = path.join(out, EVID), ws = path.join(out, WS), fix = path.join(ws, FIX);
  fs.rmSync(ev, { recursive: true, force: true }); fs.rmSync(ws, { recursive: true, force: true });
  fs.mkdirSync(ev, { recursive: true });
  fs.mkdirSync(path.join(ws, ".open-design"), { recursive: true }); fs.mkdirSync(fix, { recursive: true });
  fs.writeFileSync(path.join(ws, ENTRY), HTML, "utf8");
  fs.writeFileSync(path.join(ws, DADOS), CSV, "utf8");
  fs.writeFileSync(path.join(ws, SIDECAR), `${JSON.stringify(CARTAO, null, 2)}\n`, "utf8");
  fs.writeFileSync(path.join(ev, "lote.csv"), CSV, "utf8");
  const logPath = path.join(ev, "comandos.log"); fs.writeFileSync(logPath, "", "utf8");
  const env = { ...process.env, OPEN_DESIGN_BROWSER_PATH: process.env.OPEN_DESIGN_BROWSER_PATH || "/usr/local/bin/google-chrome-prova" };
  const exportsDir = path.join(fix, "exports");
  const rodar = (argv) => {
    const t0 = Date.now();
    const r = spawnSync(argv[0], argv.slice(1), { cwd: ws, env, encoding: "utf8", maxBuffer: 64 * 1024 * 1024, timeout: 600000 });
    const ms = Date.now() - t0, codigo = r.error ? 127 : (typeof r.status === "number" ? r.status : 124);
    let linha = `$ ${argv.join(" ")}\nexit=${codigo} duracao_ms=${ms}\n`;
    if (r.stdout) linha += `--- stdout ---\n${r.stdout}\n`;
    if (r.stderr) linha += `--- stderr ---\n${r.stderr}\n`;
    if (r.error) linha += `--- error ---\n${r.error.message}\n`;
    fs.appendFileSync(logPath, `${linha}\n`, "utf8");
    return { codigo, stdout: r.stdout || "", stderr: r.stderr || "" };
  };
  const arquivos = new Set();
  let falhas = 0;
  // Registra o resultado do kit (inclusive exit != 0) e segue: quem julga e o teste.
  for (const argv of plano(out).comandos) {
    const antes = new Set(listar(exportsDir));
    const r = rodar(argv);
    if (r.codigo !== 0) falhas++;
    for (const nome of coletar(ev, exportsDir, antes, r.stdout)) arquivos.add(nome);
  }
  const nomes = [...arquivos].sort();
  fs.writeFileSync(path.join(ev, "arquivos.txt"), `${nomes.join("\n")}\n`, "utf8");
  const pdfs = nomes.filter((n) => n.toLowerCase().endsWith(".pdf")).map((n) => path.join(ev, n));
  let info = "", texto = "";
  for (const pdf of pdfs) {
    const r = rodar(["pdfinfo", pdf]);
    info += `== ${path.basename(pdf)} ==\n${r.stdout}`;
    if (r.codigo !== 0) info += `pdfinfo exit=${r.codigo}\n${r.stderr}`;
    const t = rodar(["pdftotext", "-layout", pdf, "-"]);
    if (t.codigo === 0) { texto += t.stdout; if (t.stdout && !t.stdout.endsWith("\f")) texto += "\f"; }
    else info += `pdftotext ${path.basename(pdf)} exit=${t.codigo}\n${t.stderr}`;
  }
  fs.writeFileSync(path.join(ev, "lote.pdfinfo.txt"), info, "utf8");
  fs.writeFileSync(path.join(ev, "lote.pdftotext.txt"), texto, "utf8");
  const somas = [];
  for (const e of fs.readdirSync(ev, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    if (!e.isFile() || e.name === "sha256sums.txt") continue;
    somas.push(`${hash(path.join(ev, e.name))}  ${e.name}`);
  }
  fs.writeFileSync(path.join(ev, "sha256sums.txt"), `${somas.join("\n")}\n`, "utf8");
  if (falhas) process.stderr.write(`aviso: ${falhas} comando(s) do kit com exit != 0 (ver comandos.log)\n`);
  process.stdout.write(`evidencia gravada em ${ev}\n`);
}
function main() {
  const o = opcoes(process.argv.slice(2));
  if (o.help) { process.stdout.write(`${AJUDA}\n`); return 0; }
  if (!o.out) { process.stderr.write(`erro: --out DIR e obrigatorio\n${AJUDA}\n`); return 2; }
  const out = path.resolve(o.out), planoOut = plano(out);
  if (o.dry) {
    process.stdout.write(`${JSON.stringify({ script: path.resolve(process.argv[1] || "scripts/prova-kit/lote-csv.mjs"), evidencia: EVID, workspace: planoOut.workspace, sidecars: planoOut.sidecars, comandos: planoOut.comandos.map((c) => c.join(" ")) }, null, 2)}\n`);
    return 0;
  }
  try { executar(out); return 0; } catch (erro) {
    const ev = path.join(out, EVID), texto = erro && erro.message ? erro.message : String(erro);
    try {
      fs.mkdirSync(ev, { recursive: true });
      fs.writeFileSync(path.join(ev, "erro.json"), `${JSON.stringify({ erro: texto }, null, 2)}\n`, "utf8");
    } catch { /* sem evidencia gravavel */ }
    process.stderr.write(`erro: ${texto}\n`); return 1;
  }
}
process.exitCode = main();
