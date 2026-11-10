# Roadmap

## Entregue no v0.1

- Núcleo: config, cues, tts (provider `files` + `mock` + `gemini` opcional), schedule, subs, mixlib,
  render, qa, probe, transcribe.
- Plataforma: erros estruturados, eventos, cache por hash, registro de provedores e workflows,
  `describe`/`status`/`doctor`, envelope `--json` e códigos de saída `0..5`.
- Workflow `dub` completo (clip, orig, transcribe, check, voices, schedule, mix, render, qa).
- Workflow `storyboard` (validate, voices, timeline, mix, render, qa) com legendas por cena.
- Vozes com as contas do usuário: provider `files` lê `voices/<id>.wav`; o agente/humano gera na
  interface que escolher. Nenhuma chave de API é obrigatória.
- Imagem Docker `linux/amd64`, usuário não-root, caps removidas; Chromium opcional em container
  com CDP só em loopback.
- 14 prompts operacionais, skill do agente, guia web offline (`docs/index.html`), exemplo
  `examples/storyboard-demo/`.

## Em aberto (ordem sugerida)

1. **Fluxo de conta validado ponta a ponta com usuários reais**: o provider `files` foi testado com
   WAVs sintéticos; falta validar a geração pela interface de cada provedor (download do áudio,
   formato, nomes) em Windows/Linux e com contas reais.
2. **Provedor por API real**: `voices.provider: gemini` é opcional; o schema do TTS só foi testado
   com `mock`. Falta um teste ponta a ponta com uma chave real, um vídeo curto e revisão auditiva.
3. **Áudio de clipe e `sfx` no storyboard**: o v1 ignora o áudio embutido dos clipes e a camada
   `sfx` (avisa `CLIP_AUDIO_IGNORED`/`SFX_IGNORED`). Falta mixar os dois no bed.
4. **Âncoras por palavra**: `resolve_timeline` cai para `scene_start` quando a âncora é uma palavra
   (não há alinhamento por palavra no storyboard). Integrar timestamps por palavra do Whisper.
5. **`kit.ps1` testado em Windows**: o espelho existe, mas nunca rodou em Windows de verdade.
   Testar PowerShell 5.1/7, caminhos com espaço e Docker Desktop/WSL2.
6. **Provedores de clipe por IA**: `clip` hoje é arquivo local. Falta provedor por API com
   `estimate()` de custo antes de gastar e cache por hash.
7. **Imagem publicada**: a imagem é construída localmente. Publicar em registry (GHCR/Docker Hub)
   exige decisão do mantenedor e revisão de licenças (GPL do ffmpeg/Chromium).
8. **MCP fino** (`forja mcp serve`, stdio, ~8 tools) sobre a mesma CLI/envelope.
9. **`plan --json`**: dry-run com custo estimado, cache hits e migrações de `schema_version`.
10. **QA de conteúdo**: consistência entre fala, cards e documentos; golden por cena (SSIM/VMAF).
11. **Diarização e OCR de tarja** para identificar quem fala e as janelas de lower-third sem
    trabalho manual.
12. **Transições além de crossfade, publicador (YouTube/Drive), render distribuído.**
