# Contribuindo com o Forja

Obrigado pelo interesse! Este projeto é uma CLI em Python + kit Docker para gerar vídeos com
agentes de IA. Contribuições de código, documentação, prompts e relatos de uso são bem-vindas.

## Antes de abrir uma issue

- Leia o [guia](https://alisonglima.github.io/forja/) e o [README](README.md).
- Rode `forja --json doctor` (ou `./kit.sh doctor`) e inclua a saída **sem chaves nem senhas**.
- Procure issues existentes; evite duplicatas.

## Ambiente de desenvolvimento

Requisitos: Python 3.9+, ffmpeg/ffprobe no PATH. Node 20+ só é necessário para testar o render
Remotion de verdade; a suíte usa simulações para a maior parte do render.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
python -m pytest -q tests
```

Para a doc:

```bash
python -I scripts/build-doc.py --out docs/index.html
```

O `docs/index.html` é gerado; edite `scripts/build-doc.py` e os `prompts/*.md`, não o HTML à mão.

## Contrato de código

- **Teste primeiro**: todo módulo/comportamento novo nasce com um teste em `tests/` que importa o
  módulo **dentro** do teste. Subprocessos e rede são injetáveis (`run=`, `post=`) para o teste
  rodar sem mídia real.
- `from __future__ import annotations` no topo dos módulos; sem `print` em biblioteca; sem caminhos
  absolutos; tempos em segundos (float).
- Nunca use `os.environ` como valor padrão de parâmetro: use `env=None` e resolva na chamada.
- Segredos nunca no repositório, em log ou no `--json`; só o **nome** da variável.
- O que toca ffmpeg/Remotion/Docker precisa de execução real em algum teste de integração; teste
  que só compara texto de comando não pega comando inválido.

## Pull requests

1. Descreva o problema e a solução; linke a issue quando houver.
2. Inclua testes e rode `python -m pytest -q tests`.
3. Atualize `README.md`, `DESIGN.md`, `docs/ROADMAP.md` e `prompts/` se o contrato mudar.
4. Rode `python scripts/check-prompts.py --expect 15` se mexer em prompts.
5. Mantenha o commit focado; use mensagens no estilo Conventional Commits (`feat:`, `fix:`,
   `docs:`, `test:`, `chore:`).

Ao enviar, você concorda que a contribuição é licenciada sob a MIT License deste repositório.

## Código de conduta

Ao participar, você concorda com o [Código de Conduta](CODE_OF_CONDUCT.md).
