#!/usr/bin/env node
// L-PROVA-KIT-03: preflight provocado. So executa e grava; nao decide.
// Interface: --out DIR [--dry-run] [--help]. Sem --dry-run nada externo roda.
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const EVID = "p5-03-preflight";
const KIT = "@feimacode/open-design-agent-kit@0.4.0";
// PNG 80x80 opaco, cinza medio; so para o defeito de ppi.
const PNG80 = "iVBORw0KGgoAAAANSUhEUgAAAFAAAABQCAIAAAABc2X6AAAAY0lEQVR42u3PAQEAAAgCIKc73R8FD0ifibCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsPAlAw3RgixS4EvNAAAAAElFTkSuQmCC";

function uso() {
  process.stdout.write(
    "uso: node scripts/prova-kit/preflight-provocado.mjs --out DIR [--dry-run] [--help]\n" +
      "  --out DIR   pasta raiz da prova (grava em DIR/" + EVID + ")\n" +
      "  --dry-run   imprime o plano JSON sem criar arquivos nem iniciar processos\n" +
      "  --help      esta ajuda\n"
  );
}

function falhar(msg) {
  process.stderr.write("erro: " + msg + "\n");
  process.exit(2);
}

function argumentos(argv) {
  let out = null;
  let dry = false;
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--help" || a === "-h") return { help: true };
    if (a === "--dry-run") dry = true;
    else if (a === "--out") {
      if (i + 1 >= argv.length || argv[i + 1].startsWith("-")) falhar("--out exige DIR");
      out = argv[++i];
    } else falhar("argumento desconhecido: " + a);
  }
  if (!out) falhar("--out DIR e obrigatorio");
  return { out: path.resolve(out), dry };
}

function pagina(titulo, dimensoes, estilo, corpo) {
  return (
    "<!doctype html>\n<html lang=\"pt-BR\"><head><meta charset=\"utf-8\">" +
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">" +
    "<title>" + titulo + "</title><style>html,body{margin:0;padding:0;background:#fff;}" +
    "*{box-sizing:border-box;}" + estilo + "</style></head><body>" +
    "<main data-od-card style=\"" + dimensoes + "\">" + corpo + "</main></body></html>\n"
  );
}

function fixtures() {
  const card = "width:1080px;height:1350px;position:relative;background:#fff;color:#111;";
  const estouro = "palavra ".repeat(50);
  const a5 = "width:148mm;height:210mm;position:relative;background:#fff;color:#111;overflow:hidden;";
  return {
    "preflight-estouro.html": pagina(
      "estouro",
      card,
      "",
      "<div style=\"width:240px;height:120px;overflow:hidden;font-size:16px;line-height:1.2;" +
        "border:1px solid #000;padding:4px\">" + estouro + "</div>"
    ),
    "preflight-contraste.html": pagina(
      "contraste",
      card,
      "",
      "<p style=\"margin:80px;font-size:16px;color:#999;background:#fff\">" +
        "Texto com contraste insuficiente sobre fundo branco.</p>"
    ),
    "preflight-ppi.html": pagina(
      "ppi",
      a5,
      "",
      "<img src=\"ppi-80x80.png\" alt=\"amostra\" width=\"900\" height=\"900\" " +
        "style=\"display:block;width:900px;height:900px;margin:80px\">"
    ),
    "preflight-safe.html": pagina(
      "safe",
      card,
      "",
      "<p style=\"position:absolute;left:4px;top:4px;margin:0;font-size:16px;color:#111\">" +
        "Texto a quatro pixels da borda do cartao.</p>"
    ),
    "controle.html": pagina(
      "controle",
      card,
      "",
      "<section style=\"margin:120px;padding:80px;font-size:32px;line-height:1.4;color:#111;" +
        "background:#fff\">Cartao de controle, sem defeito provocado.</section>"
    ),
  };
}

function plano(out) {
  const fix = path.join(out, "fixtures");
  const ev = path.join(out, EVID);
  const base = (arq, viewport, shots) => {
    const argv = [
      "npx", "--yes", KIT, "check", path.join(fix, arq),
      "--viewport", viewport, "--json", "--fail-on", "error",
    ];
    if (shots) argv.push("--screenshots", path.join(ev, "screenshots", shots));
    return { argv, caso: shots || "controle" };
  };
  return [
    base("preflight-estouro.html", "card:1080x1350", "estouro"),
    base("preflight-contraste.html", "card:1080x1350", "contraste"),
    base("preflight-safe.html", "card:1080x1350", "safe"),
    base("preflight-ppi.html", "a5:1748x2480", "ppi"),
    base("controle.html", "card:1080x1350", null),
  ];
}

function hashes(dir) {
  const linhas = [];
  const andar = (atual) => {
    const itens = fs.readdirSync(atual, { withFileTypes: true })
      .sort((a, b) => a.name.localeCompare(b.name));
    for (const item of itens) {
      const completo = path.join(atual, item.name);
      if (item.isDirectory()) andar(completo);
      else {
        const rel = path.relative(dir, completo).split(path.sep).join("/");
        if (rel === "sha256sums.txt") continue;
        const h = createHash("sha256").update(fs.readFileSync(completo)).digest("hex");
        linhas.push(h + "  " + rel + "\n");
      }
    }
  };
  andar(dir);
  fs.writeFileSync(path.join(dir, "sha256sums.txt"), linhas.join(""), "utf8");
}

function gravarErro(ev, erro) {
  fs.mkdirSync(ev, { recursive: true });
  const texto = erro && erro.stack ? erro.stack : String(erro);
  fs.writeFileSync(path.join(ev, "erro.json"), JSON.stringify({ erro: texto }, null, 2) + "\n", "utf8");
  process.stderr.write("erro: " + texto + "\n");
}

function executar(out, comandos) {
  const ev = path.join(out, EVID);
  const fix = path.join(out, "fixtures");
  fs.mkdirSync(ev, { recursive: true });
  fs.mkdirSync(fix, { recursive: true });
  for (const [nome, html] of Object.entries(fixtures())) {
    fs.writeFileSync(path.join(fix, nome), html, "utf8");
  }
  fs.writeFileSync(path.join(fix, "ppi-80x80.png"), Buffer.from(PNG80, "base64"));
  const log = [];
  for (const cmd of comandos) {
    const t0 = Date.now();
    const r = spawnSync(cmd.argv[0], cmd.argv.slice(1), {
      cwd: out,
      encoding: "utf8",
      env: { ...process.env, OPEN_DESIGN_OUTPUT_DIR: out },
      maxBuffer: 64 * 1024 * 1024,
      timeout: 600000,
    });
    const ms = Date.now() - t0;
    const erro = r.error ? String(r.error.message) : "";
    const codigo = r.error ? 127 : (typeof r.status === "number" ? r.status : 124);
    fs.writeFileSync(path.join(ev, "check-" + cmd.caso + ".json"), r.stdout || "", "utf8");
    fs.writeFileSync(path.join(ev, "check-" + cmd.caso + ".log"), (r.stderr || "") + (erro ? erro + "\n" : ""), "utf8");
    fs.writeFileSync(path.join(ev, "exit-" + cmd.caso + ".txt"), codigo + "\n", "utf8");
    log.push(JSON.stringify({ argv: cmd.argv, exit: codigo, ms, ...(erro ? { erro } : {}) }) + "\n");
  }
  fs.writeFileSync(path.join(ev, "comandos.log"), log.join(""), "utf8");
  hashes(ev);
}

const opts = argumentos(process.argv.slice(2));
if (opts.help) {
  uso();
} else {
  const comandos = plano(opts.out);
  if (opts.dry) {
    process.stdout.write(JSON.stringify({
      script: path.resolve(process.argv[1] || "preflight-provocado.mjs"),
      evidencia: EVID,
      comandos: comandos.map((c) => c.argv.join(" ")),
    }) + "\n");
  } else {
    try {
      executar(opts.out, comandos);
    } catch (erro) {
      gravarErro(path.join(opts.out, EVID), erro);
      process.exit(1);
    }
  }
}
