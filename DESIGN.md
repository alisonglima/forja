# forja — contrato do CLI (v1)

Dublagem EN→pt-BR estilo documentário: voz original ao fundo, narração por cima, legenda embutida.
O CLI faz **só o determinístico**. Transcrever bem, adaptar o texto, escolher elenco e identificar quem fala
é julgamento (LLM ou humano): fica nos prompts de `prompts/`, rodados pelo agente do próprio usuário.

Python 3.9+, pacote `forja/`, dependências: `pyyaml`, `numpy`, `scipy`, `faster-whisper` (só `transcribe`).
Tudo que toca rede, disco pesado ou subprocesso é **injetável** (parâmetro `run=`/`post=`), para teste sem mídia.
Tempos sempre em **segundos** (float), relativos ao início do clip (já cortado).

## Pastas de um projeto

```
meu-video/
  config.yaml
  input/source.mp4        # vídeo original (qualquer duração)
  cues.json               # escrito pelo agente (ver abaixo)
  lower_thirds.json       # [[ini, fim], ...] janelas em que há tarja de nome no original
  work/                   # tudo gerado, descartável
    clip.mp4  orig.wav  transcript.json  voices/<id>.wav  schedule.json  subs.json  mix.wav
    frames/  cache/tts/<sha256>.wav
  out/video.mp4  out/legendas.srt  out/qa.json
```

## config.yaml (defaults em `config.DEFAULTS`)

```yaml
project:    {name: meu-video, source_lang: en, target_lang: pt-BR, require_approvals: true}
input:      {video: input/source.mp4, start: 0.0, duration: null}     # null = até o fim
transcribe: {model: large-v3-turbo, language: en, compute_type: int8, vad: true}
voices:
  provider: google_ai_studio       # google_ai_studio | files | piper | gemini | mock
  input_dir: voices                # AI Studio/files: WAVs do usuário em <projeto>/voices/<id>.wav
  model: gemini-3.8-flash-tts      # só provider gemini (opcional)
  api_key_env: GEMINI_API_KEY      # NOME da variável; o valor nunca vai no arquivo
  piper:                           # provider piper (local, sem conta/API)
    binary: piper
    model: /opt/piper/pt_BR-faber-medium.onnx
    length_scale: 1.0
    speaker: null
  min_tempo: 0.90
  max_tempo: 1.20
  glossary: {}                     # {"Marca": "Mar-ka"} aplicado ao texto antes do TTS
  cast:                            # papel -> voz
    narrator: {voice: Leda,   style: "calm, warm, measured"}
    default:  {voice: Charon, style: "natural, conversational"}
brand:      {primary: "#C24B2A", ink: "#1A1714", paper: "#F6F1E8", accent: "#C24B2A",
             font: "Liberation Sans", logo: "", safe_margin: 48}
mix:        {voice_lufs: -18.0, duck_narrator_db: -20.0, duck_speech_db: -13.0, ramp_s: 0.30,
             orig_gain: 0.90, target_lufs: -16.0, true_peak: -1.5, lra: 11.0}
render:     {width: 1280, height: 720, fps: 30, font_size: 32, max_chars_line: 42, max_lines: 2, cps_max: 20.0}
qa:         {max_wer: 0.15, max_overlap_frames: 2, lufs_tol: 1.0, max_true_peak: -1.0}
```

## cues.json (o agente escreve)

Lista de objetos: `{"id": "A", "speaker": "narradora", "role": "narrator"|"speech",`
`"t0": 3.43, "t1": 7.37, "lead": 0.3, "text": "...pt-BR...", "source_text": "...en...", "voice": "Puck", "style": "..."}`

- `id` único (string). `t0` início da fala **original**; `t1` fim da fala original. `lead` (default 0.3) atraso da narração.
- `role=speech`: a narração cobre a pessoa e a voz original fica ao fundo (ducking −13 dB).
  `role=narrator`: narração própria (ducking −20 dB). `voice`/`style` opcionais (senão vem de `voices.cast`).

## Módulos e funções públicas (assinaturas exatas)

### `config.py`
- `DEFAULTS: dict`; `class ConfigError(ValueError)`.
- `load_config(path) -> dict`: lê YAML, **deep-merge** sobre `DEFAULTS`, valida (`voices.min_tempo <= max_tempo`, `render.fps > 0`,
  `voices.provider in {"google_ai_studio","files","piper","gemini","mock"}` ou registrado, `input_dir` relativo sem `..`, `project.require_approvals` booleano,
  `brand` com cores `#RRGGBB`/fonte/margem e `piper` com binário/modelo/length_scale/speaker válidos, `mix.true_peak <= 0`); levanta `ConfigError` com a chave no texto.
- `write_default_config(path, **overrides) -> None`: grava `DEFAULTS` + overrides rasos por seção, recusa sobrescrever (`FileExistsError`).

### `cues.py`
- `ISSUE = {"level": "error"|"warn", "id": str|None, "code": str, "msg": str}`
- `load_cues(path) -> list[dict]` (aplica `lead=0.3` e `role="speech"` quando ausentes).
- `estimate_duration_s(text: str) -> float` = nº de palavras / 2.8.
- `split_lines(text, max_chars, max_lines) -> list[str] | None`: quebra por palavras (nunca no meio), preferindo
  depois de pontuação (`, ; : . ? !`); `None` se não couber em `max_lines` linhas de `max_chars`.
- `validate_cues(cues, cfg) -> list[ISSUE]` — códigos: `MISSING_FIELD` (error: id,t0,t1,text), `DUP_ID` (error), `BAD_ID` (error: id inseguro para nome de arquivo),
  `T_ORDER` (error: t1 <= t0), `LINES` (error: `split_lines` devolve None), `CPS` (warn: caracteres/s > `render.cps_max`
  sobre a janela `t1-t0`), `BUDGET` (error: `estimate_duration_s(text)` > `(t1-t0-lead)*max_tempo*1.1`), `OVERLAP` (warn: t0 < t1 do anterior).

### `probe.py`
- `probe_video(path, run=subprocess.run) -> {"duration","width","height","fps","has_audio"}` via `ffprobe -print_format json`.
  Levanta `RuntimeError` se não houver stream de vídeo.

### `schedule.py`
- `speech_bounds(samples: np.ndarray, sr: int, thr: float = 0.02) -> tuple[float, float] | None`: início/fim (s) da fala por
  envelope absoluto suavizado (média móvel 20 ms); **`None` se nada passa do limiar** (nunca `IndexError`).
- `plan(cues, durations: dict[id->float], cfg, total: float, bounds: dict[id->(float,float)|None]) -> dict`:
  para cada cue (em ordem de `t0`): `start = t0 + lead`; janela-alvo termina em `t1` (speech) ou no `start` do próximo cue (narrator;
  último: `total`); `speech_len = bounds fim-ini` (ou `durations[id]` se `None`); `tempo = speech_len / (alvo - start)` limitado a
  `[min_tempo, max_tempo]` — **nunca fora de `[0.5, 2.0]`**; `end = start + speech_len/tempo`; `lag = max(0, end - alvo)`.
  Retorna `{"total": total, "cues": [{"id","start","end","tempo","trim_start","trim_end","lag","warnings":[...]}], "warnings": [...]}`;
  `warnings` inclui `TEMPO_CLAMPED` e `OVERFLOW` (lag > 0.25 s). Não empurra o cue seguinte.

### `subs.py`
- `build_subs(schedule, cues, lower_thirds, cfg) -> list[dict]`: um evento por cue (ou vários, se o texto exceder
  `max_lines`×`max_chars_line`, repartindo o tempo proporcional ao nº de caracteres e quebrando em pontuação);
  evento = `{"start","end","lines":[...],"narrador":bool,"raised":bool}`; `raised` = há interseção com alguma janela de
  `lower_thirds` (margem 0.2 s). Eventos nunca se sobrepõem (`end <= próximo start`), duração mínima 0.8 s quando houver espaço.
- `to_srt(subs) -> str` (formato `HH:MM:SS,mmm`, índice a partir de 1, linhas separadas por `\n`).

### `mixlib.py`
- `duck_envelope(total_s, sr, intervals: list[tuple[float,float,float]], ramp_s) -> np.ndarray`:
  ganho linear por amostra, 1.0 fora; cada `(ini, fim, ganho)` aplica `ganho` com rampa (janela Hann) de `ramp_s` na entrada
  e na saída; sobreposição usa o **menor** ganho.
- `db_to_gain(db) -> float`.
- `loudnorm_measure_cmd(wav, target, tp, lra) -> list[str]` e `loudnorm_apply_cmd(wav, out, target, tp, lra, measured: dict) -> list[str]`:
  argumentos do ffmpeg (2 passes, `linear=true`, `measured_*`); `parse_loudnorm_json(stderr: str) -> dict` extrai o bloco JSON do fim.
- `voice_gain_cmd(wav, out, lufs) -> list[str]` (um `loudnorm` de 1 passe por fala: `I=lufs:TP=-1.5:LRA=7`).

### `tts.py`
- `apply_glossary(text, glossary) -> str` (substitui palavra inteira, respeita maiúsculas exatas).
- `cache_key(provider, model, voice, style, text) -> str` (sha256 hex de JSON canônico).
- `build_gemini_request(model, voice, style, text) -> tuple[str, dict, dict]` = `(url, headers_sem_chave, body)`; a chave é
  adicionada pelo chamador no header `x-goog-api-key`. **Isolar aqui todo o formato da API** (um arquivo só).
- `parse_gemini_response(resp: dict) -> bytes` (WAV; decodifica base64 do último item de áudio; `ValueError` se faltar).
- `mock_wav(text, sr=24000) -> bytes`: tom determinístico com duração `estimate_duration_s(text)` (provider `mock`).
- `input_dir(cfg) -> str`: pasta relativa das vozes fornecidas (default `voices`).
- `provided_wav(cue, cfg, root) -> Path`: resolve `<root>/<input_dir>/<id>.wav`, exige `id` seguro e WAV válido; ausente → `MISSING_INPUT`, inválido → `CONFIG_INVALID`.
- `piper_wav(cue, cfg, cache_dir, env=None, run=None) -> bytes`: roda `piper --model ... --output_file ...` com o texto no stdin; ausente → `MISSING_PREREQ`, exit ≠ 0 → `PROVIDER_ERROR`; o WAV bruto é normalizado por `synthesize`.
- `source_for(cue, cfg, root, cache_dir, post, env=None, sleep=..., run=None) -> Path`: providers `google_ai_studio`/`files` → `provided_wav`; senão → `synthesize`.
- `synthesize(...)`: `mock`/`piper`/`gemini` embutidos; qualquer outro `voices.provider` é resolvido por `registry.get("tts", provider)`, cuja fábrica devolve `callable(cue, cfg, cache_dir, post=..., env=...) -> bytes | Path` com o WAV bruto. Plugins de `forja.providers` são carregados no início da CLI.
- `synthesize(cue, cfg, cache_dir, post, env=os.environ, sleep=time.sleep) -> pathlib.Path`: cache hit não chama `post`;
  3 tentativas com backoff (1, 2, 4 s) em erro 429/5xx; 4xx ≠ 429 não repete; chave ausente → `RuntimeError("variável X não definida")`;
  valida WAV (RIFF, >0 amostras, mono) e reamostra para 24 kHz se necessário.

### `transcribe.py`
- `normalize_segments(raw: list[dict]) -> dict`: `{"language","duration","segments":[{"start","end","text","words":[{"word","start","end"}]}]}`
  (strip de espaços, descarta segmento vazio, garante start<=end).
- `run_transcribe(wav, cfg, model_dir) -> dict` (import tardio de `faster_whisper`; não testado em unidade).

### `render.py`
- `build_props(clip_name, total, subs, lower_thirds, cfg) -> dict` (entrada do template Remotion; inclui `brand`).
- `remotion_cmd(entry, props_path, public_dir, out) -> list[str]`; `mux_cmd(video, wav, out) -> list[str]`
  (`-c:v copy -c:a aac -b:a 192k -shortest`, `-movflags +faststart`).

### `qa.py`
- `wer(ref: str, hyp: str) -> float` (palavras minúsculas sem pontuação, distância de edição / len(ref)).
- `check_subs(subs, cfg) -> list[ISSUE]` (`CPS`, `LINES`, `LINE_LONG`, `DURATION` < 0.8 s, `OVERLAP`).
- `check_overlap(subs, lower_thirds, cfg) -> list[ISSUE]`: evento **não** `raised` que interseciona janela de tarja por mais de
  `max_overlap_frames`/fps → `error` `TAG_OVERLAP`.
- `check_loudness(report: dict, cfg) -> list[ISSUE]`: `report = {"I","TP"}`; `LUFS` se |I − target| > `lufs_tol`; `TRUE_PEAK` se TP > `max_true_peak`.
- `check_schedule(schedule) -> list[ISSUE]`: `OVERFLOW`, `TEMPO_CLAMPED` viram `warn`; `lag` > 0.6 s vira `error`.
- `summarize(issues) -> {"ok": bool, "errors": int, "warnings": int, "issues": [...]}`.

### `cli.py`
`python -m forja <cmd>`; `main(argv=None) -> int`. Comandos: `init <dir> [--source FILE] [--workflow dub|storyboard] [--force]`, `transcribe`, `frames [--every S]`,
`check`, `voices [--only ID,..] [--force]`, `schedule`, `mix`, `render`, `qa [--strict]`, `run [--strict]` (check→voices→schedule→mix→render→qa).
Todos aceitam `--project DIR` (default `.`). Saída de erro sempre em português, uma linha, exit code 2; `qa --strict` com erro → exit 1.
`check` com qualquer issue `error` → exit 1.

## Convenções de código

- Todo módulo começa com `from __future__ import annotations` (roda em Python 3.9+).
- Só biblioteca padrão + `numpy`, `scipy`, `pyyaml` nos módulos testáveis; `faster_whisper` só dentro de `run_transcribe`.
- Sem `print` em módulos de biblioteca (só em `cli.py`). Sem caminhos absolutos, sem nomes de pessoa/host nos exemplos.
- Testes: `/usr/bin/python3 -m pytest -q tests/test_<modulo>.py`; fixtures sintéticas geradas no próprio teste (numpy), nunca mídia real.

## Template Remotion (`remotion-template/`)

`render.build_props` devolve (e `render` grava em `work/props.json`):

```json
{"clip": "clip.mp4", "durationS": 98.5, "fps": 30, "width": 1280, "height": 720, "fontSize": 32,
 "subs": [{"start": 0.45, "end": 2.99, "lines": ["..."], "narrador": false, "raised": false}],
 "lowerThirds": [[7.3, 8.7]]}
```

O template lê tudo de `getInputProps()`/`--props`: nenhuma constante do vídeo no código. Composição `Legendas`, com
`calculateMetadata` (duração = `durationS*fps`, largura/altura/fps das props). O vídeo vem de `staticFile(props.clip)`
(`--public-dir` aponta para `work/`). Legenda: caixa preta 58% de opacidade, raio 12, texto branco negrito
`fontSize` px (linha = fontSize*1.25), itálico quando `narrador`, fade de 4 quadros, centralizada, `maxWidth` 87,5% da largura.
Posição: borda inferior em 94,5% da altura; quando há tarja (`lowerThirds`, com margem de 0,2 s e rampa de 6 quadros, só se
`raised` for verdadeiro no evento ou a janela intersecta) sobe suavemente para 79,5%. Lê a rampa por `interpolate` com
`inputRange` estritamente crescente mesmo para janelas curtas (< 0,4 s). `OffthreadVideo muted` com `objectFit: "contain"`
sobre fundo preto (não corta vídeo vertical/4:3).

---

# Plataforma `forja` (v2) — camada acima dos módulos

`forja` é uma **ferramenta de geração de vídeo operada por agentes de IA**. A dublagem é o primeiro *workflow*; o segundo é o
*storyboard* (vídeos por cenas, como os do YCE). Os módulos acima (config, cues, tts, schedule, subs, mixlib, render, qa, probe, transcribe)
são **bibliotecas** reutilizadas pelos workflows. A camada nova só orquestra, valida, explica e deixa rastro.

Princípios (valem para todo código novo):
1. **Máquina primeiro**: todo comando aceita `--json` (um único documento JSON no stdout; logs/progresso vão para stderr).
2. **Erro que ensina**: nunca traceback para o usuário; `{"ok": false, "error": {"code","msg","hint","retryable"}}` e exit code por classe.
3. **Idempotente e em cache**: passo só roda se entradas mudaram (hash) ou a saída sumiu; `--force` ignora.
4. **Descobrível**: `forja describe` diz tudo (comandos, workflows, passos, entradas/saídas, provedores, códigos de erro, schemas).
5. **Rastro**: cada passo escreve eventos em `work/events.ndjson`; `forja status` diz o estado e a **próxima ação**.
6. **Extensível sem tocar no núcleo**: provedores e workflows se registram (decorador ou *entry points*).
7. **Segredo nunca no disco do projeto, nunca em log, nunca em `--json`**: só o **nome** da variável de ambiente e um booleano "definida".

## Códigos de saída

`0` ok · `1` gate reprovado (`check`/`qa` com erro) · `2` uso/config inválido · `3` falha externa possivelmente repetível (rede, cota, 5xx)
· `4` pré-requisito ausente (ffmpeg, chave, modelo, navegador) · `5` erro interno (bug).

## Módulos novos (assinaturas exatas)

### `errors.py`
- `ERROR_CODES: dict[str, dict]` com chaves: `CONFIG_INVALID`(2), `USAGE`(2), `GATE_FAILED`(1), `PROVIDER_ERROR`(3), `RATE_LIMITED`(3),
  `NETWORK`(3), `MISSING_PREREQ`(4), `MISSING_KEY`(4), `MISSING_INPUT`(2), `INTERNAL`(5). Cada valor: `{"exit": int, "retryable": bool, "hint": str}`.
- `class ForjaError(Exception)`: `__init__(self, code, msg, hint=None, details=None)`; atributos `code, msg, hint, details, exit_code, retryable`
  (hint/exit/retryable default vêm de `ERROR_CODES[code]`; código desconhecido → `INTERNAL`).
- `error_payload(exc) -> dict` = `{"ok": False, "error": {"code","msg","hint","retryable","details"}}` (exceção não-Forja → `INTERNAL`, sem traceback, `msg` = `str(exc)`).

### `events.py`
- `emit(work_dir, step, status, **fields) -> dict`: anexa uma linha JSON a `<work_dir>/events.ndjson` (cria a pasta) com
  `{"t": ISO-8601 UTC, "step", "status"(started|ok|skipped|failed), ...fields}`; devolve o evento. Valores `Path` viram `str`; **chaves com `key`,
  `token`, `secret`, `password` no nome são descartadas** (defesa contra vazamento).
- `read_events(work_dir, limit=50) -> list[dict]` (últimos `limit`, ordem cronológica; linha corrompida é ignorada).

### `cache.py`
- `hash_inputs(paths, extra=None) -> str`: sha256 de (para cada path existente, ordenado: caminho relativo ao nome do arquivo + tamanho + sha256 do conteúdo)
  + JSON canônico de `extra`. Path ausente entra como marcador `MISSING` (muda o hash quando aparece).
- `class Manifest`: `Manifest(path)`; `.get(step) -> dict|None`; `.put(step, input_hash, outputs: list)`; `.save()`; `.is_fresh(step, input_hash, outputs) -> bool`
  (verdadeiro só se o hash gravado é igual E todas as saídas existem). Arquivo JSON legível; corrompido → vazio.

### `registry.py`
- `KINDS = ("tts", "stt", "render", "clip")`.
- `register(kind, name, *, requires_env=(), network=False, note="")`: decorador de classe/função; registra a fábrica.
  Kind inválido → `ValueError`; nome repetido no mesmo kind → `ValueError`.
- `get(kind, name)` → fábrica (inexistente → `ForjaError("CONFIG_INVALID", ...)` listando os nomes disponíveis).
- `available(kind=None, env=os.environ) -> list[dict]`: `[{"kind","name","requires_env","env_ok": bool,"network","note"}]` (`env_ok` = todas as variáveis definidas e não vazias; **nunca o valor**).
- `load_entry_points(group="forja.providers")` (usa `importlib.metadata`; falha de um plugin vira aviso em `available()` com `"error"`, não derruba).
- `reset_for_tests()`.

### `steps.py`
- `@dataclass Step`: `name: str`, `doc: str`, `inputs: Callable[[Ctx], tuple[list[Path], dict]]`, `outputs: Callable[[Ctx], list[Path]]`, `run: Callable[[Ctx], dict|None]`, `needs: list[str]` (nomes de passos anteriores).
- `@dataclass Ctx`: `root: Path`, `cfg: dict`, `work: Path`, `out: Path`, `env: Mapping`, `log: Callable[[str], None]`, `dry_run: bool`.
- `run_steps(ctx, steps, only=None, force=False) -> list[dict]`: executa na ordem; para cada passo: calcula hash; se fresco e sem `force` → evento `skipped`; senão evento `started`, roda,
  grava no manifesto (`work/manifest.json`), evento `ok` com `ms`. `only` = lista de nomes (executa só esses **mais** os `needs` ainda frescos/ausentes não rodam: apenas valida que existem, senão `ForjaError("MISSING_INPUT")`).
  Exceção em `run` → evento `failed` e a exceção sobe (convertida para ForjaError se necessário). Retorna `[{"step","status","ms","outputs":[str]}]`. `dry_run=True` não executa nem grava; devolve `status:"would_run"|"skipped"`.

### `project.py`
- `class Project`: `Project(root)`; `.config_path`, `.work`, `.out`, `.input` (Paths); `.load_config() -> dict` (usa `config.load_config`).
- `scaffold(root, name, source=None, workflow="dub", force=False) -> list[str]`: cria `input/ voices/ work/ out/`, `config.yaml` (via `config.write_default_config`), `cues.json` vazio `[]`,
  `lower_thirds.json` `[]` e `AGENTS.md` (conteúdo de `agents_md(workflow)`); recusa sobrescrever sem `force` (`ForjaError("USAGE")`). Devolve os caminhos criados (relativos).
- `agents_md(workflow) -> str`: instruções para o agente do projeto (pt-BR): ciclo `status → fazer o próximo passo → verificar`; regras (segredo só no ambiente; nunca imprimir chave; `--json`;
  não editar `work/`; tempos em segundos; QA gate antes de entregar; peça decisão humana para voz/consentimento); lista os arquivos que o agente escreve (`cues.json`, `lower_thirds.json`, `config.yaml`).
- `status(project, steps) -> dict`: `{"project": nome, "workflow": str, "steps": [{"name","state"(fresh|stale|missing),"reason"}], "next": {"command": str, "why": str}|None}`;
  `next` = primeiro passo não fresco (comando `forja run --only <passo>` ou o comando específico), `None` se tudo fresco.

### `describe.py`
- `describe(workflows: dict, version: str) -> dict`: `{"version","exit_codes","error_codes","commands":[{"name","summary","args"}],"workflows":{nome:{"summary","steps":[{"name","doc","needs"}],"files":{"agent_writes":[...],"generated":[...]}}},"providers":[...registry.available()],"schemas":{"config": <DEFAULTS>,"cues": <schema simples>}}`.

### `workflows/__init__.py`
- `WORKFLOWS: dict[str, Workflow]`; `register_workflow(name, summary, steps_factory, files)`; `get_workflow(name)` (inexistente → `CONFIG_INVALID`); `load_entry_points("forja.workflows")`.

### `workflows/dub.py` (cola; testada por integração, não por unidade)
Passos na ordem: `clip` (corta `input.video` com `input.start/duration` → `work/clip.mp4`, mede com `probe`), `orig` (extrai `work/orig.wav` 48 kHz estéreo),
`transcribe`, `check` (cues), `voices`, `schedule`, `mix`, `render`, `qa`. Cada um chama os módulos-biblioteca; ffmpeg/Remotion via `media.py`.

### `media.py` (cola de subprocessos; funções recebem `run=subprocess.run` injetável)
`cut_clip`, `extract_audio`, `trim_tempo_cmd` (trim silêncio + `atempo` de uma fala), `assemble_mix` (soma vozes+original com envelope, numpy), `measure_loudness`, `render_remotion`, `mux`, `contact_sheet`. Retornam caminhos/dicts; erro de ffmpeg → `ForjaError("PROVIDER_ERROR"|"MISSING_PREREQ")` com o final do stderr.

### `cli.py`
`forja [--json] [--project DIR] <comando>`. Comandos: `init`, `describe`, `status`, `doctor`, `run [--only a,b] [--force] [--dry-run] [--strict]`,
e atalhos por passo: `transcribe`, `frames`, `check`, `voices [--only IDs]`, `schedule`, `mix`, `render`, `qa [--strict]`, `providers`.
`main(argv=None, env=None, out=sys.stdout, err=sys.stderr) -> int` (`env=None` → `os.environ`, resolvido na chamada) (injetável para teste). Sem `--json`: texto curto em pt-BR; com `--json`: documento único.
`doctor`: confere `ffmpeg`, `ffprobe`, `node`, navegador do Remotion, Python libs, modelo STT em cache e o provedor de voz. No provider `gemini`, mostra a variável da chave apenas como "definida"/"ausente"; nos providers `google_ai_studio`/`files`/`piper`/`mock`, não exige chave. Exit 4 se faltar o essencial.

## Workflow `storyboard` (v1 parcial, formato do vídeo por cenas; origem: inventário do YCE)

`storyboard.yaml` (versão 1) descreve `canvas`, `theme`, `audio`, `providers` e `scenes[]` com `layers[]`; tipos de camada no v1: `clip` (`source: file|user`, `file`, `in_s`, `out_s`, `fit`, `audio.mode: keep|duck|mute`),
`narration` (`text`, `lang`, `voice`), `captions` (`from: narration`), `card` (`asset` PNG, `enter`/`exit` por âncora, `full_frame`), `music` (`track`, `gain_db`, `ducking`, `license` **obrigatório**), `sfx`.
Duração da cena: `{fixed_s}` ou `{from: narration, pad_before, pad_after}`. Âncoras de tempo: `scene_start`, `scene_end`, `{anchor: word, word, offset_s}` resolvidas contra `work/timing.lock.json`.
Módulos: `storyboard.py` (`validate_storyboard(sb) -> list[ISSUE]`, `resolve_timeline(sb, durations, words) -> dict`, `to_srt`), template Remotion `Storyboard` (composição genérica), `workflows/storyboard.py`.
Itens fora do v1 (registrados em `docs/ROADMAP.md`): clipes de IA por provedor (hoje manual/Flow), sfx, transições além de crossfade, publicador.

## `storyboard.py` (contrato detalhado)

Entrada = dict já lido do YAML. Issue = mesmo formato de `cues.ISSUE` (`level`, `id`, `code`, `msg`), `id` = id da cena/camada quando houver.
- `validate_storyboard(sb: dict, root: Path|None = None) -> list[ISSUE]`. Códigos:
  `SCHEMA` (error: falta `version==1`, `canvas{w,h,fps}`, `scenes` lista não vazia, cena sem `id` ou sem `layers`, camada sem `type`, `type` desconhecido), `BAD_ID` (error: id de cena inseguro para nome de arquivo),
  `DUP_SCENE` (error: id de cena repetido), `NO_DURATION` (error: cena sem `duration` ou sem `fixed_s`/`from: narration` válidos, ou `from: narration` sem camada `narration`),
  `ASSET_MISSING` (error; só quando `root` é dado: `file`/`asset`/`track` inexistente sob `root`), `ASSET_OUTSIDE` (error; caminho absoluto ou que sai da raiz do projeto), `MUSIC_NO_LICENSE` (error: camada `music` sem `license.kind`),
  `ANCHOR_UNRESOLVED` (warn: âncora `word` cuja palavra não aparece no texto da narração da cena), `FIT` (error: `fit` fora de `cover|contain`).
  Tipos de camada válidos: `clip`, `narration`, `captions`, `card`, `music`, `sfx`.
- `resolve_timeline(sb: dict, narration_s: dict[str, float], words: dict[str, list[dict]] | None = None) -> dict`:
  `narration_s[scene_id]` = duração (s) da fala da cena (sem a camada narration → ausente). Duração da cena = `fixed_s` ou `pad_before + narration_s + pad_after` (pads default 0).
  Cenas em sequência, `start` acumulado (sem transição no v1). Retorna `{"fps","total_s","scenes":[{"id","start","end","layers":[{"type","start","end", ...cópia dos campos}]}]}`.
  Camadas começam em `scene.start` (+ `enter.at_s` se houver, âncora `scene_start`), terminam em `scene.end` (ou `enter.at_s + hold_s`). Âncora `{"anchor":"word","word":W,"offset_s":o}`:
  tempo = início da primeira palavra W (`words[scene_id]` = `[{"word","start","end"}]`, comparação sem pontuação/caixa) + `offset_s` + `scene.start + pad_before`; palavra não achada → cai para `scene_start` e registra `"warnings"` na camada.
- `to_srt(timeline: dict, texts: dict[str, list[str]]) -> str`: um bloco por cena com camada `captions`, texto de `texts[scene_id]` (lista de linhas), do início ao fim da camada.

## Envelope JSON da CLI (`--json`) — vale para CLI e para o MCP

Sucesso: `{"ok": true, "data": {...}, "next_actions": [{"command": str, "why": str}], "artifacts": [{"path": str, "kind": str}], "warnings": [str], "cost": null}`
Falha: `{"ok": false, "error": {"code","msg","hint","retryable","details"}}` (mesmo `error_payload`).
`data` por comando: `describe` → documento de `describe()`; `status` → o dict de `project.status` (o `next` também vira `next_actions[0]`); `init` → `{"created": [...]}`;
`run`/passos → `{"steps": [...resultado de run_steps...]}`; `doctor` → `{"checks": [{"name","ok","detail"}]}` (nunca valor de segredo); `providers` → lista de `registry.available()`.
`warnings` agrega avisos (ex.: `TEMPO_CLAMPED`). Sem `--json`: texto curto em pt-BR no stdout; erros no stderr.

## Evolução prevista (não implementar no v1; registrar em `docs/ROADMAP.md`)
- Servidor MCP fino (`forja mcp serve`, extra `forja[mcp]`, SDK oficial, stdio, ~8 tools: describe, status, plan, run, voices, qa, artifact_get, cancel) sobre os mesmos comandos.
- Provedores `clip` por API (ex.: geração de vídeo do Gemini/“Omni”, com `estimate()` de custo antes de gastar), `music` (Lyria ou trilha local com licença), `image`, `stt` na nuvem.
- `plan --json` (dry-run com custo estimado e cache hits), migrações de `schema_version`, VMAF/golden por cena, SFX, transições, publicador.
- Pacote por agente: `skills/forja/SKILL.md` + `AGENTS.md` + `mcp.json` (já incluídos no kit; o MCP vem depois).

## `media.py` (contrato detalhado; todos os subprocessos entram por `run=subprocess.run` injetável)

Importa `forja.errors.ForjaError`, `forja.mixlib`, `forja.render`. Funções que montam comando terminam em `_cmd` e **não** executam nada (puras, testáveis).
- `run_checked(cmd, run=subprocess.run, what="ffmpeg") -> subprocess.CompletedProcess`: chama `run(cmd, capture_output=True, text=True)`;
  `FileNotFoundError` → `ForjaError("MISSING_PREREQ", ..., hint=<instale/ponha no PATH>)`; `returncode != 0` → `ForjaError("PROVIDER_ERROR", msg com `what`, details={"cmd": cmd[0], "returncode": n, "stderr_tail": últimos 500 chars do stderr})`. Devolve o resultado em caso de sucesso.
- `cut_clip_cmd(src, out, start, duration=None) -> list[str]`: `ffmpeg -y -ss <start> [-t <duration>] -i <src> -c:v libx264 -preset fast -crf 18 -c:a aac <out>` (`-ss` **antes** de `-i`, `-t` só se `duration` não for None; números como str). `cut_clip(src, out, start, duration=None, run=...) -> Path` executa e devolve `Path(out)`.
- `extract_audio_cmd(src, out, sr=48000) -> list[str]`: `ffmpeg -y -i <src> -vn -ac 2 -ar <sr> -c:a pcm_s16le <out>`. `extract_audio(src, out, sr=48000, run=...) -> Path`.
- `trim_tempo_cmd(wav, out, tempo, trim_silence=True) -> list[str]`: `ffmpeg -y -i <wav> -af <filtro> <out>`; o filtro tem `silenceremove` (início e fim, via `areverse`) quando `trim_silence` e termina com `atempo=<tempo>`; se `tempo` fora de [0.5, 2.0] → `ValueError`; se `abs(tempo-1) < 1e-6` o filtro **não** inclui `atempo`.
- `assemble_mix(orig_wav, voices, duck_intervals, cfg, out, sr=48000) -> Path`: numpy + `scipy.io.wavfile`. `voices` = `[{"wav": Path, "start": float}]`; `duck_intervals` = lista de `(start_s, end_s, db)` (formato de `mixlib.duck_envelope`); `cfg` = dict completo (usa `cfg["mix"]["orig_gain"]` e `cfg["mix"]["ramp_s"]`).
  Saída estéreo int16 em `sr`: `orig × orig_gain × duck_envelope(total_s, sr, duck_intervals, ramp_s)` + soma das vozes nas posições `start` (mono → duplica nos dois canais). Duração total = a do original. `orig_wav` ou voz com taxa ≠ `sr` → `ForjaError("CONFIG_INVALID")` citando o arquivo. Se o pico passar de 0.98, escala tudo para 0.98 (nunca clipa). Voz que ultrapassa o fim é cortada no fim. Devolve `Path(out)`.
- `measure_loudness(wav, cfg, run=...) -> dict`: roda `mixlib.loudnorm_measure_cmd(wav, cfg["mix"]["target_lufs"], cfg["mix"]["true_peak"], cfg["mix"]["lra"])` e devolve `mixlib.parse_loudnorm_json(<stderr>)`.
- `normalize_loudness(wav, out, cfg, run=...) -> dict`: mede (acima), roda `mixlib.loudnorm_apply_cmd(...)` e devolve o dict medido; saída em `out`.
- `render_remotion(entry, props, public_dir, out, run=..., cwd=None) -> Path`: grava `props` (dict) em JSON UTF-8 ao lado de `out` (`<out>.props.json`), roda `render.remotion_cmd(entry, props_path, public_dir, out)` (com `cwd=cwd` repassado ao `run` quando dado) e devolve `Path(out)`.
- `mux(video, wav, out, run=...) -> Path`: roda `render.mux_cmd(video, wav, out)`.
- `contact_sheet(video, out, duration_s, n=12, cols=4, run=...) -> Path`: um comando ffmpeg com `fps=<n/duration_s>`, `scale=320:-1` e `tile=<cols>x<ceil(n/cols)>`, `-frames:v 1`; `duration_s <= 0` → `ValueError`.

## `workflows/dub.py` — contrato dos passos (substitui o esboço anterior; vale para teste e implementação)

Um passo = `Step(name, doc, inputs, outputs, run, needs)`; `run(ctx)` devolve um dict curto (vira o campo do evento) e **grava seus arquivos**. Caminhos relativos a `ctx.root`; `ctx.work = root/"work"`, `ctx.out = root/"out"`.
`ctx.env` = ambiente (só para chaves/variáveis; nunca imprimir valor). Funções externas são chamadas **pelo módulo** (`media.cut_clip(...)`, não importadas por nome), para que testes possam trocá-las com `monkeypatch`.

| passo | needs | lê | escreve | o que faz |
|---|---|---|---|---|
| `clip` | — | `cfg["input"]["video"]` (rel. a root), `config.yaml` | `work/clip.mp4`, `work/clip.json` | `media.cut_clip(video, work/clip.mp4, input.start, input.duration)`; `probe.probe_video` → `work/clip.json` |
| `orig` | clip | `work/clip.mp4` | `work/orig.wav` | `media.extract_audio(clip, orig.wav)` (48 kHz estéreo) |
| `transcribe` | orig | `work/orig.wav`, config | `work/transcript.json` | `transcribe.run_transcribe(orig, cfg, model_dir)`; `model_dir = ctx.env.get("FORJA_MODEL_DIR")` ou `~/.cache/forja/models`; grava o JSON |
| `check` | — | `cues.json`, config | `work/check.json` | `cues.load_cues` + `cues.validate_cues` → `qa.summarize(issues)` gravado; **se houver `error`: `ForjaError("GATE_FAILED", ..., details={"issues": [...]})`** (avisos não reprovam) |
| `voices` | check | `cues.json`, config | `work/voices/manifest.json` (+ `work/voices/<id>.wav`) | para cada cue: `tts.source_for(cue, cfg, ctx.root, work/"cache"/"tts", post=_http_post, env=ctx.env)` (provider `google_ai_studio`/`files` lê `voices/<id>.wav`; `piper` roda local; `mock` não chama `post`); aplica ganho por fala `mixlib.voice_gain_cmd(wav, work/voices/<id>.wav, cfg["mix"]["voice_lufs"])` via `media.run_checked`; manifesto `{id: {"wav": "work/voices/<id>.wav", "duration": seg}}` (duração lida com o módulo `wave`) |
| `schedule` | voices | manifesto, `cues.json`, `lower_thirds.json`, `work/clip.json`, config | `work/plan.json`, `work/subs.json`, `out/legendas.srt` | durações e `schedule.speech_bounds` (amostras de cada `<id>.wav` via `scipy.io.wavfile`) → `schedule.plan(cues, durations, cfg, total=clip.json["duration"], bounds)` → `plan.json`; `subs.build_subs(plan, cues, lower_thirds, cfg)` → `subs.json`; `subs.to_srt` → `out/legendas.srt` |
| `mix` | schedule, orig | `work/plan.json`, `work/orig.wav`, voices, config | `work/mix.wav`, `work/loudness.json`, `work/voices/<id>.fit.wav` | por cue do plano: `media.trim_tempo_cmd(wav, fit, tempo)` com **`-ar 48000 -ac 1` inseridos antes do arquivo de saída** (rodado por `media.run_checked`); `duck_intervals = [(start, end, mixlib.db_to_gain(duck_narrator_db se role=="narrator" senão duck_speech_db))]`; `media.assemble_mix(orig, [{"wav": fit, "start": start}], duck_intervals, cfg, work/"mix_raw.wav")`; `media.normalize_loudness(mix_raw, work/mix.wav, cfg)`; depois **mede a saída** com `media.measure_loudness(work/mix.wav, cfg)` e grava `loudness.json` como `{"I": ..., "TP": ...}` (chaves `input_i`/`input_tp` dessa medição). O gate de QA julga o que será entregue, nunca a medição de entrada do 2º passe |
| `render` | mix | `work/mix.wav`, `work/subs.json`, `lower_thirds.json`, `work/clip.mp4`, config | `out/video.mp4` | `brief.require_approvals(..., ("script","voice"))`; `render.build_props("clip.mp4", total, subs, lower_thirds, cfg)`; `media.render_remotion(entry, props, public_dir=work, out=work/"render.mp4", cwd=<dir do template>)`; `media.mux(render.mp4, mix.wav, out/video.mp4)`; `entry` = `src/index.jsx` dentro do template; template = `ctx.env["FORJA_REMOTION_DIR"]` ou `<repo>/remotion-template` (relativo ao pacote: `Path(__file__).resolve().parents[2] / "remotion-template"`) |
| `qa` | render | `out/video.mp4`, `work/plan.json`, `work/subs.json`, `work/loudness.json`, `lower_thirds.json`, config | `out/qa.json` | `qa.check_subs` + `qa.check_overlap` + `qa.check_loudness(loudness.json, cfg)` + `qa.check_schedule(plan)` → `qa.summarize` gravado em `out/qa.json`; **se `errors > 0`: `ForjaError("GATE_FAILED", ...)`** |

`_http_post(url, headers, body) -> dict`: `urllib.request` (só `https`; erro HTTP → exceção com atributo `status`; formato que `tts.synthesize` espera: leia `tts.py`). `lower_thirds.json` ausente = `[]`.
Todos os JSON gravados com `ensure_ascii=False, indent=2`.

## `workflows/storyboard.py` — contrato dos passos (v1)

Mesma convenção do `dub` (um `Step` por linha; funções externas chamadas pelo módulo, p/ `monkeypatch`; JSON com `ensure_ascii=False, indent=2`; nunca imprimir segredo). `storyboard.yaml` (YAML, lido com `yaml.safe_load`) na raiz do projeto; caminhos de assets **relativos à raiz** (`assets/...`).
Entrada mínima válida: `{"version": 1, "canvas": {"w": 1280, "h": 720, "fps": 30}, "scenes": [{"id": "S1", "duration": {"fixed_s": 4}, "layers": [...]}]}` (ver "storyboard.py (contrato detalhado)").

| passo | needs | lê | escreve | o que faz |
|---|---|---|---|---|
| `validate` | — | `storyboard.yaml`, config | `work/validate.json` | `storyboard.validate_storyboard(sb, root)` + avisos de `brief`/aprovação → `qa.summarize(issues)` gravado; **`error` ⇒ `ForjaError("GATE_FAILED", ..., details={"issues": [...]})`** |
| `voices` | validate | `storyboard.yaml`, config | `work/voices/manifest.json` (+ `work/voices/<cena>.wav`) | para cada cena com camada `narration`: `cue = {"id": <cena>, "text": layer["text"], "voice": layer.get("voice"), "style": layer.get("style")}` (sem `voice` ⇒ o cast `default` do config); `tts.source_for(cue, cfg, ctx.root, work/"cache"/"tts", post=_http_post, env=ctx.env)` (provider `google_ai_studio`/`files` lê `voices/<cena>.wav`); ganho `mixlib.voice_gain_cmd(... cfg["mix"]["voice_lufs"])` via `media.run_checked`; manifesto `{cena: {"wav": "work/voices/<cena>.wav", "duration": seg}}` (duração do trecho com fala: `schedule.speech_bounds` ou, se `None`, a do WAV) |
| `timeline` | voices | `storyboard.yaml`, manifesto, config | `work/timeline.json`, `work/subs.json`, `out/legendas.srt` | `storyboard.resolve_timeline(sb, {cena: duration}, words=None)` (âncoras por palavra caem em `scene_start` e viram `warnings` — v1 não alinha palavras) → `timeline.json` (com `"fps"`, `"total_s"`); legendas: para cada cena com camada `captions` e narração, `texts[cena] = cues.split_lines(texto, cfg["render"]["max_chars_line"], cfg["render"]["max_lines"])` (se `None`, quebra simples por palavras em 2 linhas) → `storyboard.to_srt(timeline, texts)` → `out/legendas.srt` e eventos `{"start","end","lines","narrador":false,"raised":false}` em `work/subs.json` |
| `mix` | timeline | `work/timeline.json`, manifesto, `storyboard.yaml`, config | `work/mix.wav`, `work/loudness.json`, `work/bed.wav`, `work/voices/<cena>.fit.wav` | **base** `work/bed.wav` (48 kHz estéreo, `total_s`): se houver camada `music` (`track`, `gain_db` default 0), decodifica a trilha cortada em `total_s` com `volume=<gain_db>dB` (ffmpeg via `media.run_checked`); senão silêncio (`anullsrc`); a narração de cada cena entra em `scene.start + (duration.pad_before ou 0)` (voz ajustada com `media.trim_tempo_cmd(wav, fit, 1.0)` + `-ar 48000 -ac 1` antes do arquivo de saída); `duck_intervals = [(ini, fim, mixlib.db_to_gain(layer.get("ducking_db", cfg["mix"]["duck_narrator_db"])))]` para o intervalo de cada narração; `media.assemble_mix(bed, voices, duck_intervals, {**cfg, "mix": {**cfg["mix"], "orig_gain": 1.0}}, work/"mix_raw.wav")`; `media.normalize_loudness(...)` e **mede a saída** (`media.measure_loudness(work/mix.wav, cfg)`) → `loudness.json` `{"I","TP"}`. Áudio embutido dos clipes e `sfx` **não** entram no v1: se existirem, `warnings` no retorno do passo (`CLIP_AUDIO_IGNORED`, `SFX_IGNORED`), nunca erro |
| `render` | mix | `work/timeline.json`, `work/subs.json`, `work/mix.wav`, assets | `out/video.mp4` | `brief.require_approvals(..., ("script","voice","overlays"))`; props = `{"timeline": timeline, "subs": subs, "lowerThirds": storyboard.caption_windows(timeline), "brand": cfg["brand"], "fps": canvas.fps, "width": canvas.w, "height": canvas.h, "fontSize": cfg["render"]["font_size"], "durationS": timeline["total_s"]}`; `media.render_remotion(entry, props, public_dir=<raiz do projeto>, out=work/"render.mp4", cwd=<template>, composition="Storyboard")`; `media.mux(render.mp4, mix.wav, out/video.mp4)` (entry/template como no `dub`) |
| `qa` | render | `out/video.mp4`, `work/subs.json`, `work/loudness.json`, `work/timeline.json`, config | `out/qa.json` | `qa.check_subs` + `qa.check_loudness` + (v1) conferência de duração: `ffprobe` do `out/video.mp4` vs `timeline.total_s` (diferença > 0.5 s ⇒ `error` `DURATION_MISMATCH`) → `qa.summarize` gravado; `errors > 0` ⇒ `GATE_FAILED` |

`_http_post` e o resolvedor do template/entry: **reuse** os de `forja/workflows/dub.py` (importe-os de lá; não duplique).
`music` sem `license` já é erro do `validate`. Nenhum asset é copiado: o `public_dir` é a raiz do projeto e os `file`/`asset` das camadas são relativos a ela.

## Overlays do storyboard (v1.1)

`LAYER_TYPES` inclui `overlay`. A camada tem:

```yaml
- type: overlay
  preset: lower_third | title | callout | quote | cta | logo | stat
  text: "..."                 # obrigatório exceto logo; até 280 caracteres
  subtext: "..."              # opcional; até 120
  position: bottom-left | bottom-right | top-left | top-right | center | bottom-center | top-center
  asset: assets/logo.png      # obrigatório no preset logo
  enter: {anchor: scene_start, offset_s: 0.6}
  hold_s: 3.5
  safe_area: true
  style: {accent: "#RRGGBB", ink: "#RRGGBB", paper: "#RRGGBB", font: "...", font_size: 12..200,
          radius: 0..80, opacity: 0..1, width: 40..1200, align: left|center|right,
          uppercase: bool, shadow: bool}
```

- `validate_storyboard` emite `OVERLAY_PRESET`, `OVERLAY_TEXT`, `OVERLAY_POSITION`, `OVERLAY_ASSET`,
  `OVERLAY_HOLD` e `OVERLAY_STYLE`; assets passam por `ASSET_MISSING`/`ASSET_OUTSIDE`.
- `resolve_timeline` calcula `start`/`end` com `enter`/`hold_s`; overlay que passa do fim da cena é
  cortado com warning.
- `caption_windows(timeline)` devolve as janelas de overlays com posição `bottom-*`; o passo `timeline`
  marca `raised` nos eventos de legenda que colidem, e `Captions.jsx` sobe a legenda.
- `Overlay.jsx` (Remotion) desenha os presets com `brand` + `style`; o texto usa fallback
  `Liberation Sans, Arial, Helvetica, sans-serif`. O tema padrão está em `config.brand`.
- O storyboard demo em `examples/storyboard-demo/` exercita `lower_third` e `cta`.

## Brief e aprovação humana (v1.1)

- `brief.yaml`: `version: 1`, `objective`, `audience`, `tone`, `duration_s`, `must_include`,
  `must_avoid`, `consent`. `brief.brief_issues(root)` devolve avisos `BRIEF_MISSING`/`BRIEF_INCOMPLETE`
  e erros de schema; `check`/`validate` anexam esses avisos ao resultado.
- `approvals.json`: `{"script","voice","overlays","publish"}` booleanos + `by`/`at`.
  `load_approvals` falha fechado (`GATE_FAILED`) com JSON inválido; `write_approvals` é atômico.
- `forja approve --script --voice --overlays --publish --by NOME` grava as aprovações.
- `project.require_approvals` (default `true` no `forja init`; `false` em `project.scaffold` para testes)
  faz `render` chamar `brief.require_approvals`; sem as chaves exigidas → `GATE_FAILED`.
  `forja init --no-require-approvals` desliga o gate em demos/testes.
- `brief`/`approvals` entram em `agent_writes`; o agente só chama `approve` depois da confirmação
  explícita do humano.
