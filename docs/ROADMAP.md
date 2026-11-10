# Roadmap

## Entregue no v0.1

- Núcleo: config, cues, tts (`files`, `piper`, `mock`, `gemini` opcional), schedule, subs, mixlib,
  render, qa, probe, transcribe.
- Plataforma: erros estruturados, eventos, cache por hash, registro de provedores e workflows,
  `describe`/`status`/`doctor`, envelope `--json` e códigos de saída `0..5`.
- Workflow `dub` completo (clip, orig, transcribe, check, voices, schedule, mix, render, qa).
- Workflow `storyboard` (validate, voices, timeline, mix, render, qa) com legendas por cena.
- **Voz local** (`piper`) com modelo pt-BR na imagem; `files` para contas próprias; `gemini` opcional.
- **Overlays profissionais** (`lower_third`, `title`, `callout`, `quote`, `cta`, `logo`, `stat`),
  tema `brand`, `style` por camada e legenda que sobe quando o overlay é embaixo.
- **Brief e aprovação humana**: `brief.yaml`, `approvals.json`, comando `forja approve` e gate
  `GATE_FAILED` no render quando `project.require_approvals` está ligado.
- Imagem Docker `linux/amd64`, usuário não-root, caps removidas; Chromium opcional em container
  com CDP só em loopback.
- 14 prompts, skill do agente, guia offline (`docs/index.html`), exemplo de storyboard.

## Em aberto (ordem sugerida)

1. **Build Docker com Piper validado em Linux x86_64**: o provider foi testado com Piper real no
   host e o Remotion/Chrome local; falta construir a imagem final e rodar o E2E dentro dela.
2. **Fluxo de conta validado ponta a ponta com usuários reais**: o provider `files` foi testado com
   WAVs sintéticos; falta validar a geração pela interface de cada provedor (download, formato,
   nomes) em Windows/Linux.
3. **Windows**: `kit.ps1` e Docker Desktop/WSL2 ainda não foram executados em Windows real.
4. **Áudio de clipe e `sfx`**: o v1 ignora o áudio embutido dos clipes e a camada `sfx`
   (`CLIP_AUDIO_IGNORED`/`SFX_IGNORED`). Falta mixar os dois no bed.
5. **Âncoras por palavra**: `resolve_timeline` cai para `scene_start` quando a âncora é uma palavra
   (não há alinhamento por palavra no storyboard). Integrar timestamps por palavra do Whisper.
6. **MCP fino** (`forja mcp serve`, stdio, ~8 tools) sobre a mesma CLI/envelope, para agentes que
   preferem tools a shell.
7. **Provedores de clipe por IA**: `clip` hoje é arquivo local. Falta provedor por API com
   `estimate()` de custo antes de gastar e cache por hash.
8. **Imagem publicada**: a imagem é construída localmente. Publicar em registry (GHCR/Docker Hub)
   exige decisão do mantenedor e revisão de licenças (GPL do ffmpeg/Piper/Chromium).
9. **`plan --json`**: dry-run com custo estimado, cache hits e migrações de `schema_version`.
10. **QA de conteúdo e de overlays**: consistência entre fala, cards e documentos; golden por cena
    (SSIM/VMAF) e checagem automática de safe area/colisão de overlays.
11. **Diarização e OCR de tarja** para identificar quem fala e as janelas de lower-third sem
    trabalho manual.
12. **Transições além de crossfade, publicador (YouTube/Drive), render distribuído.**
