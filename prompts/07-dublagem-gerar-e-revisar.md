Você é meu produtor de pós. O elenco foi aprovado por mim e as vozes estão em `projects/<NOME>/voices/<id>.wav` (ou no provedor por API que eu configurei). Gere o vídeo e **verifique** o resultado — não declare pronto só porque o comando terminou.

Ciclo: `init` → `transcribe` → `frames` → `cues.json` → `check` → `voices` → `run` → `qa --strict`. Aqui estamos no `run` e no `qa --strict`.

1. Confirme que `approvals.json` tem `script` e `voice` aprovados; se não, pare e me peça a aprovação (`./kit.sh run --project /projects/<NOME> --json approve --script --voice --by <MEU_NOME>`). Depois rode tudo: `./kit.sh run --project /projects/<NOME> --json run --strict`. Ordem interna: `check → voices → schedule → mix → render → qa`. Saídas em `out/`: `video.mp4`, `legendas.srt`, `qa.json`.
2. Rode o gate obrigatório: `./kit.sh run --project /projects/<NOME> --json qa --strict`. **Exit 1 = reprovado**: corrija e repita; não entregue com erro.
3. Leia `out/qa.json`. Cada issue tem `level` (error/warn), `code` e mensagem. Resolva assim:
   - `OVERFLOW` / `TEMPO_CLAMPED`: a fala não coube no tempo. **Reescreva o texto do cue mais curto** em `cues.json`, regenere a voz em `voices/<id>.wav` e rode `./kit.sh run --project /projects/<NOME> --json voices --only <id>`; depois `./kit.sh run --project /projects/<NOME> --json schedule`. Não aumente `max_tempo` além de 1,2 sem eu aprovar.
   - `CPS` / `LINES` / `LINE_LONG`: legenda cansativa de ler — encurte o texto.
   - `TAG_OVERLAP`: a legenda cobre a tarja de nome — confira `lower_thirds.json`.
   - `LUFS` / `TRUE_PEAK`: volume final fora do alvo (−16 LUFS, pico ≤ −1 dBTP) — rode `mix` de novo e me avise se persistir.
4. **Confira com os olhos**: extraia 6 quadros (início, 3 no meio onde há tarja de nome, 2 no fim) com `ffmpeg` dentro do container (`./kit.sh shell`) e abra as imagens. Veja se a legenda está legível, não cobre rosto nem tarja, e muda de posição quando a tarja aparece.
5. Faça uma **checagem de escuta guiada** para mim (você não ouve áudio): liste, cue a cue, texto + tempo de início/fim + falante, e me peça para ouvir os 3 trechos de maior risco (fala mais longa, fala mais rápida, pronúncia de nome estrangeiro).
6. Entrega: copie `out/video.mp4` e `out/legendas.srt` para onde eu pedir.

Antes de publicar em qualquer lugar: o vídeo contém voz sintética de pessoas reais — siga o roteiro do arquivo `12-consentimento-e-aviso.md` e **pergunte a mim sobre o consentimento**. Use `forja status` (no kit, `./kit.sh run --project /projects/<NOME> --json status`) para confirmar o estado. Reporte o resultado do `qa --strict`, os quadros conferidos, os riscos de escuta e o que ficou pendente. Diga o que **não verificou**: o áudio em si, a naturalidade e a emoção da voz e a sincronia labial.
