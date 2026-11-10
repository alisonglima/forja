# Changelog

Todas as mudanças notáveis deste projeto são documentadas aqui.
O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto adere a
[Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [0.1.0] — 2026-11-10

### Adicionado

- CLI `forja` com workflows `dub` (dublagem EN→pt-BR) e `storyboard` (vídeo por cenas).
- Provider de voz `files`: o usuário gera as vozes com a própria conta/ferramenta e salva
  `voices/<id>.wav`; nenhuma chave de API é obrigatória.
- Provider `piper`: TTS neural local com voz pt-BR na imagem, sem conta/API.
- Providers opcionais `gemini` (API) e `mock` (testes), com contrato de provedores extensível.
- Overlays profissionais (`lower_third`, `title`, `callout`, `quote`, `cta`, `logo`, `stat`) com tema
  `brand`, estilo por camada e legenda elevada quando o overlay fica embaixo.
- `brief.yaml`, `approvals.json`, comando `forja approve` e gate humano `GATE_FAILED` no render.
- Envelope `--json`, `describe`, `status` com `next_actions`, cache por hash, eventos e códigos de
  saída `0..5`.
- QA como gate (`qa --strict`), legendas queimadas via Remotion e mixagem com ducking/loudness.
- Kit Docker `linux/amd64`, usuário não-root, `cap_drop: ALL` e `no-new-privileges`.
- Chromium opcional em container, com CDP só em `127.0.0.1` e senha.
- 14 prompts operacionais, skill para agentes, guia offline e exemplo de storyboard.
- Documentação em GitHub Pages, templates de issue/PR e política de segurança.

### Segurança

- IDs de cue/cena validados antes de virar nome de arquivo.
- Gates de QA/check falham fechados com JSON ilegível.
- Subprocessos não herdam variáveis com cara de segredo.
- Config numérica validada antes de entrar em filtros do ffmpeg.
- Escrita atômica de JSON e cache.
- Aprovações falham fechadas com JSON inválido; overlays validam preset/texto/posição/estilo/asset.
