# Prompt de validação independente — Forja

Você é um **auditor técnico independente** do repositório **https://github.com/alisonglima/forja**. O dono já validou a geração real no setup dele (Google AI Studio para narração e Google Flow para cenas, no navegador logado com a conta e os créditos). **Não reproduza a geração real, não gaste créditos e não acesse contas.** Seu trabalho é validar se o repositório, a CLI, o render e a documentação refletem esse setup com segurança e sem induzir ao erro.

## Contexto do produto

- **Narração padrão:** Google AI Studio, no navegador, com a conta do usuário; os WAVs são salvos em `voices/<id>.wav`. O provider padrão é `google_ai_studio`.
- **Cenas padrão:** Google Flow, no navegador logado, com a conta e os créditos; os MP4s são baixados para `assets/flow/` e entram no `storyboard.yaml` como camadas `clip`. **O Forja não chama o Flow por API.**
- **Alternativas:** `files` (alias para qualquer WAV), `piper` (TTS local opcional, não é o setup padrão), `gemini` (API opcional). Não podem ser apresentadas como caminho padrão.
- **Overlays:** presets `lower_third`, `title`, `callout`, `quote`, `cta`, `logo`, `stat`, tema `brand`, `style` por camada e legenda elevada quando o overlay é embaixo.
- **Humanos no comando:** `brief.yaml`, `approvals.json`, `forja approve` e gate `GATE_FAILED` no render quando `require_approvals` está ligado.
- **Áudio:** o bed do storyboard soma música, áudio embutido do clipe e `sfx`; `clip.audio` aceita keep/duck/mute + gain, e `sfx` exige licença. A narração faz ducking.
- **Âncoras por palavra:** `enter`/`exit.anchor: word` são resolvidos transcrevendo só as cenas que usam âncora, com cache em `work/words/`.
- **MCP:** `forja mcp serve` é stdio/JSON-RPC 2.0 e expõe 8 tools sobre a CLI.
- **Remotion** desenha legendas, cards e overlays; **sem GitHub Actions** no repositório.

## O que validar (nesta ordem)

1. **Leia a fonte de verdade:** `AGENTS.md`, `DESIGN.md`, `README.md`, `docs/index.html`, `prompts/14-google-flow-cenas.md` e os prompts 01/06/08/10/11/13. Não confie em README/testes: confira no código.
2. **Código e contrato:**
   - `config.DEFAULTS["voices"]["provider"]` é `google_ai_studio`; `files` continua aceito como alias; `piper`/`gemini` são opcionais.
   - `tts.source_for` trata `google_ai_studio` e `files` como WAVs do projeto; `piper` roda local; `gemini` exige chave; provider registrado é despachado.
   - `forja init` cria `brief.yaml`/`approvals.json`, liga `require_approvals` e `--no-require-approvals` desliga; `forja approve` grava de forma atômica.
   - O render falha fechado (`GATE_FAILED`) sem as aprovações exigidas e com `approvals.json` inválido.
   - Overlays: validação de preset/texto/posição/estilo/asset; `caption_windows` eleva legenda; `Storyboard.jsx` renderiza `Overlay`.
   - Áudio: o bed inclui música, áudio embutido do clipe (default keep, mute/duck/gain) e `sfx` (asset/file, license.kind, gain/duration); a narração faz ducking.
   - Âncoras por palavra: `timeline` transcreve só cenas com `enter/exit.anchor: word`, cacheia `work/words/`, e falha com `MISSING_PREREQ` em vez de alinhar no chute.
   - MCP: `forja mcp serve` fala JSON-RPC 2.0 por stdio, lista 8 tools e chama a CLI; stdout só protocolo, sem segredos.
   - `forja doctor` mostra o provider correto; não exige chave nos modos AI Studio/files/piper.
   - `forja describe`/`providers` listam os providers, o comando `approve` e `mcp serve`.
   - `examples/mcp.json` é JSON válido e usa `forja mcp serve`.
   - Docker: Piper é opcional e não pode ser vendido como setup; Flow não tem chamada de API.
3. **Testes e gates:**
   - `python3 -m pytest -q tests` (deve passar; reporte o número).
   - `python3 scripts/check-prompts.py --expect 15`.
   - `python3 -I scripts/build-doc.py --out /tmp/a.html` duas vezes e `cmp` (doc determinística).
   - `forja --json describe`, `forja --json init /tmp/forja-audit --no-require-approvals`, `forja --json --project /tmp/forja-audit doctor` (sem Docker). Se `forja` não estiver no PATH, use `python3 -m forja`.
   - Handshake MCP manual com `initialize`, `tools/list` e `forja_status` (sem conta/API).
   - **Não rode Docker no Mac** e não use contas reais/AI Studio/Flow.
4. **Documentação e UX:**
   - O guia tem botão de tema claro/escuro funcional e link para o GitHub; funciona em 1280 e 360, sem rolagem horizontal.
   - A seção **Sem Docker** e o `LOCAL.md`/`scripts/local-setup.sh`/`local-setup.ps1` cobrem Windows, macOS e Linux, sem prometer isolamento do Docker e sem exigir Docker/VPS.
   - As ressalvas de AI Studio (conta/termos/limites), Flow (créditos, termos, SynthID, não determinismo, áudio do clipe que entra por padrão e pode ser mutado) e Piper (voz única, GPL, qualidade, não é padrão) estão explícitas.
   - Nenhuma instrução induz a achar que o Forja chama Flow/AI Studio por API, que Piper é o setup ou que uma chave é obrigatória.
5. **Segurança e higiene:**
   - Sem `.env`, mídia, `projects/`, `models/`, chaves ou dados pessoais no repo/pacote.
   - Sem workflows de GitHub Actions/Dependabot.
   - Sem caminhos absolutos do autor, e-mails ou hosts internos.
   - `approvals.json`/`check.json`/`qa.json` inválidos não podem falhar abertos; ids de cue/cena não podem escapar da raiz; subprocessos não herdam segredos.
6. **Pendência dos três itens:** dê um veredito específico para:
   - **Áudio de clipe/sfx:** o bed inclui as duas fontes, `mute` remove o áudio do clipe, `sfx` sem licença falha e o mix/render não ignoram mais esses áudios.
   - **Âncoras por palavra:** `enter`/`exit.anchor: word` usam os tempos do Whisper, o cache funciona e a falha vira `MISSING_PREREQ`; não há fallback silencioso.
   - **MCP:** `initialize`, `tools/list` e `tools/call` funcionam por stdio, com 8 tools e sem segredos no stdout.
   Se algum estiver incompleto, marque **pendência** com arquivo:linha e correção; se completo, escreva **sem pendência**.

7. **Procure bugs específicos:** provider padrão divergente, alias `google_ai_studio` quebrado, `init` sem gate, gate que não falha, overlay que colide com legenda, áudio de clipe/sfx fora do bed, âncora por palavra caindo no `scene_start` sem erro, MCP vazando log no stdout, `Piper` no caminho padrão, Flow descrito como API, testes que só comparam texto de comando, doc com link externo indevido, contagem de prompts inconsistente.

## Saída esperada

Entregue um relatório curto e verificável:

1. **Veredito:** `aprovado`, `aprovado com ressalvas` ou `reprovado`, mais a linha **“os três itens: sem pendência”** ou a lista de pendências.
2. **Achados** por severidade (`crítico`, `alto`, `médio`, `baixo`), cada um com arquivo:linha, evidência (comando/saída ou trecho), impacto e correção sugerida.
3. **O que você executou** e o resultado literal (testes, check-prompts, doc determinística, `describe`/`doctor`).
4. **O que não verificou** e por quê (ex.: geração real no AI Studio/Flow, Docker, Windows, áudio ouvido).
5. **Sugestões de patch** (sem aplicar).

Regras: **não altere arquivos, não faça commit/push, não publique, não use GitHub Actions, não imprima segredos e não gaste créditos.** Se algo for crítico, apenas relate com o menor comando que reproduz. O dono decide o que corrigir.
