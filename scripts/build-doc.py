#!/usr/bin/env python3
"""Gera o guia web do kit forja: um unico HTML offline, deterministico.

Uso:
    python -I scripts/build-doc.py --out docs/index.html
    python -I scripts/build-doc.py --out /tmp/guia.html --prompts prompts

O arquivo nao referencia nada externo (sem fontes, CSS, JS ou imagens de
terceiros). Os prompts de ``prompts/*.md`` entram literalmente no HTML
(escapados) e cada um ganha um botao de copiar.
"""
from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Titulo e "quando usar" de cada prompt. A chave e o nome do arquivo sem .md.
# Um prompt novo (sem entrada aqui) ainda entra na pagina, com titulo derivado.
PROMPT_INFO = {
    "00-instalar-docker": (
        "Instalar o Docker",
        "Quando a maquina ainda nao tem Docker ou o Docker nao esta funcionando.",
    ),
    "01-preparar-kit": (
        "Preparar o kit",
        "Na primeira vez: cria o .env, coloca a chave e passa no doctor.",
    ),
    "02-instalar-skill-no-seu-agente": (
        "Instalar a skill no seu agente",
        "Logo depois do doctor: ensina o seu agente a operar a forja sozinho.",
    ),
    "03-dublagem-transcrever-e-entender": (
        "Dublagem: transcrever e entender",
        "Primeiro passo de um video para dublar: cria o projeto e transcreve.",
    ),
    "04-dublagem-quem-fala": (
        "Dublagem: quem fala",
        "Depois de transcrever: quadros, falantes e janelas de tarja.",
    ),
    "05-dublagem-adaptar-roteiro": (
        "Dublagem: adaptar o roteiro",
        "Transforma a transcricao em cues em portugues que cabem no tempo.",
    ),
    "06-dublagem-elenco-e-vozes": (
        "Dublagem: elenco e vozes",
        "Escolhe uma voz por pessoa e salva os WAVs em voices/ (ou usa um provedor por API, se configurado).",
    ),
    "07-dublagem-gerar-e-revisar": (
        "Dublagem: gerar e revisar",
        "Roda o pipeline completo, confere o QA e mostra o video.",
    ),
    "08-video-por-cenas": (
        "Video por cenas",
        "Para criar um video do zero, sem video de origem, a partir de um briefing.",
    ),
    "09-evoluir-a-forja": (
        "Evoluir a forja",
        "Quando voce quer um provedor ou um workflow novo, sem quebrar o resto.",
    ),
    "10-navegador-modo-simples": (
        "Navegador: modo simples",
        "Modo conta: Chrome visivel em outra area de trabalho, controlado por CDP, para logar com a sua conta.",
    ),
    "11-navegador-em-container": (
        "Navegador: dentro do container",
        "Modo conta: Chromium no Docker, visivel numa aba do seu navegador, para logar com a sua conta.",
    ),
    "12-consentimento-e-aviso": (
        "Consentimento e aviso de IA",
        "Antes de publicar: direitos, consentimento e o aviso de voz sintetizada.",
    ),
    "13-resolver-problemas": (
        "Resolver problemas",
        "Quando algo falha: diagnostico na ordem certa, sem adivinhar a causa.",
    ),
}


def _fallback_title(slug: str) -> str:
    """Deriva um titulo legivel de um nome de arquivo desconhecido."""
    words = slug.split("-", 1)[-1].replace("-", " ").replace("_", " ").strip()
    return words[:1].upper() + words[1:] if words else slug


def _prompt_cards(files: list[Path]) -> str:
    cards = []
    for path in files:
        slug = path.stem
        number = slug.split("-", 1)[0] if "-" in slug else ""
        title, when = PROMPT_INFO.get(slug, (_fallback_title(slug), "Prompt do kit."))
        # O teste do contrato compara exatamente html.escape(texto.strip(), quote=False).
        text = html.escape(path.read_text(encoding="utf-8").strip(), quote=False)
        cards.append(
            '<article class="prompt" id="p-%(slug)s">\n'
            '  <div class="prompt-head">\n'
            "    <div>\n"
            '      <p class="prompt-id">%(number)s</p>\n'
            "      <h3>%(title)s</h3>\n"
            '      <p class="when">Quando usar: %(when)s</p>\n'
            "    </div>\n"
            '    <button class="copy" type="button" data-copy="%(slug)s" '
            'aria-label="Copiar o prompt %(title)s">Copiar</button>\n'
            "  </div>\n"
            '  <pre data-prompt="%(slug)s">%(text)s</pre>\n'
            "</article>"
            % {
                "slug": html.escape(slug, quote=True),
                "number": html.escape(number),
                "title": html.escape(title),
                "when": html.escape(when),
                "text": text,
            }
        )
    return "\n".join(cards)


CSS = r"""
*, *::before, *::after { box-sizing: border-box; }
html { color-scheme: light dark; scroll-behavior: smooth; -webkit-text-size-adjust: 100%; }
:root {
  --bg: #faf5ec;
  --bg-2: #f3ebdd;
  --surface: #fffdf8;
  --surface-2: #f7f0e4;
  --ink: #241f1a;
  --muted: #6d6459;
  --line: #e2d6c4;
  --line-strong: #cdbda6;
  --accent: #a94e27;
  --accent-ink: #fff8f2;
  --accent-soft: #f4ddcf;
  --ok: #2f6a4c;
  --ok-soft: #dcecdf;
  --warn: #8a5a12;
  --code-bg: #241f1a;
  --code-ink: #f6eee2;
  --shadow: 0 18px 40px rgba(60, 42, 24, .10);
  --radius: 18px;
  --sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --serif: "Iowan Old Style", "Palatino Linotype", Palatino, "Book Antiqua", Georgia, serif;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #15120f;
    --bg-2: #1b1713;
    --surface: #211c17;
    --surface-2: #2a241d;
    --ink: #f3eadc;
    --muted: #b8ab99;
    --line: #3a3229;
    --line-strong: #4d4236;
    --accent: #e08a5f;
    --accent-ink: #21150e;
    --accent-soft: #3b291e;
    --ok: #8bc7a4;
    --ok-soft: #1e3327;
    --warn: #e0b66a;
    --code-bg: #0e0c0a;
    --code-ink: #f3eadc;
    --shadow: 0 18px 40px rgba(0, 0, 0, .35);
  }
}
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: var(--sans);
  font-size: 17px;
  line-height: 1.62;
  overflow-wrap: break-word;
  -webkit-font-smoothing: antialiased;
}
h1, h2, h3 { font-family: var(--serif); font-weight: 600; letter-spacing: -0.015em; }
p { margin: 0 0 14px; }
a { color: var(--accent); }
a:focus-visible, button:focus-visible, summary:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 3px;
}
code {
  font-family: var(--mono);
  font-size: .88em;
  background: var(--surface-2);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 1px 5px;
  overflow-wrap: anywhere;
}
pre code { background: none; border: 0; padding: 0; font-size: 1em; }
.wrap { width: min(1120px, calc(100% - 40px)); margin: 0 auto; }
.skip {
  position: absolute; left: -9999px; top: 0; background: var(--accent);
  color: var(--accent-ink); padding: 10px 14px; z-index: 100; border-radius: 0 0 10px 0;
}
.skip:focus { left: 0; }

/* barra */
.top {
  position: sticky; top: 0; z-index: 30;
  background: var(--bg);
  border-bottom: 1px solid var(--line);
}
.bar { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 13px 0; }
.brand {
  display: inline-flex; align-items: center; gap: 10px;
  font-family: var(--serif); font-size: 22px; color: var(--ink); text-decoration: none;
}
.mark {
  width: 32px; height: 32px; border-radius: 10px; display: grid; place-items: center;
  background: var(--accent); color: var(--accent-ink);
  font-family: var(--serif); font-size: 21px; line-height: 1;
}
.top nav ul { display: flex; flex-wrap: wrap; gap: 4px 16px; list-style: none; margin: 0; padding: 0; }
.top nav a { color: var(--muted); text-decoration: none; font-size: 14px; font-weight: 500; }
.top nav a:hover { color: var(--accent); }

/* hero */
.hero {
  padding: 66px 0 50px;
  background:
    radial-gradient(820px 360px at 8% -12%, var(--accent-soft), transparent 72%),
    radial-gradient(620px 300px at 96% 118%, var(--bg-2), transparent 70%);
  border-bottom: 1px solid var(--line);
}
.hero-grid { display: grid; grid-template-columns: minmax(0, 1.22fr) minmax(0, .88fr); gap: 46px; align-items: center; }
.eyebrow {
  margin: 0 0 14px; font-size: 12.5px; font-weight: 700; letter-spacing: .13em;
  text-transform: uppercase; color: var(--accent);
}
h1 { font-size: clamp(36px, 4.8vw, 56px); line-height: 1.05; margin: 0 0 18px; text-wrap: balance; }
h1 em { font-style: italic; color: var(--accent); }
.lede { font-size: 19px; color: var(--muted); max-width: 56ch; margin: 0 0 26px; }
.actions { display: flex; flex-wrap: wrap; gap: 11px; }
.btn {
  display: inline-flex; align-items: center; justify-content: center;
  min-height: 44px; padding: 11px 19px; border-radius: 999px;
  border: 1px solid var(--line-strong); color: var(--ink);
  text-decoration: none; font-size: 15px; font-weight: 650; background: var(--surface);
}
.btn:hover { border-color: var(--accent); color: var(--accent); }
.btn.primary { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }
.btn.primary:hover { filter: brightness(1.06); color: var(--accent-ink); }
.chips { display: flex; flex-wrap: wrap; gap: 8px; list-style: none; margin: 26px 0 0; padding: 0; }
.chips li {
  font-size: 13px; color: var(--muted); background: var(--surface);
  border: 1px solid var(--line); border-radius: 999px; padding: 5px 11px;
}
.terminal {
  background: var(--code-bg); color: var(--code-ink);
  border: 1px solid rgba(255, 255, 255, .08);
  border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden;
}
.term-bar { display: flex; align-items: center; gap: 7px; padding: 12px 16px; border-bottom: 1px solid rgba(255, 255, 255, .1); }
.term-bar span { width: 10px; height: 10px; border-radius: 50%; background: #6c5a4c; }
.term-bar span:nth-child(1) { background: #c96a4a; }
.term-bar span:nth-child(2) { background: #d0a24e; }
.term-bar span:nth-child(3) { background: #6f9c74; }
.term-bar b { margin-left: auto; font: 500 11px var(--mono); color: #b9a894; letter-spacing: .1em; text-transform: uppercase; }
.terminal pre {
  margin: 0; padding: 18px 20px 8px; font: 13.5px/1.75 var(--mono);
  white-space: pre-wrap; overflow-wrap: anywhere;
}
.term-note { margin: 0; padding: 0 20px 18px; color: #b9a894; font-size: 13px; }

/* secoes */
main > section { padding: 62px 0; border-bottom: 1px solid var(--line); scroll-margin-top: 84px; }
main > section:last-of-type { border-bottom: 0; }
.sec-head { display: flex; align-items: baseline; gap: 13px; margin-bottom: 24px; }
.sec-num {
  flex: none; font: 600 12.5px var(--mono); color: var(--accent);
  border: 1px solid var(--line-strong); border-radius: 8px; padding: 4px 8px;
}
h2 { font-size: clamp(30px, 3.7vw, 42px); line-height: 1.1; margin: 0; }
.sec-lede { font-size: 19px; color: var(--muted); max-width: 72ch; margin: 0 0 30px; }
h3 { font-size: 22px; line-height: 1.25; margin: 0 0 8px; }
h4 { font-size: 15px; margin: 0 0 6px; }

/* cartoes e grades */
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px; }
.card {
  background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 24px;
}
.card p:last-child { margin-bottom: 0; }
.card .kicker {
  display: inline-block; font: 600 11.5px var(--mono); letter-spacing: .08em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 10px;
}
.card .flow { margin: 14px 0 0; padding: 0; list-style: none; font-size: 14.5px; color: var(--muted); }
.card .flow li { padding: 5px 0; border-top: 1px dashed var(--line); }
.card .flow b { color: var(--ink); font-weight: 600; }
.split { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 18px; }
.split .card ul { margin: 10px 0 0; padding-left: 20px; color: var(--muted); }
.split .card li { margin: 5px 0; }

/* passos */
.steps { list-style: none; counter-reset: step; margin: 0; padding: 0; display: grid; gap: 12px; }
.steps > li {
  position: relative; padding: 17px 20px 17px 62px;
  background: var(--surface); border: 1px solid var(--line); border-radius: 14px;
}
.steps > li::before {
  counter-increment: step; content: counter(step);
  position: absolute; left: 18px; top: 17px; width: 30px; height: 30px;
  display: grid; place-items: center; border-radius: 50%;
  background: var(--accent-soft); color: var(--accent); font: 700 14px var(--sans);
}
.steps p { margin: 0; color: var(--muted); }
.steps p + p { margin-top: 6px; }
.steps strong { color: var(--ink); }

/* avisos */
.note {
  margin: 24px 0 0; padding: 17px 20px;
  background: var(--accent-soft); border-left: 4px solid var(--accent);
  border-radius: 0 14px 14px 0;
}
.note p:last-child { margin-bottom: 0; }
.note .label {
  display: block; font-size: 11.5px; font-weight: 700; letter-spacing: .1em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 5px;
}
.note.ok { background: var(--ok-soft); border-left-color: var(--ok); }
.note.ok .label { color: var(--ok); }

/* tabelas */
.table-wrap { overflow-x: auto; background: var(--surface); border: 1px solid var(--line); border-radius: 16px; }
table { width: 100%; border-collapse: collapse; font-size: 15px; min-width: 560px; }
th, td { text-align: left; padding: 13px 16px; vertical-align: top; border-bottom: 1px solid var(--line); }
th {
  font-size: 11.5px; text-transform: uppercase; letter-spacing: .08em;
  color: var(--muted); background: var(--surface-2); font-weight: 700;
}
tr:last-child td { border-bottom: 0; }
td strong { color: var(--ink); }
td.center, th.center { text-align: center; }

/* arquitetura */
.figure {
  margin: 0; padding: 16px; background: var(--surface);
  border: 1px solid var(--line); border-radius: var(--radius);
}
.figure svg { display: block; width: 100%; height: auto; }
.figure figcaption { margin: 12px 6px 4px; color: var(--muted); font-size: 14px; text-align: center; }
.figure svg.diagram-tall { display: none; }
.dg-node { fill: var(--surface-2); stroke: var(--line-strong); stroke-width: 1.4; }
.dg-strong { fill: var(--accent-soft); stroke: var(--accent); stroke-width: 1.6; }
.dg-container { fill: none; stroke: var(--line-strong); stroke-width: 1.5; stroke-dasharray: 7 6; }
.dg-cloud { fill: var(--surface); stroke: var(--accent); stroke-width: 1.5; stroke-dasharray: 5 4; }
.dg-text { fill: var(--ink); font-family: var(--sans); font-size: 15px; font-weight: 600; }
.dg-sub { fill: var(--muted); font-family: var(--sans); font-size: 12.5px; }
.dg-mono { fill: var(--muted); font-family: var(--mono); font-size: 12px; }
.dg-arrow { stroke: var(--accent); stroke-width: 2; fill: none; }
.dg-dash { stroke: var(--accent); stroke-width: 1.8; stroke-dasharray: 5 5; fill: none; }
.dg-label { fill: var(--accent); font-family: var(--sans); font-size: 11.5px; font-weight: 600; }
marker path { fill: var(--accent); }

/* prompts */
.prompt {
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 16px; margin: 0 0 18px; overflow: hidden;
}
.prompt-head {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 18px; padding: 20px 22px 14px;
}
.prompt-id {
  display: inline-block; margin: 0 0 5px; padding: 2px 7px;
  font: 600 12px var(--mono); color: var(--accent);
  background: var(--accent-soft); border-radius: 6px;
}
.prompt h3 { margin: 0 0 4px; font-size: 21px; }
.prompt .when { margin: 0; color: var(--muted); font-size: 14.5px; }
.copy {
  flex: none; min-height: 40px; padding: 9px 16px; cursor: pointer;
  border: 1px solid var(--line-strong); border-radius: 999px;
  background: var(--surface-2); color: var(--ink);
  font: 650 13.5px var(--sans);
}
.copy:hover { border-color: var(--accent); color: var(--accent); }
.copy.done { background: var(--ok-soft); border-color: var(--ok); color: var(--ok); }
.prompt pre {
  margin: 0; padding: 0 22px 20px; max-height: 340px; overflow: auto;
  background: transparent; border: 0; border-radius: 0;
  white-space: pre-wrap; overflow-wrap: anywhere;
  font: 13.5px/1.68 var(--mono); color: var(--ink);
}
.route { display: grid; gap: 8px; margin: 0 0 26px; }
.route p { margin: 0; color: var(--muted); }
.route b { color: var(--ink); }

/* rodape */
.foot { padding: 34px 0 46px; color: var(--muted); font-size: 14px; border-top: 1px solid var(--line); }
.foot p { margin: 0 0 5px; }
.foot .brand { font-size: 18px; margin-bottom: 8px; }

@media (max-width: 880px) {
  .hero-grid { grid-template-columns: 1fr; gap: 30px; }
  .hero { padding: 48px 0 40px; }
}
@media (max-width: 760px) {
  .top { position: static; }
  .bar { flex-wrap: wrap; gap: 10px; padding: 12px 0; }
  .top nav ul { gap: 5px 14px; }
  main > section { padding: 46px 0; scroll-margin-top: 20px; }
  .sec-head { flex-wrap: wrap; }
  .figure svg.diagram-wide { display: none; }
  .figure svg.diagram-tall { display: block; }
}
@media (max-width: 560px) {
  .wrap { width: calc(100% - 28px); }
  body { font-size: 16px; }
  .lede, .sec-lede { font-size: 17px; }
  .prompt-head { flex-direction: column; gap: 12px; padding: 18px 18px 12px; }
  .copy { width: 100%; }
  .prompt pre { padding: 0 18px 18px; }
  .card { padding: 20px; }
  .steps > li { padding: 16px 16px 16px 56px; }
  .steps > li::before { left: 14px; top: 15px; }
  .figure { padding: 10px; }
}
@media print {
  .top, .actions, .copy { display: none; }
  body { background: #fff; color: #000; }
  main > section { break-inside: avoid; }
}
"""


DIAGRAM_WIDE = r"""
<svg class="diagram-wide" viewBox="0 0 1180 400" role="img" aria-labelledby="dgw-title dgw-desc">
  <title id="dgw-title">Fluxo da forja: agente, kit.sh, container e ferramentas</title>
  <desc id="dgw-desc">O agente roda o kit.sh, que sobe o container forja. Dentro do container ficam ffmpeg, Whisper e Remotion com Chrome. O provedor de voz que você escolher recebe apenas o texto da narração (quando você usa a interface ou uma API opcional).</desc>
  <defs>
    <marker id="dot-w" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z"></path>
    </marker>
  </defs>

  <rect class="dg-node" x="24" y="132" width="190" height="112" rx="14"></rect>
  <text class="dg-text" x="119" y="172" text-anchor="middle">Seu agente</text>
  <text class="dg-sub" x="119" y="195" text-anchor="middle">lê os prompts e</text>
  <text class="dg-sub" x="119" y="212" text-anchor="middle">roda comandos</text>
  <text class="dg-mono" x="119" y="234" text-anchor="middle">Claude, Codex, Cursor…</text>

  <line class="dg-arrow" x1="218" y1="188" x2="254" y2="188" marker-end="url(#dot-w)"></line>

  <rect class="dg-strong" x="258" y="132" width="178" height="112" rx="14"></rect>
  <text class="dg-text" x="347" y="176" text-anchor="middle">kit.sh</text>
  <text class="dg-sub" x="347" y="199" text-anchor="middle">atalhos + compose</text>
  <text class="dg-mono" x="347" y="221" text-anchor="middle">setup · build · run</text>

  <line class="dg-arrow" x1="440" y1="188" x2="476" y2="188" marker-end="url(#dot-w)"></line>

  <rect class="dg-container" x="480" y="46" width="430" height="336" rx="18"></rect>
  <text class="dg-text" x="500" y="76">container forja</text>
  <text class="dg-sub" x="500" y="96">linux/amd64 · usuário não-root · caps removidas</text>

  <rect class="dg-node" x="500" y="112" width="190" height="86" rx="12"></rect>
  <text class="dg-text" x="595" y="144" text-anchor="middle">ffmpeg</text>
  <text class="dg-sub" x="595" y="166" text-anchor="middle">corta · mixa · mede</text>
  <text class="dg-sub" x="595" y="183" text-anchor="middle">loudness</text>

  <rect class="dg-node" x="702" y="112" width="188" height="86" rx="12"></rect>
  <text class="dg-text" x="796" y="144" text-anchor="middle">Whisper</text>
  <text class="dg-sub" x="796" y="166" text-anchor="middle">transcreve o áudio</text>
  <text class="dg-sub" x="796" y="183" text-anchor="middle">na sua máquina</text>

  <rect class="dg-node" x="500" y="216" width="190" height="86" rx="12"></rect>
  <text class="dg-text" x="595" y="247" text-anchor="middle">Remotion + Chrome</text>
  <text class="dg-sub" x="595" y="269" text-anchor="middle">legendas queimadas</text>
  <text class="dg-sub" x="595" y="286" text-anchor="middle">e vídeo por cenas</text>

  <rect class="dg-node" x="702" y="216" width="188" height="86" rx="12"></rect>
  <text class="dg-text" x="796" y="247" text-anchor="middle">cache + QA</text>
  <text class="dg-sub" x="796" y="269" text-anchor="middle">hash por passo</text>
  <text class="dg-sub" x="796" y="286" text-anchor="middle">gate de qualidade</text>

  <text class="dg-mono" x="500" y="336">volumes: projects/ e models/</text>
  <text class="dg-mono" x="500" y="356">a chave chega por ambiente; nunca vai para o projeto</text>

  <line class="dg-dash" x1="910" y1="188" x2="946" y2="188" marker-end="url(#dot-w)"></line>
  <text class="dg-label" x="928" y="176" text-anchor="middle">texto</text>
  <text class="dg-label" x="928" y="212" text-anchor="middle">voz</text>

  <rect class="dg-cloud" x="950" y="128" width="206" height="120" rx="14"></rect>
  <text class="dg-text" x="1053" y="162" text-anchor="middle">Provedor de voz</text>
  <text class="dg-sub" x="1053" y="186" text-anchor="middle">sua conta/interface</text>
  <text class="dg-sub" x="1053" y="203" text-anchor="middle">ou API opcional</text>
  <text class="dg-mono" x="1053" y="226" text-anchor="middle">sem chave obrigatória</text>

  <text class="dg-label" x="38" y="300" text-anchor="start">o vídeo e o áudio</text>
  <text class="dg-label" x="38" y="318" text-anchor="start">não saem da máquina</text>
</svg>
"""


DIAGRAM_TALL = r"""
<svg class="diagram-tall" viewBox="0 0 360 690" role="img" aria-labelledby="dgt-title dgt-desc">
  <title id="dgt-title">Fluxo da forja em coluna</title>
  <desc id="dgt-desc">O agente chama o kit.sh, que sobe o container forja com ffmpeg, Whisper e Remotion. O provedor de voz recebe apenas o texto da narração.</desc>
  <defs>
    <marker id="dot-t" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z"></path>
    </marker>
  </defs>

  <rect class="dg-node" x="24" y="18" width="312" height="76" rx="14"></rect>
  <text class="dg-text" x="180" y="49" text-anchor="middle">Seu agente</text>
  <text class="dg-sub" x="180" y="72" text-anchor="middle">lê os prompts e roda comandos</text>

  <line class="dg-arrow" x1="180" y1="98" x2="180" y2="128" marker-end="url(#dot-t)"></line>

  <rect class="dg-strong" x="24" y="132" width="312" height="76" rx="14"></rect>
  <text class="dg-text" x="180" y="163" text-anchor="middle">kit.sh</text>
  <text class="dg-sub" x="180" y="186" text-anchor="middle">atalhos + docker compose</text>

  <line class="dg-arrow" x1="180" y1="212" x2="180" y2="242" marker-end="url(#dot-t)"></line>

  <rect class="dg-container" x="24" y="246" width="312" height="278" rx="16"></rect>
  <text class="dg-text" x="42" y="276">container forja</text>
  <text class="dg-sub" x="42" y="295">não-root · sem capacidades extras</text>

  <rect class="dg-node" x="42" y="310" width="276" height="58" rx="10"></rect>
  <text class="dg-text" x="180" y="335" text-anchor="middle">ffmpeg</text>
  <text class="dg-sub" x="180" y="355" text-anchor="middle">corta, mixa, mede o loudness</text>

  <rect class="dg-node" x="42" y="378" width="276" height="58" rx="10"></rect>
  <text class="dg-text" x="180" y="403" text-anchor="middle">Whisper</text>
  <text class="dg-sub" x="180" y="423" text-anchor="middle">transcreve o áudio localmente</text>

  <rect class="dg-node" x="42" y="446" width="276" height="58" rx="10"></rect>
  <text class="dg-text" x="180" y="471" text-anchor="middle">Remotion + Chrome</text>
  <text class="dg-sub" x="180" y="491" text-anchor="middle">legendas e vídeo por cenas</text>

  <line class="dg-dash" x1="180" y1="528" x2="180" y2="558" marker-end="url(#dot-t)"></line>
  <text class="dg-label" x="192" y="548" text-anchor="start">só o texto da narração</text>

  <rect class="dg-cloud" x="24" y="562" width="312" height="96" rx="14"></rect>
  <text class="dg-text" x="180" y="596" text-anchor="middle">Provedor de voz</text>
  <text class="dg-sub" x="180" y="619" text-anchor="middle">sua conta/interface; não recebe o vídeo</text>
  <text class="dg-mono" x="180" y="641" text-anchor="middle">a chave fica só no .env</text>
</svg>
"""


TEMPLATE = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Forja — guia do kit de vídeo por agentes</title>
<meta name="description" content="Guia didático da forja: dublagem em português e vídeos por cenas operados pelo seu agente de IA. Instalação, prompts, segurança e licenças.">
<style>__CSS__</style>
</head>
<body>
<a class="skip" href="#conteudo">Pular para o conteúdo</a>

<header class="top">
  <div class="wrap bar">
    <a class="brand" href="#topo"><span class="mark" aria-hidden="true">f</span> forja</a>
    <nav aria-label="Seções do guia">
      <ul>
        <li><a href="#visao-geral">Visão geral</a></li>
        <li><a href="#modo-simples">Modos</a></li>
        <li><a href="#arquitetura">Arquitetura</a></li>
        <li><a href="#prompts">Prompts</a></li>
        <li><a href="#seguranca">Segurança</a></li>
        <li><a href="#licencas">Licenças</a></li>
        <li><a href="#navegador">Navegador</a></li>
        <li><a href="#problemas">Problemas</a></li>
      </ul>
    </nav>
  </div>
</header>

<main id="conteudo">

<section class="hero" id="topo">
  <div class="wrap hero-grid">
    <div class="hero-copy">
      <p class="eyebrow">Guia do kit · versão 0.1</p>
      <h1>Vídeo com voz e legenda,<br><em>operado pelo seu agente.</em></h1>
      <p class="lede">A <strong>forja</strong> dubla vídeos para o português e monta vídeos por cenas usando as <strong>suas contas</strong>. Você conversa com o seu agente de IA; ele roda os comandos, confere o resultado e pede a sua decisão quando é hora de escolher.</p>
      <div class="actions">
        <a class="btn primary" href="#visao-geral">Entender em 2 minutos</a>
        <a class="btn" href="#prompts">Ir para os prompts</a>
      </div>
      <ul class="chips">
        <li>Roda na sua máquina</li>
        <li>Docker em x86_64</li>
        <li>Sem chave de API obrigatória</li>
        <li>O vídeo não é enviado para ninguém</li>
      </ul>
    </div>
    <aside class="terminal" aria-label="Exemplo de comandos do kit">
      <div class="term-bar" aria-hidden="true"><span></span><span></span><span></span><b>kit</b></div>
      <pre><code>./kit.sh setup
./kit.sh doctor
./kit.sh build

./kit.sh run --project /projects/meu-video \
  --json status</code></pre>
      <p class="term-note">A saída em JSON diz qual é o próximo passo.</p>
    </aside>
  </div>
</section>

<section id="visao-geral">
  <div class="wrap">
    <div class="sec-head"><span class="sec-num">01</span><h2>O que a forja faz</h2></div>
    <p class="sec-lede">Duas tarefas, o mesmo jeito de trabalhar. Você entrega o material, as contas e as decisões; o agente cuida do caminho técnico.</p>

    <div class="cards">
      <article class="card">
        <span class="kicker">workflow dub</span>
        <h3>Dublar um vídeo</h3>
        <p>Pega um vídeo em inglês, transcreve, adapta o texto com você, usa as vozes que você gerou, mixa por cima do áudio original com ducking e queima a legenda no vídeo.</p>
        <ul class="flow">
          <li><b>Entra:</b> <code>input/source.mp4</code> + <code>voices/&lt;id&gt;.wav</code></li>
          <li><b>Sai:</b> <code>out/video.mp4</code>, <code>legendas.srt</code>, <code>qa.json</code></li>
        </ul>
      </article>
      <article class="card">
        <span class="kicker">workflow storyboard</span>
        <h3>Criar por cenas</h3>
        <p>Monta um vídeo do zero a partir de um <code>storyboard.yaml</code>: clipes, narração que você gerou, cards, trilha e legendas, cena por cena, com a duração vindo da fala.</p>
        <ul class="flow">
          <li><b>Entra:</b> <code>storyboard.yaml</code> + <code>assets/</code> + <code>voices/&lt;cena&gt;.wav</code></li>
          <li><b>Sai:</b> <code>out/video.mp4</code>, <code>legendas.srt</code>, <code>qa.json</code></li>
        </ul>
      </article>
    </div>

    <h3 style="margin-top:34px">Quem decide o quê</h3>
    <div class="split">
      <div class="card">
        <span class="kicker">seu papel</span>
        <ul>
          <li>Escolher a voz e aprovar o elenco.</li>
          <li>Fechar o texto final da dublagem.</li>
          <li>Confirmar direitos, consentimento e aviso de IA.</li>
          <li>Autorizar qualquer gasto (API é opcional).</li>
          <li>Publicar — e decidir onde.</li>
        </ul>
      </div>
      <div class="card">
        <span class="kicker">papel do agente</span>
        <ul>
          <li>Rodar <code>doctor</code>, <code>status</code>, <code>run</code> e <code>qa</code>.</li>
          <li>Transcrever, extrair quadros e propor o texto.</li>
          <li>Escrever <code>cues.json</code> e <code>storyboard.yaml</code>.</li>
          <li>Validar e normalizar as vozes que você forneceu.</li>
          <li>Ler o erro, corrigir e só então te chamar.</li>
        </ul>
      </div>
    </div>

    <h3 style="margin-top:34px">O ciclo de trabalho</h3>
    <ol class="steps">
      <li>
        <strong>Veja o estado.</strong>
        <p><code>./kit.sh run --project /projects/meu-video --json status</code> mostra cada passo e o campo <code>next_actions</code>.</p>
      </li>
      <li>
        <strong>Faça o próximo passo.</strong>
        <p>Muitas vezes o passo é do agente: escrever as cues, montar o storyboard, validar as vozes. Ele pede a sua decisão quando precisa.</p>
      </li>
      <li>
        <strong>Rode o pipeline.</strong>
        <p><code>./kit.sh run --project /projects/meu-video --json run</code> roda só o que mudou: o cache é por hash das entradas.</p>
      </li>
      <li>
        <strong>Confira o portão de qualidade.</strong>
        <p><code>./kit.sh run --project /projects/meu-video --json qa --strict</code>. Saída <code>1</code> quer dizer reprovado: leia os <code>issues</code> antes de entregar.</p>
      </li>
    </ol>

    <div class="note ok">
      <span class="label">a regra de ouro</span>
      <p>O agente não escolhe voz, não publica e não gasta além do combinado sem você. As contas são suas; o kit só orquestra o trabalho determinístico.</p>
    </div>

    <h3 style="margin-top:36px">Antes de começar</h3>
    <div class="cards">
      <article class="card">
        <h4>Máquina</h4>
        <p>Windows 10/11 com WSL2 ou Linux, ambos <strong>x86_64</strong>. Docker com Compose v2. 8&nbsp;GB de RAM (16&nbsp;GB é melhor) e 25&nbsp;GB livres.</p>
      </article>
      <article class="card">
        <h4>Imagem</h4>
        <p>Cerca de <strong>1,8&nbsp;GB</strong> para o pipeline. O Chromium opcional do modo avançado acrescenta uns 2,6&nbsp;GB.</p>
      </article>
      <article class="card">
        <h4>Internet</h4>
        <p>No primeiro build e para baixar o modelo de transcrição uma vez. Depois, só o provedor de voz que você escolher precisa de rede — e o vídeo/áudio original não é enviado pelo kit.</p>
      </article>
    </div>

    <h3 style="margin-top:36px">Começar em 5 passos</h3>
    <ol class="steps">
      <li><strong>Prepare o kit.</strong><p><code>./kit.sh setup</code> cria o <code>.env</code>, uma senha aleatória do navegador e as pastas <code>projects/</code> e <code>models/</code>.</p></li>
      <li><strong>Escolha as vozes.</strong><p>O padrão é <code>voices.provider: files</code>: você gera cada voz na interface/ferramenta da sua conta e salva em <code>projects/&lt;nome&gt;/voices/&lt;id&gt;.wav</code>. Provedor por API é opcional.</p></li>
      <li><strong>Construa a imagem.</strong><p><code>./kit.sh build</code>. É a parte demorada; só acontece na primeira vez (ou quando o kit muda).</p></li>
      <li><strong>Ensine o seu agente.</strong><p>Copie o <strong>prompt 02</strong> desta página e cole no seu agente. Ele instala a skill e passa a saber operar a forja.</p></li>
      <li><strong>Peça o vídeo.</strong><p>Use o <strong>prompt 03</strong> para dublar um vídeo existente ou o <strong>prompt 08</strong> para criar um vídeo por cenas.</p></li>
    </ol>

    <div class="note">
      <span class="label">mapa do kit</span>
      <p><code>kit.sh</code> (atalhos) · <code>compose.yaml</code> (container) · <code>.env</code> (senha do navegador e opções; fora do git) · <code>voices/</code> (suas vozes) · <code>prompts/</code> (14 mensagens) · <code>projects/</code> (seus vídeos) · <code>docs/index.html</code> (esta página) · <code>skills/forja/</code> (a skill do agente).</p>
    </div>
  </div>
</section>

<section id="modo-simples">
  <div class="wrap">
    <div class="sec-head"><span class="sec-num">02</span><h2>Modo padrão: as suas contas</h2></div>
    <p class="sec-lede">É o caminho recomendado: <strong>sem chave de API</strong>. Você gera as vozes na interface ou na ferramenta que já usa e o kit faz o resto.</p>

    <ol class="steps">
      <li>
        <strong>Crie a configuração.</strong>
        <p><code>./kit.sh setup</code> copia o <code>.env.example</code>, gera a senha do navegador, ajusta o seu UID/GID e cria <code>projects/</code> e <code>models/</code>.</p>
      </li>
      <li>
        <strong>Confirme o provedor de voz.</strong>
        <p>O padrão é <code>voices.provider: files</code> e <code>voices.input_dir: voices</code>. Você não precisa de chave; as vozes ficam em <code>projects/&lt;nome&gt;/voices/&lt;id&gt;.wav</code>. Um provedor por API é opcional e configurado no <code>config.yaml</code>.</p>
      </li>
      <li>
        <strong>Gere as vozes com a sua conta.</strong>
        <p>Abra a interface do provedor que você escolher (por exemplo no navegador, com a sua conta) ou use a ferramenta local que preferir. Para cada cue do <code>cues.json</code>, gere a fala e salve um WAV PCM em <code>projects/&lt;nome&gt;/voices/&lt;id&gt;.wav</code>. O kit valida, normaliza e mixa.</p>
      </li>
      <li>
        <strong>Confira o ambiente.</strong>
        <p><code>./kit.sh doctor</code> mostra Docker, Compose, arquitetura, espaço em disco e o provedor de voz. Se você optar por API, a chave aparece só como <em>definida</em> ou <em>ausente</em> — nunca o valor.</p>
      </li>
      <li>
        <strong>Construa a imagem.</strong>
        <p><code>./kit.sh build</code>. O Docker baixa a base, instala ffmpeg, Python, Whisper e o Chrome Headless do Remotion. Vai demorar alguns minutos na primeira vez.</p>
      </li>
      <li>
        <strong>Entregue o volante ao agente.</strong>
        <p>Copie o <strong>prompt 02</strong> para instalar a skill. Depois use o <strong>prompt 03</strong> (dublar) ou o <strong>prompt 08</strong> (cenas) e responda às perguntas dele.</p>
      </li>
    </ol>

    <div class="note ok">
      <span class="label">nenhuma chave obrigatória</span>
      <p>No modo <code>files</code>, o kit não fala com nenhum serviço de voz: ele só valida e mixa os arquivos que você gerou. Se você escolher um provedor por API, a chave é sua, fica no <code>.env</code> e o gasto é decidido por você.</p>
    </div>

    <h3 style="margin-top:34px">O que fica onde</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Arquivo ou pasta</th><th>Para que serve</th><th>Vai para o git?</th></tr></thead>
        <tbody>
          <tr><td><code>.env</code></td><td>Senha do navegador, UID/GID e limites do container; chave só se você optar por API.</td><td>Nunca.</td></tr>
          <tr><td><code>projects/&lt;nome&gt;/voices/</code></td><td>Os WAVs que você gerou, um por cue ou cena.</td><td>Não.</td></tr>
          <tr><td><code>projects/&lt;nome&gt;/</code></td><td>O vídeo de entrada, as cues, o storyboard e as saídas.</td><td>Não.</td></tr>
          <tr><td><code>prompts/</code></td><td>As 14 mensagens prontas para o seu agente.</td><td>Sim.</td></tr>
          <tr><td><code>docs/index.html</code></td><td>Este guia, offline, num arquivo só.</td><td>Sim.</td></tr>
          <tr><td><code>models/</code></td><td>Cache do modelo de transcrição; pode apagar (ele baixa de novo).</td><td>Não.</td></tr>
          <tr><td><code>work/</code> e <code>out/</code> (no projeto)</td><td>Intermediários e resultado. <code>work/</code> é descartável.</td><td>Não.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</section>

<section id="modo-avancado">
  <div class="wrap">
    <div class="sec-head"><span class="sec-num">03</span><h2>Modo avançado: navegador no container</h2></div>
    <p class="sec-lede">Para quem quer a interface do provedor numa aba do navegador normal, sem ocupar a área de trabalho — e para quem optar por um provedor de voz por API.</p>

    <ol class="steps">
      <li>
        <strong>Suba o navegador.</strong>
        <p><code>./kit.sh browser-up</code> inicia o Chromium e um proxy que deixa o CDP acessível apenas no seu loopback. A senha já foi gerada no <code>.env</code>; pegue-a no arquivo, não a imprima.</p>
      </li>
      <li>
        <strong>Entre na tela.</strong>
        <p>Abra <code>https://localhost:3001</code>, aceite o certificado autoassinado e use o usuário e a senha do <code>.env</code>.</p>
      </li>
      <li>
        <strong>Faça o login com a sua conta.</strong>
        <p>O login acontece <em>dentro</em> desse ambiente. O perfil fica num volume Docker e sobrevive a reinícios. A sessão não é copiada de outra máquina — e não deve ser.</p>
      </li>
      <li>
        <strong>Gere as vozes e salve os WAVs.</strong>
        <p>Use a interface para gerar a fala de cada cue e salve em <code>projects/&lt;nome&gt;/voices/&lt;id&gt;.wav</code>. O agente pode conduzir por CDP em <code>127.0.0.1:9222</code> (Playwright MCP ou computer use).</p>
      </li>
      <li>
        <strong>Opcional: provedor por API.</strong>
        <p>Se você preferir automatizar a síntese, configure <code>voices.provider: gemini</code>, <code>voices.model</code> e a sua chave no <code>.env</code>. O caminho padrão continua sendo <code>files</code>.</p>
      </li>
      <li>
        <strong>Termine com cuidado.</strong>
        <p><code>./kit.sh browser-down</code> desliga e mantém o login. <code>./kit.sh browser-reset</code> apaga o perfil — depois revogue a sessão na conta do provedor.</p>
      </li>
    </ol>

    <div class="note">
      <span class="label">cuidado real</span>
      <p>O terminal web da imagem do Chromium tem <code>sudo</code> sem senha. Quem alcança a tela vira root <em>dentro do container</em>. Por isso as portas <code>3001</code> e <code>9222</code> ficam presas em <code>127.0.0.1</code> e nunca devem ser publicadas na rede. Em máquina compartilhada, não deixe a tela aberta.</p>
    </div>

    <h3 style="margin-top:34px">Padrão ou avançado?</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Pergunta</th><th>Modo padrão (contas)</th><th>Modo avançado</th></tr></thead>
        <tbody>
          <tr><td><strong>Como gera as vozes</strong></td><td>Interface/ferramenta com a sua conta; <code>voices.provider: files</code></td><td>Chromium no container + interface; API opcional</td></tr>
          <tr><td><strong>Navegador</strong></td><td>O seu, em outra área de trabalho</td><td>Chromium no Docker, numa aba de <code>https://localhost:3001</code></td></tr>
          <tr><td><strong>Chave de API</strong></td><td>Nenhuma</td><td>Só se você configurar um provedor por API</td></tr>
          <tr><td><strong>O que instala</strong></td><td>Só a imagem da forja</td><td>Imagem da forja + Chromium (~2,6&nbsp;GB) + proxy</td></tr>
          <tr><td><strong>Quando escolher</strong></td><td>Padrão. Você quer usar a sua conta sem instalar nada além do kit.</td><td>Você quer a UI numa aba do navegador ou vai automatizar por API.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</section>

<section id="arquitetura">
  <div class="wrap">
    <div class="sec-head"><span class="sec-num">04</span><h2>Como as peças se encaixam</h2></div>
    <p class="sec-lede">Você fala com o agente. Ele roda o <code>kit.sh</code>. O <code>kit.sh</code> chama o Docker. Dentro do container, a CLI orquestra ffmpeg, Whisper, Remotion e o provedor de voz que você escolher.</p>

    <figure class="figure">
      __DIAGRAM_WIDE__
      __DIAGRAM_TALL__
      <figcaption>O caminho de um comando: agente → <code>kit.sh</code> → container <code>forja</code> → ferramentas. O provedor de voz recebe somente o texto da narração — e só quando você usa a interface ou uma API opcional.</figcaption>
    </figure>

    <h3 style="margin-top:34px">O que atravessa a fronteira</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Fica na sua máquina</th><th>Sai para a internet</th></tr></thead>
        <tbody>
          <tr><td>Vídeo, áudio, quadros, transcrição, cues, storyboard, saídas.</td><td>O texto da narração enviado ao provedor de voz que você escolher (voltam os arquivos de voz).</td></tr>
          <tr><td>As suas contas e, se houver API, a chave no <code>.env</code>.</td><td>Downloads do primeiro build e o modelo do Whisper, baixados uma vez.</td></tr>
          <tr><td>O cache por hash e o <code>work/events.ndjson</code>.</td><td>Nada de vídeo ou áudio original é enviado pelo kit.</td></tr>
        </tbody>
      </table>
    </div>

    <h3 style="margin-top:34px">Por que um container</h3>
    <div class="cards">
      <article class="card"><h4>Repetível</h4><p>O mesmo comando funciona no Windows (WSL2) e no Linux. As versões de ffmpeg, Python, Node e Chrome ficam presas na imagem.</p></article>
      <article class="card"><h4>Isolado</h4><p>Roda com o seu UID/GID (nunca root), com <code>cap_drop: ALL</code>, <code>no-new-privileges</code> e limites de CPU e memória.</p></article>
      <article class="card"><h4>Portátil</h4><p>Só duas pastas são montadas: <code>projects/</code> e <code>models/</code> (cache de modelos). O resto do seu disco não é visível para o pipeline.</p></article>
    </div>

    <h3 style="margin-top:34px">Dentro do container</h3>
    <ul>
      <li><strong>ffmpeg</strong> — corta o trecho, extrai o áudio, aplica o ducking, normaliza o loudness e muxa o resultado.</li>
      <li><strong>Whisper (faster-whisper)</strong> — transcreve em CPU, com timestamps por palavra, sem mandar o áudio para fora.</li>
      <li><strong>Remotion + Chrome Headless Shell</strong> — desenha as legendas e o vídeo por cenas quadro a quadro.</li>
      <li><strong>CLI forja</strong> — decide o que rodar, guarda o cache, escreve os eventos e aplica o portão de QA.</li>
      <li><strong>Provedor de voz</strong> — fora do container, recebe o texto e devolve a voz; você usa a sua conta/interface ou, se optar, uma chave de API.</li>
    </ul>

    <div class="note ok">
      <span class="label">por que isso importa</span>
      <p>O agente pode errar um comando sem estragar a sua máquina: o pior caso é um arquivo em <code>projects/</code>. E o QA é um portão de verdade — <code>qa --strict</code> sai com código 1 quando o vídeo não passa.</p>
    </div>
  </div>
</section>

<section id="prompts">
  <div class="wrap">
    <div class="sec-head"><span class="sec-num">05</span><h2>Os prompts, na ordem</h2></div>
    <p class="sec-lede">São mensagens prontas para colar no seu agente. Cada uma assume que a anterior foi concluída. O botão <strong>Copiar</strong> leva o texto inteiro — o mesmo que está logo abaixo.</p>

    <div class="route">
      <p><b>Dublar:</b> 00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 12.</p>
      <p><b>Criar por cenas:</b> 00 → 01 → 02 → 08 → 12.</p>
      <p><b>Apoio:</b> 09 (evoluir), 10 e 11 (navegador), 13 (problemas), a qualquer momento.</p>
    </div>

    <div class="prompts">
      __PROMPTS__
    </div>

    <div class="note">
      <span class="label">como usar</span>
      <p>Abra o prompt, confira os placeholders (como <code>&lt;CAMINHO_DO_KIT&gt;</code> e <code>&lt;NOME&gt;</code>) e copie. O agente deve pedir a sua confirmação antes de gastar API, escolher voz ou publicar.</p>
    </div>
  </div>
</section>

<section id="seguranca">
  <div class="wrap">
    <div class="sec-head"><span class="sec-num">06</span><h2>Segurança sem drama</h2></div>
    <p class="sec-lede">O kit foi desenhado para uma máquina e para as <strong>suas</strong> contas. Estas são as regras que mantêm isso simples.</p>

    <div class="cards">
      <article class="card">
        <h4>Sem chave obrigatória</h4>
        <p>No modo padrão (<code>voices.provider: files</code>), o kit não fala com nenhum serviço de voz: você gera os WAVs e ele valida/mixa. Se optar por um provedor de API, a chave fica só no <code>.env</code> (0600 no Linux/macOS; no Windows, restrinja a pasta do kit), nunca em log, commit, print ou <code>--json</code>.</p>
      </article>
      <article class="card">
        <h4>O container não é root</h4>
        <p>Roda com o seu UID/GID, <code>cap_drop: ALL</code>, <code>no-new-privileges</code> e teto de CPU e memória. Só <code>projects/</code> e <code>models/</code> aparecem para ele.</p>
      </article>
      <article class="card">
        <h4>O navegador é loopback</h4>
        <p>No modo avançado, <code>3001</code> (a tela, com senha) e <code>9222</code> (o CDP, sem autenticação própria) escutam só em <code>127.0.0.1</code>. Quem alcança o CDP, controla.</p>
      </article>
      <article class="card">
        <h4>O login fica no ambiente final</h4>
        <p>Faça o login na conta do provedor dentro do navegador do kit. Não copie perfil ou cookies entre máquinas: a sessão é do dispositivo e não deve viajar.</p>
      </article>
      <article class="card">
        <h4>As contas são suas</h4>
        <p>Use a sua conta e a sua ferramenta de voz. Não compartilhe login, não empreste chave e não deixe a tela do Chromium aberta em máquina compartilhada.</p>
      </article>
      <article class="card">
        <h4>Consentimento é de quem publica</h4>
        <p>Voz sintetizada de pessoa real pede autorização e aviso. O prompt 12 monta a pasta de conformidade com você; a decisão final é sempre humana.</p>
      </article>
    </div>

    <div class="note">
      <span class="label">se algo vazar</span>
      <p>Se você usa um provedor por API, gere outra chave e atualize o <code>.env</code>. Se o problema for o navegador, rode <code>./kit.sh browser-reset</code> e revogue a sessão na conta do provedor. O <code>work/events.ndjson</code> foi feito para não guardar segredo: chaves nos nomes dos campos são descartadas.</p>
    </div>
  </div>
</section>

<section id="licencas">
  <div class="wrap">
    <div class="sec-head"><span class="sec-num">07</span><h2>Licenças e direitos</h2></div>
    <p class="sec-lede">Você não precisa ser advogado para usar o kit — mas precisa saber o que está usando e o que vai publicar.</p>

    <div class="table-wrap">
      <table>
        <thead><tr><th>Peça</th><th>Licença / condição</th><th>O que isso significa para você</th></tr></thead>
        <tbody>
          <tr>
            <td><strong>Remotion 4.0.540</strong></td>
            <td><strong>Free License</strong> para indivíduos e empresas de até 3 pessoas; acima disso, licença comercial paga.</td>
            <td>Para uso pessoal ou time de até 3 pessoas, é gratuito, inclusive comercial. Verificado na página oficial em 10/11/2026; se o seu caso for maior, verifique a licença vigente em <code>remotion.dev/docs/license/pricing</code>.</td>
          </tr>
          <tr>
            <td><strong>ffmpeg</strong></td>
            <td>LGPL/GPL conforme o build. O pacote Debian da imagem inclui componentes GPL (por exemplo, libx264).</td>
            <td>O vídeo que você produz é seu; a licença do ffmpeg não contamina a saída. Se você redistribuir a imagem do container, revise as obrigações de fonte.</td>
          </tr>
          <tr>
            <td><strong>Whisper / faster-whisper</strong></td>
            <td>MIT (modelo e implementação).</td>
            <td>Transcrição local, sem custo por minuto. O modelo é baixado uma vez.</td>
          </tr>
          <tr>
            <td><strong>Provedor de voz</strong></td>
            <td>Termos da conta/provedor que você escolher; API opcional.</td>
            <td>No modo <code>files</code>, você controla a geração e o áudio não passa pelo kit. Se usar uma API, o texto da narração é enviado ao provedor e valem os termos e a política dele.</td>
          </tr>
          <tr>
            <td><strong>Música, imagens e clipes</strong></td>
            <td>Direitos de quem criou. No storyboard, a camada <code>music</code> exige <code>license.kind</code>.</td>
            <td>Trilha, foto e clipe precisam de licença compatível com o uso (CC0, CC BY, comprada ou própria). Guarde a origem e o crédito.</td>
          </tr>
          <tr>
            <td><strong>Vozes e pessoas</strong></td>
            <td>Consentimento e direitos de imagem/voz.</td>
            <td>Dublar e clonar voz são transformações. Tenha autorização de quem detém os direitos e das pessoas ouvidas; quem publica responde pelo uso.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="note">
      <span class="label">aviso obrigatório de voz sintetizada</span>
      <p>Deixe claro no vídeo que a voz é gerada por IA — por exemplo, um card ou uma linha na legenda dizendo <strong>“Este vídeo usa voz sintetizada por IA.”</strong> Coloque também na descrição. O prompt 12 ajuda a montar esse aviso e a registrar o consentimento.</p>
    </div>

    <div class="note ok">
      <span class="label">licença deste kit</span>
      <p>O Forja é software livre sob a <strong>MIT License</strong>. Você pode usar, modificar e redistribuir, mantendo o aviso de copyright. Veja o arquivo <code>LICENSE</code> e o <code>THIRD_PARTY.md</code> na raiz do repositório.</p>
    </div>
  </div>
</section>

<section id="navegador">
  <div class="wrap">
    <div class="sec-head"><span class="sec-num">08</span><h2>O Chromium pode rodar minimizado?</h2></div>
    <p class="sec-lede">Pergunta curta, resposta honesta: <strong>não é confiável</strong>. Janela minimizada ou totalmente coberta conta como oculta para o navegador.</p>

    <div class="note">
      <span class="label">por que não</span>
      <p>O Chrome reduz timers, animações e trabalho de renderização quando a janela não está visível. O CDP até responde, mas a página pode travar, atrasar ou desenhar errado. Para automação de verdade, a janela precisa estar visível — mesmo que em outra área de trabalho.</p>
    </div>

    <div class="cards" style="margin-top:22px">
      <article class="card">
        <span class="kicker">modo padrão</span>
        <h4>Outra área de trabalho</h4>
        <p>Use um perfil de navegador dedicado e deixe a janela visível num desktop virtual: Windows <code>Win+Ctrl+D</code>, macOS Mission Control, Linux outro workspace. Não minimize.</p>
      </article>
      <article class="card">
        <span class="kicker">modo avançado</span>
        <h4>Container + aba</h4>
        <p>O Chromium roda no Docker e aparece numa aba do seu navegador normal. A página continua viva no container, sem depender da sua área de trabalho.</p>
      </article>
      <article class="card">
        <span class="kicker">sempre</span>
        <h4>As contas são suas</h4>
        <p>A interface com a sua conta é o caminho padrão. A API é opcional e só entra se você configurar. Em qualquer modo, não compartilhe a conta nem copie a sessão para outra máquina.</p>
      </article>
    </div>

    <h3 style="margin-top:34px">Faça e evite</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Faça</th><th>Evite</th></tr></thead>
        <tbody>
          <tr><td>Perfil dedicado, só para o kit.</td><td>Usar o seu perfil diário (o Chrome 136+ ignora a porta de depuração nele).</td></tr>
          <tr><td>Janela visível em outra área de trabalho.</td><td>Minimizar ou deixar atrás de outras janelas por horas.</td></tr>
          <tr><td>Login feito dentro do ambiente final.</td><td>Copiar perfil ou cookies de outra máquina.</td></tr>
          <tr><td>CDP só em <code>127.0.0.1</code>; a tela tem senha, o CDP não.</td><td>Publicar <code>9222</code> ou <code>3001</code> na rede local.</td></tr>
          <tr><td><code>browser-reset</code> + revogar sessão ao terminar.</td><td>Deixar a tela aberta em máquina compartilhada.</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</section>

<section id="problemas">
  <div class="wrap">
    <div class="sec-head"><span class="sec-num">09</span><h2>Quando algo dá errado</h2></div>
    <p class="sec-lede">Não adivinhe a causa. Leia o erro literal, reproduza com o menor comando possível e só então conclua. O prompt 13 conduz o agente por essa ordem.</p>

    <ol class="steps">
      <li><strong>Comece pelo ambiente.</strong><p><code>./kit.sh doctor</code>. Docker, Compose, arquitetura, provedor de voz e disco. O <code>doctor</code> da CLI (<code>forja --json doctor</code>) vê ffmpeg, ffprobe, node e as bibliotecas.</p></li>
      <li><strong>Veja os containers.</strong><p><code>docker compose ps -a</code> e <code>docker compose logs --tail 80 forja</code> (ou <code>browser</code>).</p></li>
      <li><strong>Pergunte à CLI o que falta.</strong><p><code>./kit.sh run --project /projects/meu-video --json status</code> devolve o estado de cada passo e <code>next_actions</code>.</p></li>
      <li><strong>Leia o rastro.</strong><p><code>projects/meu-video/work/events.ndjson</code> tem um evento por passo, com início, fim e o erro. O último <code>failed</code> é o que importa.</p></li>
      <li><strong>Traduza o código.</strong><p>No <code>--json</code>, olhe <code>error.code</code>, <code>error.hint</code> e <code>retryable</code>. A dica já diz o que corrigir; <code>retryable: true</code> pode ser repetido.</p></li>
    </ol>

    <h3 style="margin-top:34px">Códigos de saída</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th class="center">Código</th><th>Significado</th><th>O que fazer</th></tr></thead>
        <tbody>
          <tr><td class="center"><strong>0</strong></td><td>Tudo certo.</td><td>Siga para o QA ou para a entrega.</td></tr>
          <tr><td class="center"><strong>1</strong></td><td>Portão reprovado: <code>check</code> ou <code>qa</code> com erro.</td><td>Leia os <code>issues</code>, corrija e rode de novo.</td></tr>
          <tr><td class="center"><strong>2</strong></td><td>Uso ou configuração inválida.</td><td>Confira os argumentos e o <code>config.yaml</code>.</td></tr>
          <tr><td class="center"><strong>3</strong></td><td>Falha externa possivelmente repetível (rede, cota, 5xx).</td><td>Espere e repita; se persistir, leia o provedor.</td></tr>
          <tr><td class="center"><strong>4</strong></td><td>Pré-requisito ausente (ffmpeg, WAV de voz, modelo, navegador).</td><td>Instale ou configure o que falta e rode <code>doctor</code>.</td></tr>
          <tr><td class="center"><strong>5</strong></td><td>Erro interno (bug).</td><td>Guarde o <code>--json</code> e reporte o código e a mensagem.</td></tr>
        </tbody>
      </table>
    </div>

    <h3 style="margin-top:34px">Erros comuns</h3>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Código do erro</th><th>Quase sempre é</th><th>Saída</th></tr></thead>
        <tbody>
          <tr><td><code>MISSING_INPUT</code></td><td>Falta a voz em <code>voices/&lt;id&gt;.wav</code> ou outro arquivo de entrada.</td><td>Gere a voz com a sua conta/ferramenta e salve no caminho indicado; rode o passo de novo.</td></tr>
          <tr><td><code>MISSING_KEY</code></td><td>Só no provedor por API: a chave não está no <code>.env</code>.</td><td>Se você optou por API, preencha a chave; no modo <code>files</code>, isso não se aplica.</td></tr>
          <tr><td><code>MISSING_PREREQ</code></td><td>Falta ffmpeg, modelo ou o build não terminou.</td><td>Rode <code>./kit.sh doctor</code> e <code>./kit.sh build</code>.</td></tr>
          <tr><td><code>GATE_FAILED</code></td><td>O check ou o QA encontrou erro.</td><td>Corrija os itens de <code>issues</code>; não force a entrega.</td></tr>
          <tr><td><code>RATE_LIMITED</code></td><td>Cota do provedor.</td><td>Aguarde; o kit já tenta de novo com espera.</td></tr>
          <tr><td><code>CONFIG_INVALID</code></td><td><code>config.yaml</code> ou <code>storyboard.yaml</code> inválido.</td><td>Leia a mensagem; rode <code>forja init</code> de novo se necessário.</td></tr>
          <tr><td><code>USAGE</code></td><td>Comando ou argumento errado.</td><td>Confira <code>forja --help</code> e o prompt da etapa.</td></tr>
        </tbody>
      </table>
    </div>

    <div class="note">
      <span class="label">peça ajuda com contexto</span>
      <p>Copie o <strong>prompt 13</strong> e cole a saída literal do erro (com <code>--json</code>). Diga o comando exato, o projeto e o que você esperava. Não cole chave nem senha.</p>
    </div>
  </div>
</section>

</main>

<footer class="foot">
  <div class="wrap">
    <p class="brand"><span class="mark" aria-hidden="true">f</span> forja</p>
    <p>Guia offline do kit: dublagem EN→pt-BR e vídeo por cenas, operados pelo seu agente.</p>
    <p>Este arquivo não faz nenhuma requisição externa. Os prompts estão embutidos e podem ser copiados. Forja é software livre sob a MIT License.</p>
  </div>
</footer>

<script>
(function () {
  "use strict";
  function fallbackCopy(text) {
    var area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.top = "-1000px";
    document.body.appendChild(area);
    area.select();
    try { document.execCommand("copy"); } catch (error) { /* sem suporte */ }
    document.body.removeChild(area);
  }
  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    fallbackCopy(text);
    return Promise.resolve();
  }
  var buttons = document.querySelectorAll("button[data-copy]");
  for (var i = 0; i < buttons.length; i++) {
    (function (button) {
      button.addEventListener("click", function () {
        var slug = button.getAttribute("data-copy");
        var block = document.querySelector('pre[data-prompt="' + slug + '"]');
        if (!block) { return; }
        var label = button.textContent;
        function done() {
          button.textContent = "Copiado!";
          button.className = button.className + " done";
          window.setTimeout(function () {
            button.textContent = label;
            button.className = button.className.replace(" done", "");
          }, 1600);
        }
        function retry() {
          fallbackCopy(block.textContent);
          done();
        }
        copyText(block.textContent).then(done, retry);
      });
    })(buttons[i]);
  }
})();
</script>
</body>
</html>
"""


def _render(files: list[Path]) -> str:
    page = TEMPLATE.replace("__CSS__", CSS.strip())
    page = page.replace("__DIAGRAM_WIDE__", DIAGRAM_WIDE.strip())
    page = page.replace("__DIAGRAM_TALL__", DIAGRAM_TALL.strip())
    return page.replace("__PROMPTS__", _prompt_cards(files))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gera o guia web (um HTML offline) do kit forja."
    )
    parser.add_argument("--out", required=True, help="arquivo HTML de saida")
    parser.add_argument(
        "--prompts",
        default=str(ROOT / "prompts"),
        help="pasta com os prompts em Markdown (default: prompts/)",
    )
    args = parser.parse_args(argv)

    prompts_dir = Path(args.prompts).expanduser()
    if not prompts_dir.is_dir():
        print("erro: pasta de prompts nao encontrada: %s" % prompts_dir, file=sys.stderr)
        return 2
    files = sorted(prompts_dir.glob("*.md"))
    if not files:
        print("erro: nenhum arquivo .md encontrado em %s" % prompts_dir, file=sys.stderr)
        return 2

    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_render(files), encoding="utf-8")
    print("gerado: %s (%d prompts, %d bytes)" % (out, len(files), out.stat().st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
