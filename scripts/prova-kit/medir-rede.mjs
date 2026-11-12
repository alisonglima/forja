#!/usr/bin/env node
// L-PROVA-KIT-06: telemetria de rede por fase. So executa e registra; o teste
// tests/prova_kit/test_rede.py decide. --dry-run nao inicia processo nem cria arquivo.
import { spawn, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPT = fileURLToPath(import.meta.url);
const EVIDENCIA = 'p5-06-rede';
const WORKSPACE = 'workspace';
const KIT = '@feimacode/open-design-agent-kit@0.4.0';
const BROWSER = '/usr/local/bin/google-chrome-prova';
const HTML = '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>html,body{margin:0;padding:0;background:#fff}[data-od-card]{width:1080px;height:1350px;box-sizing:border-box;padding:96px;background:#fff;color:#111;font-family:Georgia,serif;display:flex;flex-direction:column;justify-content:space-between}h1{font-size:96px;line-height:1.05;margin:0}p{font-size:40px;line-height:1.3;margin:24px 0 0}</style></head><body><section data-od-card><h1>Prova de rede</h1><p>Telemetria e rede: fixture local.</p></section></body></html>\n';
const MANIFESTO = { version: 1, kind: 'html', title: 'Prova de rede', entry: 'rede.html', renderer: 'html', exports: ['html', 'pdf', 'png'], status: 'complete', metadata: { format: 'ig-portrait' } };
function caminhos(cfg) {
  const ev = path.join(cfg.out, EVIDENCIA), workspace = path.join(cfg.out, WORKSPACE);
  const fixtures = path.join(workspace, 'fixtures'), fixture = path.join(fixtures, 'rede.html');
  return { ev, workspace, fixtures, fixture, sidecar: `${fixture}.artifact.json` };
}
function uso() { return 'uso: node scripts/prova-kit/medir-rede.mjs --out DIR [--dry-run] [--help]\n\n  --out DIR    pasta de saida das evidencias (obrigatoria)\n  --dry-run    imprime o plano JSON; nao executa processo nem cria nada\n  --fase NOME  install | static | video (padrao: static)\n  --help       esta ajuda'; }
function erroUso(msg) { process.stderr.write(`erro: ${msg}\n${uso()}\n`); process.exitCode = 2; }
function analisarArgs(argv) {
  let out = null, dry = false, fase = 'static';
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--help' || a === '-h') return { help: true };
    if (a === '--dry-run') { dry = true; continue; }
    if (a === '--out' || a.startsWith('--out=')) {
      if (a === '--out') { if (i + 1 >= argv.length) return erroUso('--out exige DIR'); out = argv[++i]; } else out = a.slice(6);
      continue;
    }
    if (a === '--fase' || a.startsWith('--fase=')) {
      if (a === '--fase') { if (i + 1 >= argv.length) return erroUso('--fase exige valor'); fase = argv[++i]; } else fase = a.slice(7);
      continue;
    }
    return erroUso(`argumento desconhecido: ${a}`);
  }
  if (!out) return erroUso('--out e obrigatorio');
  if (!['install', 'static', 'video'].includes(fase)) return erroUso(`fase invalida: ${fase}`);
  return { out: path.resolve(out), dry, fase };
}
function plano(cfg) {
  const { ev, workspace, fixture, sidecar } = caminhos(cfg);
  const pcap = path.join(ev, `rede-${cfg.fase}.pcap`), entry = path.relative(workspace, fixture);
  return { script: SCRIPT, evidencia: EVIDENCIA, fase: cfg.fase, workspace: path.relative(cfg.out, workspace), sidecars: [path.relative(cfg.out, sidecar)], comandos: [
    'cat /sys/class/net/eth0/statistics/tx_bytes', 'cat /sys/class/net/eth0/statistics/rx_bytes',
    `tcpdump -ni eth0 -w ${pcap}`, 'ss -tunp', `npx --yes ${KIT} check ${entry} --workspace ${workspace} --fail-on error --json`,
    'ss -tunp', `tcpdump -nr ${pcap} -q ip and not host 127.0.0.1`,
    `tcpdump -nr ${pcap} -q ip6 and not host ::1`, `tcpdump -n -t -r ${pcap} -q ip or ip6`,
    `tcpdump -nr ${pcap} -q port 53 -vv`] };
}
function executar(cfg) {
  const { ev, workspace, fixtures, fixture, sidecar } = caminhos(cfg);
  fs.mkdirSync(ev, { recursive: true }); fs.mkdirSync(path.join(workspace, '.open-design'), { recursive: true }); fs.mkdirSync(fixtures, { recursive: true });
  fs.writeFileSync(fixture, HTML, 'utf8'); fs.writeFileSync(sidecar, `${JSON.stringify(MANIFESTO, null, 2)}\n`, 'utf8');
  const log = path.join(ev, 'comandos.log'); fs.writeFileSync(log, '');
  const erros = [], gravar = (n, t) => fs.writeFileSync(path.join(ev, n), t);
  const registrar = (i) => fs.appendFileSync(log, `${JSON.stringify(i)}\n`);
  const dormir = (ms) => new Promise((r) => setTimeout(r, ms));
  function rodar(argv, extra = {}, fatal = true, cwd = workspace) {
    const t0 = Date.now(); let r;
    try { r = spawnSync(argv[0], argv.slice(1), { encoding: 'utf8', cwd, maxBuffer: 64 * 1024 * 1024, env: { ...process.env, ...extra } }); }
    catch (e) { r = { status: 1, stdout: '', stderr: String(e && e.message ? e.message : e), error: e }; }
    const code = typeof r.status === 'number' ? r.status : 1, item = { argv, cwd, code, ms: Date.now() - t0 };
    if (r.error) item.erro = String(r.error.message || r.error);
    if (code !== 0) { item.stderr_tail = String(r.stderr || '').slice(-500); if (fatal) erros.push(`comando falhou (${code}): ${argv.join(' ')}`); }
    registrar(item);
    return { code, stdout: String(r.stdout || ''), stderr: String(r.stderr || '') };
  }
  function iface() {
    for (const n of ['eth0', 'lo']) if (fs.existsSync(`/sys/class/net/${n}/statistics/tx_bytes`)) return n;
    throw new Error('interface de rede nao encontrada (eth0/lo)');
  }
  const bytes = (nome, tipo) => {
    const p = `/sys/class/net/${nome}/statistics/${tipo}_bytes`, v = fs.readFileSync(p, 'utf8').trim();
    if (!/^\d+$/.test(v)) throw new Error(`contador invalido: ${p}`);
    return Number(v);
  };
  return (async () => {
    const nome = iface(), suf = cfg.fase === 'static' ? '' : `-${cfg.fase}`;
    const pcap = path.join(ev, `rede-${cfg.fase}.pcap`); fs.rmSync(pcap, { force: true });
    const tx0 = bytes(nome, 'tx'), rx0 = bytes(nome, 'rx');
    const inicio = new Date().toISOString(), tpIni = Date.now();
    const tp = spawn('tcpdump', ['-ni', nome, '-w', pcap], { cwd: workspace, stdio: ['ignore', 'ignore', 'pipe'] });
    let tpErr = ''; tp.on('error', (e) => { tpErr += String(e.message || e); }); tp.stderr.on('data', (d) => { tpErr += d.toString(); });
    for (let i = 0; i < 30; i += 1) { if (fs.existsSync(pcap) && fs.statSync(pcap).size >= 24) break; await dormir(100); }
    gravar(`ss-antes${suf}.txt`, rodar(['ss', '-tunp']).stdout);
    const kitEnv = {};
    if (fs.existsSync(BROWSER)) kitEnv.OPEN_DESIGN_BROWSER_PATH = BROWSER;
    if (cfg.fase === 'static') kitEnv.npm_config_offline = 'true';
    const kit = rodar(['npx', '--yes', KIT, 'check', path.relative(workspace, fixture), '--workspace', workspace, '--fail-on', 'error', '--json'], kitEnv, false, workspace);
    gravar(`kit-check${suf}.log`, kit.stdout + (kit.stderr ? `\n[stderr]\n${kit.stderr}` : ''));
    await new Promise((resolve) => {
      let fim = false;
      const fechar = () => { if (fim) return; fim = true; clearTimeout(timer); resolve(); };
      const timer = setTimeout(fechar, 5000); timer.unref?.();
      if (tp.exitCode !== null) { fechar(); return; }
      tp.once('close', fechar); try { tp.kill('SIGINT'); } catch { fechar(); }
    });
    registrar({ argv: ['tcpdump', '-ni', nome, '-w', pcap], code: tp.exitCode ?? 0, sinal: tp.signalCode || null, ms: Date.now() - tpIni, stderr_tail: tpErr.slice(-500) });
    if (tp.exitCode && tp.exitCode !== 0) erros.push(`tcpdump saiu com ${tp.exitCode}`);
    const tx1 = bytes(nome, 'tx'), rx1 = bytes(nome, 'rx');
    gravar(`rede-${cfg.fase}.json`, `${JSON.stringify({ fase: cfg.fase, tx: Math.max(0, tx1 - tx0), rx: Math.max(0, rx1 - rx0), iface: nome, inicio, fim: new Date().toISOString(), host: os.hostname() })}\n`);
    gravar(`ss-depois${suf}.txt`, rodar(['ss', '-tunp']).stdout);
    const okPcap = fs.existsSync(pcap) && fs.statSync(pcap).size >= 24;
    if (!okPcap) erros.push('pcap ausente ou truncado');
    const fora = [];
    if (okPcap) for (const proto of ['ip and not host 127.0.0.1', 'ip6 and not host ::1']) {
      const r = rodar(['tcpdump', '-nr', pcap, '-q', proto]); if (r.stdout.trim()) fora.push(r.stdout.trim());
    }
    gravar(`fora-loopback${suf}.txt`, fora.length ? `${fora.join('\n')}\n` : '');
    const dst = new Set();
    if (okPcap) for (const linha of rodar(['tcpdump', '-n', '-t', '-r', pcap, '-q', 'ip or ip6']).stdout.split('\n')) {
      const i = linha.indexOf(' > '); if (i < 0) continue;
      const token = (linha.slice(i + 3).trim().split(/\s+/)[0] || '').replace(/:$/, ''); if (token) dst.add(token);
    }
    gravar(`destinos${suf}.txt`, dst.size ? `${[...dst].sort().join('\n')}\n` : '');
    gravar(`dns${suf}.txt`, okPcap ? rodar(['tcpdump', '-nr', pcap, '-q', 'port 53', '-vv']).stdout : '');
    const sensivel = /(?:^|_)(?:TOKEN|SECRET|SECRETS|PASSWORD|PASSWD|APIKEY|API_KEY|ACCESS_KEY|PRIVATE_KEY|CREDENTIAL|CREDENTIALS|AUTH)$/;
    const permitidas = ['PATH', 'HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL', 'TERM', 'NODE_VERSION', 'npm_config_offline', 'OPEN_DESIGN_BROWSER_PATH'];
    gravar('env.txt', `${permitidas.filter((k) => process.env[k] !== undefined && !sensivel.test(k.toUpperCase())).sort().map((k) => `${k}=${process.env[k]}`).join('\n')}\n`);
    if (erros.length) gravar('erro.json', `${JSON.stringify({ fase: cfg.fase, erros }, null, 2)}\n`);
    const somas = [];
    for (const n of fs.readdirSync(ev).sort()) {
      if (n === 'sha256sums.txt') continue;
      const p = path.join(ev, n); if (!fs.statSync(p).isFile()) continue;
      somas.push(`${createHash('sha256').update(fs.readFileSync(p)).digest('hex')}  ${n}`);
    }
    gravar('sha256sums.txt', `${somas.join('\n')}\n`);
    if (erros.length) { process.stderr.write(`erro: ${erros.length} falha(s); ver ${path.join(ev, 'erro.json')}\n`); process.exitCode = 1; }
  })();
}
function principal() {
  const cfg = analisarArgs(process.argv.slice(2));
  if (!cfg) return;
  if (cfg.help) { process.stdout.write(`${uso()}\n`); return; }
  if (cfg.dry) { process.stdout.write(`${JSON.stringify(plano(cfg))}\n`); return; }
  if (process.platform !== 'linux') {
    process.stderr.write('erro: modo real exige Linux (LXC descartavel); use --dry-run nesta maquina\n');
    process.exitCode = 1; return;
  }
  Promise.resolve().then(() => executar(cfg)).catch((e) => {
    const ev = path.join(cfg.out, EVIDENCIA), msg = e && e.message ? e.message : String(e);
    try { fs.mkdirSync(ev, { recursive: true }); fs.writeFileSync(path.join(ev, 'erro.json'), `${JSON.stringify({ fase: cfg.fase, erros: [msg] }, null, 2)}\n`); } catch { /* registro best-effort */ }
    process.stderr.write(`erro: ${msg}\n`);
    process.exitCode = 1;
  });
}
principal();
