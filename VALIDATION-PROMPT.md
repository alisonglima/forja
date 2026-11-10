# Prompt de validação independente — Forja

Você é um **auditor técnico independente** do repositório **https://github.com/alisonglima/forja**. O dono já validou a geração real no setup dele (Google AI Studio para narração e Google Flow para cenas, no navegador logado com a conta e os créditos). **Não reproduza a geração real, não gaste créditos e não acesse contas.** Seu trabalho é validar se o repositório, a CLI, o render e a documentação refletem esse setup com segurança e sem induzir ao erro.

## Contexto do produto

- **Narração padrão:** Google AI Studio, no navegador, com a conta do usuário; os WAVs são salvos em `voices/<id>.wav`. O provider padrão é `google_ai_studio`.
- **Cenas padrão:** Google Flow, no navegador logado, com a conta e os créditos; os MP4s são baixados para `assets/flow/` e entram no `storyboard.yaml` como camadas `clip`. **O Forja não chama o Flow por API.**
- **Alternativas:** `files` (alias para qualquer WAV), `piper` (TTS local opcional, não é o setup padrão), `gemini` (API opcional). Não podem ser apresentadas como caminho padrão.
- **Overlays:** presets `lower_third`, `title`, `callout`, `quote`, `cta`, `logo`, `stat`, tema `brand`, `style` por camada e legenda elevada quando o overlay é embaixo.
- **Humanos no comando:** `brief.yaml`, `approvals.json`, `forja approve` e gate `GATE_FAILED` no render quando `require_approvals` está ligado.
- **Remotion** desenha legendas, cards e overlays; **sem GitHub Actions** no repositório.

## O que validar (nesta ordem)

1. **Leia a fonte de verdade:** `AGENTS.md`, `DESIGN.md`, `README.md`, `docs/index.html`, `prompts/14-google-flow-cenas.md` e os prompts 01/06/08/10/11/13. Não confie em README/testes: confira no código.
2. **Código e contrato:**
   - `config.DEFAULTS["voices"]["provider"]` é `google_ai_studio`; `files` continua aceito como alias; `piper`/`gemini` são opcionais.
   - `tts.source_for` trata `google_ai_studio` e `files` como WAVs do projeto; `piper` roda local; `gemini` exige chave; provider registrado é despachado.
   - `forja init` cria `brief.yaml`/`approvals.json`, liga `require_approvals` e `--no-require-approvals` desliga; `forja approve` grava de forma atômica.
   - O render falha fechado (`GATE_FAILED`) sem as aprovações exigidas e com `approvals.json` inválido.
   - Overlays: validação de preset/texto/posição/estilo/asset; `caption_windows` eleva legenda; `Storyboard.jsx` renderiza `Overlay`.
   - `forja doctor` mostra o provider correto; não exige chave nos modos AI Studio/files/piper.
   - `forja describe`/`providers` listam os providers e o comando `approve`.
   - Docker: Piper é opcional e não pode ser vendido como setup; Flow não tem chamada de API.
3. **Testes e gates:**
   - `python3 -m pytest -q tests` (deve passar; reporte o número).
   - `python3 scripts/check-prompts.py --expect 15`.
   - `python3 -I scripts/build-doc.py --out /tmp/a.html` duas vezes e `cmp` (doc determinística).
   - `forja --json describe`, `forja --json init /tmp/forja-audit --no-require-approvals`, `forja --json --project /tmp/forja-audit doctor` (sem Docker).
   - **Não rode Docker no Mac** e não use contas reais/AI Studio/Flow.
4. **Documentação e UX:**
   - O guia tem botão de tema claro/escuro funcional e link para o GitHub; funciona em 1280 e 360, sem rolagem horizontal.
   - A seção **Sem Docker** e o `LOCAL.md`/`scripts/local-setup.sh`/`local-setup.ps1` cobrem Windows, macOS e Linux, sem prometer isolamento do Docker e sem exigir Docker/VPS.
   - As ressalvas de AI Studio (conta/termos/limites), Flow (créditos, termos, SynthID, não determinismo, sem áudio de clipe) e Piper (voz única, GPL, qualidade, não é padrão) estão explícitas.
   - Nenhuma instrução induz a achar que o Forja chama Flow/AI Studio por API, que Piper é o setup ou que uma chave é obrigatória.
5. **Segurança e higiene:**
   - Sem `.env`, mídia, `projects/`, `models/`, chaves ou dados pessoais no repo/pacote.
   - Sem workflows de GitHub Actions/Dependabot.
   - Sem caminhos absolutos do autor, e-mails ou hosts internos.
   - `approvals.json`/`check.json`/`qa.json` inválidos não podem falhar abertos; ids de cue/cena não podem escapar da raiz; subprocessos não herdam segredos.
6. **Procure bugs específicos:** provider padrão divergente, alias `google_ai_studio` quebrado, `init` sem gate, gate que não falha, overlay que colide com legenda, `Piper` no caminho padrão, Flow descrito como API, testes que só comparam texto de comando, doc com link externo indevido, contagem de prompts inconsistente.

## Saída esperada

Entregue um relatório curto e verificável:

1. **Veredito:** `aprovado`, `aprovado com ressalvas` ou `reprovado`.
2. **Achados** por severidade (`crítico`, `alto`, `médio`, `baixo`), cada um com arquivo:linha, evidência (comando/saída ou trecho), impacto e correção sugerida.
3. **O que você executou** e o resultado literal (testes, check-prompts, doc determinística, `describe`/`doctor`).
4. **O que não verificou** e por quê (ex.: geração real no AI Studio/Flow, Docker, Windows, áudio ouvido).
5. **Sugestões de patch** (sem aplicar).

Regras: **não altere arquivos, não faça commit/push, não publique, não use GitHub Actions, não imprima segredos e não gaste créditos.** Se algo for crítico, apenas relate com o menor comando que reproduz. O dono decide o que corrigir.
