# AGENTS.md — forja

Ferramenta de geração de vídeo operada por agentes (dublagem EN→pt-BR, legendas embutidas, vídeos por cenas). Contrato técnico: `DESIGN.md`. Skill: `skills/forja/SKILL.md`. Prompts prontos: `prompts/`.

- Projeto novo: `forja init DIR [--source VIDEO] [--workflow dub|storyboard]`; sem `--source`, cria um projeto `storyboard`. O init cria `brief.yaml`/`approvals.json` e liga `require_approvals`; use `--no-require-approvals` só em demo/teste.
- Vozes: padrão `google_ai_studio` (WAVs gerados na interface web do AI Studio em `voices/<id>.wav`), `files` (alias para qualquer WAV), `piper` (TTS local, sem conta/API) ou `gemini` opcional. O kit inclui Piper para narração offline.
- Teste: `python3 -m pytest -q tests`. Todo módulo novo nasce com teste de contrato.
- Estilo: `from __future__ import annotations`; sem `print` em biblioteca; subprocessos e rede **injetáveis** (`run=`, `post=`); sem caminhos absolutos.
- Nunca use `os.environ` como valor padrão de parâmetro (é avaliado na importação e a assinatura passa a carregar o ambiente, com segredos): use `env=None` e resolva na chamada.
- Segredos: nunca no repo, em log ou em `--json` (só o **nome** da variável). `.env` fica fora do git.
- Overlays: camada `overlay` (`lower_third`, `title`, `callout`, `quote`, `cta`, `logo`, `stat`) com `brand` e `style`; ver `DESIGN.md`.
- Cenas: o caminho padrão é o **Google Flow** no navegador logado com a conta/creditos (prompt 14); o Forja não chama o Flow por API.
- Storyboard: `clip.audio` (keep/mute/duck + gain), `sfx` (asset/file + license.kind), música e voz entram no bed; `enter/exit.anchor: word` transcreve a narração com Whisper e cacheia `work/words/`.
- MCP: `forja mcp serve` (stdio) expõe 8 tools; a aprovação humana continua obrigatória.
- Aprovação humana: preencha `brief.yaml`; depois de revisar, rode `forja approve --script --voice --overlays --by <nome>`.
- Extensão: provedores em `forja/registry.py` (`@register("tts", "nome")`; a fábrica devolve `callable(cue, cfg, cache_dir, post=..., env=...) -> bytes|Path`) e workflows em `forja/workflows/`; plugins externos por entry point (`forja.providers`, `forja.workflows`), carregados no início da CLI.
- Imagem Docker: alvo `linux/amd64`, usuário não-root.
