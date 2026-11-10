# Changelog

Todas as mudanças notáveis deste projeto são documentadas aqui.
O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto adere a
[Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Corrigido

- `.env.example`, `kit.sh` e `kit.ps1` passam a indicar `google_ai_studio` como provider padrão
  (`files` é alias e lê os mesmos WAVs).
- Guia e prompts 08/14 descrevem a política de áudio do Flow: pedir somente SFX e som ambiente,
  sem fala/narração/diálogo/música; o áudio embutido entra no bed e `audio: {mode: mute}` remove.
- Quickstart do guia cita `google_ai_studio` antes de `piper`; `piper` fica como alternativa offline opcional.
- Removido bullet duplicado de âncoras por palavra no prompt 08.
- `DESIGN.md` registra `MISSING_PREREQ` em âncora por palavra não resolvida, `sfx.start` relativo à
  cena, aviso `CLIP_OUT_S_UNSUPPORTED`, cache de `voices/*.wav`, WAV estéreo convertido e
  `next_actions` com `--project`.

## [0.1.0] — 2026-11-10

### Adicionado

- CLI `forja` com workflows `dub` (dublagem EN→pt-BR) e `storyboard` (vídeo por cenas).
- Provider padrão `google_ai_studio`: o usuário gera as vozes no AI Studio e salva
  `voices/<id>.wav`; nenhuma chave de API é obrigatória. `files` é alias genérico.
- Provider `piper`: TTS neural local opcional com voz pt-BR na imagem, sem conta/API.
- Providers opcionais `gemini` (API) e `mock` (testes), com contrato de provedores extensível.
- Overlays profissionais (`lower_third`, `title`, `callout`, `quote`, `cta`, `logo`, `stat`) com tema
  `brand`, estilo por camada e legenda elevada quando o overlay fica embaixo.
- Áudio de clipe e `sfx` no bed, com `clip.audio.mode`/`gain_db` e licença obrigatória de `sfx`.
- Âncoras por palavra no `enter`/`exit`, com transcrição faster-whisper e cache em `work/words/`.
- Servidor MCP stdio (`forja mcp serve`) com 8 tools sobre a CLI.
- `brief.yaml`, `approvals.json`, comando `forja approve` e gate humano `GATE_FAILED` no render.
- Envelope `--json`, `describe`, `status` com `next_actions`, cache por hash, eventos e códigos de
  saída `0..5`.
- QA como gate (`qa --strict`), legendas queimadas via Remotion e mixagem com ducking/loudness.
- Kit Docker `linux/amd64`, usuário não-root, `cap_drop: ALL` e `no-new-privileges`.
- Chromium opcional em container, com CDP só em `127.0.0.1` e senha.
- 15 prompts operacionais, skill para agentes, guia offline, alternativa sem Docker e exemplo de storyboard.
- Documentação em GitHub Pages, templates de issue/PR e política de segurança.

### Segurança

- IDs de cue/cena validados antes de virar nome de arquivo.
- Gates de QA/check falham fechados com JSON ilegível.
- Subprocessos não herdam variáveis com cara de segredo.
- Config numérica validada antes de entrar em filtros do ffmpeg.
- Escrita atômica de JSON e cache.
- Aprovações falham fechadas com JSON inválido; overlays validam preset/texto/posição/estilo/asset.
