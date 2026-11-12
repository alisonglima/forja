#!/usr/bin/env node
// L-PROVA-KIT-02: exporta A5, A4 e folder multipagina em PDF e registra a
// evidencia p5-02-pdf. So executa e grava; quem julga e tests/prova_kit/.
import { createHash } from 'node:crypto';
import { appendFileSync, existsSync, mkdirSync, readFileSync, readdirSync,
  renameSync, rmSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const KIT = ['npx', '--yes', '@feimacode/open-design-agent-kit@0.4.0'];
const EVIDENCIA = 'p5-02-pdf';
const PECAS = [['a5', 'a5'], ['a4', 'a4'], ['folder', 'a5']];
const USO = `uso: node scripts/prova-kit/export-pdf.mjs --out DIR [--dry-run] [--help]
Exporta fixtures A5, A4 e folder A5 multipagina em PDF e grava a evidencia
em DIR/${EVIDENCIA}/, com pdfinfo, pdffonts, pdftotext, pdfimages, pdftocairo
e qpdf. Tambem grava comandos.log, sha256sums.txt e prova.json.
  --out DIR   diretorio de saida (obrigatorio)
  --dry-run   imprime o plano JSON sem executar nem criar nada
  --help      mostra esta ajuda
`;
let LOG = '';
let FALHA = null;

function erro(msg) { process.stderr.write(`erro: ${msg}\n`); process.exit(2); }

function citar(s) { return /^[A-Za-z0-9_./:=@+-]+$/.test(s) ? s : `'${s.replace(/'/g, "'\\''")}'`; }

function formatar(argv, env) {
  const prefixo = env ? Object.entries(env).map(([k, v]) => `${k}=${citar(v)}`).join(' ') + ' ' : '';
  return prefixo + argv.map(citar).join(' ');
}

function planejar(out) {
  const ev = path.join(out, EVIDENCIA), fix = path.join(out, 'fixtures'), tmp = path.join(out, '.tmp-p5-02'), cmds = [];
  for (const [base, preset] of PECAS) {
    cmds.push({ argv: [...KIT, 'export', path.join(fix, `${base}.html`), '--format', 'pdf', '--preset', preset, '--bleed', '0'], env: { OPEN_DESIGN_OUTPUT_DIR: ev, OPEN_DESIGN_BROWSER_PATH: '/usr/local/bin/google-chrome-prova' }, log: path.join(ev, `${base}.kit.log`), kit: base });
  }
  for (const [base] of PECAS) {
    const pdf = path.join(ev, `${base}.pdf`);
    cmds.push({ argv: base === 'folder' ? ['pdfinfo', '-f', '1', '-l', '4', pdf] : ['pdfinfo', pdf], saida: path.join(ev, `${base}.pdfinfo.txt`) });
    cmds.push({ argv: ['pdffonts', pdf], saida: path.join(ev, `${base}.pdffonts.txt`) });
    cmds.push({ argv: ['pdftotext', '-layout', pdf, '-'], saida: path.join(ev, `${base}.pdftotext.txt`) });
    cmds.push({ argv: ['pdfimages', '-list', pdf], saida: path.join(ev, `${base}.pdfimages.txt`) });
    cmds.push({ argv: ['pdftocairo', '-png', '-r', '72', pdf, path.join(ev, `${base}-page`)] });
    cmds.push({ argv: ['qpdf', '--qdf', pdf, path.join(tmp, `${base}.qdf.pdf`)], tolerante: true, qdf: base });
  }
  for (let p = 1; p <= 4; p += 1) cmds.push({ argv: ['pdftotext', '-f', String(p), '-l', String(p), '-layout', path.join(ev, 'folder.pdf'), '-'], anexar: path.join(ev, 'folder-paginas.txt'), separar: true });
  return { ev, fix, tmp, cmds };
}

function cartao(rotulo, w, h) {
  const css = `@page{size:${w}mm ${h}mm;margin:0}html,body{margin:0;padding:0}` + `[data-od-card]{width:${w}mm;height:${h}mm;box-sizing:border-box;padding:14mm;overflow:hidden;background:#f7f4ee;color:#1d2a36;font-family:"DejaVu Sans","Noto Sans",sans-serif}` + `.faixa{height:6mm;margin-bottom:8mm;background:#2f6f6a}h1{margin:0 0 6mm;font-size:22pt}p{margin:0 0 4mm;font-size:11pt;line-height:1.5}`;
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Prova ${rotulo}</title><style>${css}</style></head><body><section data-od-card><div class="faixa"></div><h1>${rotulo}: Ação e Coração</h1><p>Conceição apresenta o programa com texto vetorial, acentos e fontes embutidas.</p><p>Página única para conferir o tamanho nominal do papel ${rotulo}.</p></section></body></html>\n`;
}

const PAGINAS = [
  ['Capa', 'Ação, Conceição e Coração', 'Folder de quatro páginas A5 para a prova K.2.'],
  ['Boas-vindas', 'Conceição recebe você', 'Texto selecionável na segunda página do folder.'],
  ['Programação', 'Ação cultural e oficinas', 'Agenda com títulos e horários em texto vetorial.'],
  ['Contato', 'Coração da comunidade', 'Endereço e canais de contato na última página.'],
];

function folder() {
  const css = `@page{size:148mm 210mm;margin:0}html,body{margin:0;padding:0}` + `.pagina{width:148mm;height:210mm;box-sizing:border-box;padding:14mm;overflow:hidden;background:#f7f4ee;color:#1d2a36;font-family:"DejaVu Sans","Noto Sans",sans-serif;break-after:page;page-break-after:always}` + `.pagina:last-child{break-after:auto;page-break-after:auto}.faixa{height:6mm;margin-bottom:8mm;background:#2f6f6a}h1{margin:0 0 6mm;font-size:20pt}p{margin:0 0 4mm;font-size:10.5pt;line-height:1.5}`;
  const secoes = PAGINAS.map(([t, d, p]) => `<section data-od-card class="pagina"><div class="faixa"></div><h1>${t}</h1><p class="destaque">${d}</p><p>${p}</p></section>`).join('\n');
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Folder A5</title><style>${css}</style></head><body>\n${secoes}\n</body></html>\n`;
}

function escreverFixtures(fix) {
  writeFileSync(path.join(fix, 'a5.html'), cartao('A5', 148, 210));
  writeFileSync(path.join(fix, 'a4.html'), cartao('A4', 210, 297));
  writeFileSync(path.join(fix, 'folder.html'), folder());
}

function pdfsEm(dir) {
  const achados = [];
  const andar = (d) => { for (const e of readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) andar(p); else if (e.name.toLowerCase().endsWith('.pdf')) achados.push(p); } };
  andar(dir);
  return achados;
}

function limpar(ev) {
  for (const [base] of PECAS) {
    for (const suf of ['.pdf', '.pdfinfo.txt', '.pdffonts.txt', '.pdftotext.txt', '.pdfimages.txt', '.kit.log', '.qpdf.txt']) rmSync(path.join(ev, base + suf), { force: true });
    for (const nome of readdirSync(ev)) if (nome.startsWith(`${base}-page-`) && nome.endsWith('.png')) rmSync(path.join(ev, nome), { force: true });
  }
  for (const nome of ['folder-paginas.txt', 'prova.json', 'sha256sums.txt', 'erro.json', 'comandos.log']) rmSync(path.join(ev, nome), { force: true });
}

function rodar(c) {
  const t0 = process.hrtime.bigint();
  const r = spawnSync(c.argv[0], c.argv.slice(1), {
    cwd: path.dirname(LOG), encoding: 'utf8', maxBuffer: 64 * 1024 * 1024,
    env: { ...process.env, ...(c.env || {}) },
  });
  const dur = Number(process.hrtime.bigint() - t0) / 1e6;
  const code = r.error ? 127 : (typeof r.status === 'number' ? r.status : 1);
  const out = r.stdout || '';
  const err = r.stderr || (r.error ? r.error.message : '');
  appendFileSync(LOG, JSON.stringify({ argv: c.argv, exit_code: code,
    duracao_ms: Number(dur.toFixed(3)) }) + '\n');
  if (c.saida) writeFileSync(c.saida, out);
  if (c.anexar) {
    appendFileSync(c.anexar, out);
    if (c.separar && out && !out.endsWith('\f')) appendFileSync(c.anexar, '\f');
  }
  if (c.log) {
    writeFileSync(c.log, `$ ${formatar(c.argv, c.env)}\nexit=${code}\n--- stdout ---\n`
      + `${out}\n--- stderr ---\n${err}\n`);
  }
  if (code !== 0 && !c.tolerante && !FALHA) {
    FALHA = { exit_code: code, argv: c.argv, stderr: err.slice(0, 4000) };
  }
  return { code, out, err };
}

function garantirPdf(ev, base, antes) {
  const alvo = path.join(ev, `${base}.pdf`);
  if (existsSync(alvo)) return;
  const novos = pdfsEm(ev).filter((p) => !antes.has(p));
  if (novos.length) {
    novos.sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs);
    renameSync(novos[0], alvo);
  } else if (!FALHA) {
    FALHA = { exit_code: 1, argv: [...KIT, 'export', `${base}.html`],
      stderr: `kit nao gerou ${base}.pdf em ${ev}` };
  }
}

function resumoQpdf(base, r, ev, tmp) {
  const qdf = path.join(tmp, `${base}.qdf.pdf`);
  let txt = `qpdf_exit=${r.code}\n`;
  if (existsSync(qdf)) {
    const s = readFileSync(qdf, 'latin1');
    txt += `DeviceRGB=${(s.match(/\/DeviceRGB/g) || []).length}\n`;
    txt += `rg=${(s.match(/\brg\b/g) || []).length}\n`;
    txt += `RG=${(s.match(/\bRG\b/g) || []).length}\n`;
  } else txt += 'qdf ausente\n';
  writeFileSync(path.join(ev, `${base}.qpdf.txt`), txt);
  rmSync(qdf, { force: true });
}

function sha256(p) { return createHash('sha256').update(readFileSync(p)).digest('hex'); }

function artefatos(ev) {
  return readdirSync(ev, { withFileTypes: true }).filter((e) => e.isFile())
    .map((e) => e.name).filter((n) => n !== 'sha256sums.txt' && n !== 'prova.json').sort();
}

function main() {
  const argv = process.argv.slice(2);
  let out = null;
  let dry = false;
  let help = false;
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--help' || a === '-h') help = true;
    else if (a === '--dry-run') dry = true;
    else if (a === '--out') {
      if (i + 1 >= argv.length || argv[i + 1].startsWith('--')) erro('--out exige um diretorio');
      out = argv[i + 1];
      i += 1;
    } else erro(`argumento desconhecido: ${a}`);
  }
  if (help) { process.stdout.write(USO); return; }
  if (!out) { process.stderr.write(`erro: --out e obrigatorio\n${USO}`); process.exit(2); }

  const { ev, fix, tmp, cmds } = planejar(path.resolve(out));
  if (dry) {
    process.stdout.write(JSON.stringify({ script: path.resolve(process.argv[1]),
      evidencia: EVIDENCIA, comandos: cmds.map((c) => formatar(c.argv, c.env)) }) + '\n');
    return;
  }

  mkdirSync(ev, { recursive: true });
  mkdirSync(fix, { recursive: true });
  mkdirSync(tmp, { recursive: true });
  LOG = path.join(ev, 'comandos.log');
  limpar(ev);
  escreverFixtures(fix);
  try {
    for (const c of cmds) {
      if (c.kit) {
        const antes = new Set(pdfsEm(ev));
        rodar(c);
        garantirPdf(ev, c.kit, antes);
      } else {
        const r = rodar(c);
        if (c.qdf) resumoQpdf(c.qdf, r, ev, tmp);
      }
    }
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
  if (FALHA) {
    writeFileSync(path.join(ev, 'erro.json'), JSON.stringify(FALHA, null, 2) + '\n');
  }
  const nomes = artefatos(ev);
  const hashes = Object.fromEntries(nomes.map((n) => [n, sha256(path.join(ev, n))]));
  writeFileSync(path.join(ev, 'sha256sums.txt'),
    nomes.map((n) => `${hashes[n]}  ${n}`).join('\n') + '\n');
  writeFileSync(path.join(ev, 'prova.json'), JSON.stringify({ schema: 'prova-kit/pdf-rgb/v1',
    evidencia: EVIDENCIA, exit_code: FALHA ? 1 : 0, gerado_em: new Date().toISOString(),
    sha256: hashes }, null, 2) + '\n');
  if (FALHA) process.stderr.write(`erro: ${FALHA.stderr || FALHA.argv.join(' ')}\n`);
  process.exit(FALHA ? 1 : 0);
}

main();
