#!/usr/bin/env node
// Prova K.2(e): abertura de 5 s, HyperFrames vs Remotion.
// Este script so executa e registra; quem decide e tests/prova_kit/test_video*.py.
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  appendFileSync,
  copyFileSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";

const SCRIPT = resolve(process.argv[1]);
const EV = "p5-05-video";
const MOTORES = ["hf", "remotion"];
const USO = `uso: node ${SCRIPT} --out DIR [--dry-run] [--help]`;
const args = process.argv.slice(2);

function valor(nome) {
  const i = args.indexOf(nome);
  if (i >= 0 && i + 1 < args.length && !args[i + 1].startsWith("--")) return args[i + 1];
  const par = args.find((a) => a.startsWith(`${nome}=`));
  return par ? par.slice(nome.length + 1) : null;
}

if (args.includes("--help")) {
  console.log(USO);
  process.exit(0);
}
const outArg = valor("--out");
if (!outArg) {
  console.error(`erro: --out DIR e obrigatorio\n${USO}`);
  process.exit(2);
}
const dryRun = args.includes("--dry-run");
const out = resolve(outArg);

const p = {
  out,
  video: join(out, EV),
  fixtures: join(out, "fixtures"),
  hf: join(out, "fixtures", "hf-abertura"),
  public: join(out, "fixtures", "public"),
  fundo: join(out, "fixtures", "public", "fundo.png"),
  props: join(out, "fixtures", "remotion-props.json"),
  hfMp4: join(out, EV, "hf.mp4"),
  remMp4: join(out, EV, "remotion.mp4"),
  hfTime: join(out, EV, "hf.time"),
  remTime: join(out, EV, "remotion.time"),
  hfLog: join(out, EV, "hf.log"),
  remLog: join(out, EV, "remotion.log"),
  hfProbe: join(out, EV, "hf.ffprobe.json"),
  remProbe: join(out, EV, "remotion.ffprobe.json"),
  ssim: join(out, EV, "ssim.txt"),
  comandos: join(out, EV, "comandos.log"),
  raiz: resolve(dirname(SCRIPT), "..", ".."),
  remDir: process.env.REMOTION_DIR || resolve(dirname(SCRIPT), "..", "..", "remotion-template"),
};

const cmdFundo = () => [
  "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
  "-i", "color=c=0x0b1020:s=1080x1920:d=1", "-frames:v", "1", p.fundo,
];
const cmdKit = () => [
  "npx", "--yes", "@feimacode/open-design-agent-kit@0.4.0", "render-video",
  p.hf, "--output", p.hfMp4, "--quality", "high",
];
const cmdRem = () => [
  "./node_modules/.bin/remotion", "render", "src/index.jsx", "Storyboard",
  p.remMp4, "--props", p.props, "--public-dir", p.public,
];
const cmdProbe = (mp4) => [
  "ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", mp4,
];
const cmdFrames = (mp4, arq) => [
  "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", mp4, "-f", "framemd5", arq,
];
const cmdSsim = () => [
  "ffmpeg", "-hide_banner", "-i", p.hfMp4, "-i", p.remMp4,
  "-lavfi", "[0:v][1:v]ssim", "-f", "null", "-",
];
const cmdStill = (mp4, t, arq) => [
  "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", t, "-i", mp4,
  "-frames:v", "1", arq,
];
const cmd360 = (mp4, arq) => [
  "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", mp4,
  "-vf", "scale=360:-2", "-frames:v", "1", arq,
];
const cmdTime = (time, cmd) => ["/usr/bin/time", "-v", "-o", time, ...cmd];

function previstos() {
  const lista = [
    cmdTime(p.hfTime, cmdKit()).join(" "),
    cmdTime(p.remTime, cmdRem()).join(" "),
    cmdProbe(p.hfMp4).join(" "),
    cmdProbe(p.remMp4).join(" "),
    cmdSsim().join(" "),
  ];
  for (const motor of MOTORES) {
    const mp4 = motor === "hf" ? p.hfMp4 : p.remMp4;
    for (const rodada of [1, 2]) {
      lista.push(cmdFrames(mp4, join(p.video, `${motor}.${rodada}.framemd5`)).join(" "));
    }
    for (const t of ["0.0", "2.5", "4.9"]) {
      lista.push(cmdStill(mp4, t, join(p.video, `${motor}.still-${t}.png`)).join(" "));
    }
    lista.push(cmd360(mp4, join(p.video, `${motor}.360.png`)).join(" "));
  }
  return lista;
}

if (dryRun) {
  console.log(JSON.stringify({
    script: SCRIPT,
    evidencia: EV,
    workspace: "workspace",
    sidecars: [],
    comandos: previstos(),
  }, null, 2));
  process.exit(0);
}

const HTML = `<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>abertura 5s</title>
<link rel="stylesheet" href="./abertura.css">
</head>
<body>
<main id="palco">
  <img id="fundo" src="./fundo.png" alt="">
  <p id="kicker">PROVA K.2(e)</p>
  <h1 id="titulo">ABERTURA 5s</h1>
  <p id="linha">HyperFrames vs Remotion</p>
</main>
<script src="./abertura.js"></script>
</body>
</html>
`;
const CSS = `html,body{margin:0;padding:0;background:#0b1020;overflow:hidden}
#palco{position:relative;width:1080px;height:1920px;overflow:hidden;font-family:"Liberation Sans",Arial,sans-serif;color:#f6f1e8}
#fundo{position:absolute;inset:0;width:1080px;height:1920px;object-fit:cover}
#kicker{position:absolute;left:96px;top:560px;margin:0;font-size:34px;letter-spacing:6px;color:#c24b2a;font-weight:700}
#titulo{position:absolute;left:96px;top:680px;margin:0;font-size:132px;line-height:1.02;font-weight:700}
#linha{position:absolute;left:96px;top:900px;margin:0;font-size:52px;line-height:1.2;color:#d8d2c6}
#kicker{animation:entra 0.8s ease-out both}
#titulo{animation:entra 1.2s ease-out 0.2s both}
#linha{animation:entra 1s ease-out 0.5s both}
@keyframes entra{from{opacity:0;transform:translateY(90px)}to{opacity:1;transform:translateY(0)}}
`;
const JS = `(() => {
  const alvo = document.querySelector("#titulo");
  if (window.gsap) {
    window.gsap.from("#kicker", { opacity: 0, duration: 0.8, delay: 0.2 });
    window.gsap.from(alvo, { y: 90, opacity: 0, duration: 1.2, ease: "power3.out" });
    window.gsap.from("#linha", { opacity: 0, duration: 1, delay: 0.6 });
  }
})();
`;
const props = {
  durationS: 5,
  fps: 30,
  width: 1080,
  height: 1920,
  fontSize: 32,
  timeline: {
    fps: 30,
    total_s: 5,
    scenes: [{
      id: "abertura",
      start: 0,
      end: 5,
      layers: [
        { type: "card", asset: "fundo.png", full_frame: true, start: 0, end: 5 },
        { type: "overlay", preset: "title", text: "ABERTURA 5s",
          subtext: "HyperFrames vs Remotion", start: 0, end: 5, style: { font_size: 96 } },
      ],
    }],
  },
  subs: [],
  lowerThirds: [],
  brand: { primary: "#c24b2a", ink: "#1a1714", paper: "#f6f1e8",
    accent: "#c24b2a", font: "Liberation Sans", safe_margin: 48 },
};

for (const d of [p.video, p.fixtures, p.hf, p.public]) mkdirSync(d, { recursive: true });
writeFileSync(join(p.hf, "index.html"), HTML, "utf-8");
writeFileSync(join(p.hf, "abertura.css"), CSS, "utf-8");
writeFileSync(join(p.hf, "abertura.js"), JS, "utf-8");
writeFileSync(p.props, JSON.stringify(props, null, 2) + "\n", "utf-8");

const falhas = [];
function rodar(argvCmd, opts = {}) {
  const cwd = opts.cwd || p.raiz;
  const inicio = Date.now();
  const r = spawnSync(argvCmd[0], argvCmd.slice(1), {
    cwd,
    env: opts.env || process.env,
    encoding: "utf-8",
    maxBuffer: 128 * 1024 * 1024,
  });
  const reg = {
    argv: argvCmd,
    cwd,
    exit: r.status,
    signal: r.signal || null,
    duration_ms: Date.now() - inicio,
  };
  if (r.error) reg.error = String(r.error.message);
  appendFileSync(p.comandos, JSON.stringify(reg) + "\n", "utf-8");
  if (r.status !== 0) falhas.push(reg);
  return r;
}

rodar(cmdFundo());
copyFileSync(p.fundo, join(p.hf, "fundo.png"));
copyFileSync(p.fundo, join(p.public, "fundo.png"));

const envKit = { ...process.env, npm_config_offline: "false" };
const saiuHf = rodar(cmdTime(p.hfTime, cmdKit()), { env: envKit });
writeFileSync(p.hfLog, `${saiuHf.stdout || ""}${saiuHf.stderr || ""}`, "utf-8");
const saiuRem = rodar(cmdTime(p.remTime, cmdRem()), { cwd: p.remDir });
writeFileSync(p.remLog, `${saiuRem.stdout || ""}${saiuRem.stderr || ""}`, "utf-8");

for (const motor of MOTORES) {
  const mp4 = motor === "hf" ? p.hfMp4 : p.remMp4;
  const probe = motor === "hf" ? p.hfProbe : p.remProbe;
  const r = rodar(cmdProbe(mp4));
  writeFileSync(probe, r.stdout || "", "utf-8");
  for (const rodada of [1, 2]) {
    rodar(cmdFrames(mp4, join(p.video, `${motor}.${rodada}.framemd5`)));
  }
  for (const t of ["0.0", "2.5", "4.9"]) {
    rodar(cmdStill(mp4, t, join(p.video, `${motor}.still-${t}.png`)));
  }
  rodar(cmd360(mp4, join(p.video, `${motor}.360.png`)));
}
const ssim = rodar(cmdSsim());
writeFileSync(p.ssim, `${ssim.stderr || ""}${ssim.stdout || ""}`, "utf-8");

if (falhas.length) {
  writeFileSync(join(p.video, "erro.json"), JSON.stringify({ falhas }, null, 2) + "\n", "utf-8");
}

function sha256(arquivo) {
  return createHash("sha256").update(readFileSync(arquivo)).digest("hex");
}
const nomes = readdirSync(p.video)
  .filter((n) => n !== "sha256sums.txt" && statSync(join(p.video, n)).isFile())
  .sort();
writeFileSync(
  join(p.video, "sha256sums.txt"),
  nomes.map((n) => `${sha256(join(p.video, n))}  ${n}`).join("\n") + "\n",
  "utf-8",
);

console.log(JSON.stringify({ evidencia: p.video, falhas: falhas.length }));
process.exitCode = falhas.length ? 1 : 0;
