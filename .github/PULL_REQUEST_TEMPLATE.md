## O que muda

<!-- Descreva o problema e a solução em 2-3 frases. -->

## Por quê

<!-- Contexto, issue relacionada, uso real. -->

## Como testar

<!-- Comandos e resultados. Ex.: python -m pytest -q tests -->

## Checklist

- [ ] Teste de contrato escrito/atualizado e passando
- [ ] `python -m pytest -q tests` verde
- [ ] `python scripts/check-prompts.py --expect 14` (se mexeu em prompts)
- [ ] `README.md`/`DESIGN.md`/`docs/ROADMAP.md` atualizados quando o contrato mudou
- [ ] `docs/index.html` regenerado (se mexeu em `scripts/build-doc.py` ou `prompts/`)
- [ ] Sem chave, senha, cookie ou dado pessoal no diff
