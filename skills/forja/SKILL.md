---
name: forja
description: Gera e dubla vídeos por linha de comando (dublagem EN→pt-BR estilo documentário, legendas embutidas, vídeos por cenas com narração, cards e trilha). Use quando o usuário pedir para dublar, legendar, narrar, montar ou revisar um vídeo, ou mencionar forja, cues.json, storyboard ou kit de vídeo.
license: MIT
compatibility: Requer Docker (imagem do kit) ou Python 3.9+, ffmpeg com libass, Node 20+ (Remotion). Rede só para o provedor de voz/modelos que o usuário escolher.
metadata:
  version: "0.1"
---

# Como operar a forja

Você opera a CLI `forja` (no kit: `./kit.sh run ...`; instalada: `forja ...`). **Sempre use `--json`** e leia o campo `next_actions`.

## Ciclo
0. Projeto novo: `forja init <dir>` (sem `--source`) cria o workflow `storyboard`; `forja init <dir> --source <video>` cria `dub`.
1. `forja --json --project <dir> status` → estado de cada passo e a **próxima ação**.
2. Faça o que o passo pede (alguns passos são **seus**: escrever `cues.json`, `lower_thirds.json`, `config.yaml`, `storyboard.yaml` e as vozes em `voices/`).
3. `forja --json --project <dir> run [--only passo]` → roda só o que mudou (cache por hash). Falhou? Leia `error.code` + `error.hint`; `retryable: true` pode repetir, o resto corrija a causa.
4. `forja --json --project <dir> qa --strict` antes de entregar. Exit `1` = reprovado: corrija os `issues`.
5. Pare e **pergunte ao humano** em: escolha de voz, texto final dos cues, consentimento/aviso de IA e qualquer gasto com API além do combinado.

## Vozes
O padrão é `voices.provider: files`: **o humano gera as vozes com a conta/ferramenta dele** e você salva um WAV PCM por cue em `<projeto>/voices/<id>.wav`. O kit valida, normaliza, mixa e renderiza. Não peça chave de API nesse modo. Provedores por API são opcionais e configurados pelo humano no `config.yaml`/`.env`.

## Descobrir
`forja --json describe` lista comandos, workflows, passos (entradas/saídas), provedores (e se a variável da chave está definida), códigos de erro e o schema do `config.yaml`.

## Regras duras
- As contas são do humano. Nunca copie login, cookie, perfil de navegador ou chave. Se houver provedor por API, a chave só existe no ambiente e **nunca** é impressa, gravada em arquivo, commit ou log; `doctor`/`providers` só dizem "definida/ausente".
- Tempos em **segundos**, relativos ao início do trecho. Não edite `work/` (é gerado).
- Texto de dublagem: caber no tempo (≈ 2,8 palavras/s); encurte o texto, **não** acelere a voz acima de 1,2×.
- Voz sintética de pessoa real ⇒ aviso de IA no vídeo + consentimento (ver `prompts/12-consentimento-e-aviso.md`).

## Arquivos
Agente escreve: `cues.json`, `lower_thirds.json`, `config.yaml`, `storyboard.yaml`, `assets/` e `voices/<id>.wav`. Gerados: `work/*`, `out/video.mp4`, `out/legendas.srt`, `out/qa.json`.
