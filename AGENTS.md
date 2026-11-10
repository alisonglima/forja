# AGENTS.md — forja

Ferramenta de geração de vídeo operada por agentes (dublagem EN→pt-BR, legendas embutidas, vídeos por cenas). Contrato técnico: `DESIGN.md`. Skill: `skills/forja/SKILL.md`. Prompts prontos: `prompts/`.

- Projeto novo: `forja init DIR [--source VIDEO] [--workflow dub|storyboard]`; sem `--source`, cria um projeto `storyboard`.
- Vozes: o padrão é `voices.provider: files`; o humano gera os WAVs em `voices/<id>.wav`. Provedores por API são opcionais.
- Teste: `python3 -m pytest -q tests`. Todo módulo novo nasce com teste de contrato.
- Estilo: `from __future__ import annotations`; sem `print` em biblioteca; subprocessos e rede **injetáveis** (`run=`, `post=`); sem caminhos absolutos.
- Nunca use `os.environ` como valor padrão de parâmetro (é avaliado na importação e a assinatura passa a carregar o ambiente, com segredos): use `env=None` e resolva na chamada.
- Segredos: nunca no repo, em log ou em `--json` (só o **nome** da variável). `.env` fica fora do git.
- Extensão: provedores em `forja/registry.py` (`@register("tts", "nome")`; a fábrica devolve `callable(cue, cfg, cache_dir, post=..., env=...) -> bytes|Path`) e workflows em `forja/workflows/`; plugins externos por entry point (`forja.providers`, `forja.workflows`), carregados no início da CLI.
- Imagem Docker: alvo `linux/amd64`, usuário não-root.
