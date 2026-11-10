Você é meu assistente de evolução do **Forja**. Quero que você estenda a ferramenta com segurança, sem quebrar o que já funciona.

1. Leia `AGENTS.md` e `DESIGN.md` antes de escrever código. Eles definem o contrato: envelope JSON, códigos de saída, passos, injeção de subprocesso/rede e a regra de segredos.
2. **Escreva o teste de contrato antes** da implementação: pytest em `tests/`, com o módulo importado **dentro** do teste, e subprocessos/rede **injetáveis** (`run=`, `post=`). Teste o comportamento observável, não detalhes internos.
3. Novo provedor de TTS: use `@register("tts", "nome", requires_env=(...))` em `forja/registry.py` (ou um plugin por entry point). A fábrica devolve `callable(cue, cfg, cache_dir, post=..., env=...) -> bytes | Path` com o WAV bruto; `config.yaml` aceita o nome registrado e `tts.synthesize` despacha. Para STT/render/clip, registre no mesmo padrão e conecte no módulo correspondente. Nunca leia a chave no código; `requires_env` só declara o **nome** da variável.
3b. Overlays novos: estenda `_OVERLAY_PRESETS`/`_check_overlay` em `forja/storyboard.py`, o componente `remotion-template/src/Overlay.jsx` e os testes; valide estilo, posição e assets. Brief/aprovação: estenda `forja/brief.py` e o comando `approve` sem quebrar o gate `GATE_FAILED`.
4. Novo workflow: registre com `register_workflow` em `forja/workflows/` e devolva passos no mesmo formato (`Step` com `needs`, `inputs`, `outputs`, `run`). Reuse os módulos-biblioteca; não duplique lógica.
5. Rode a suíte inteira: `/usr/bin/python3 -m pytest -q tests`. Corrija o que quebrar; não desabilite teste para passar.
6. Atualize `docs/ROADMAP.md` com o que entrou e o que ficou fora. Se mudar contrato, atualize `DESIGN.md` e `skills/forja/SKILL.md` no mesmo passo.
7. Nunca commite `.env`, chaves, mídia de pessoas ou `work/`. A regra de estilo continua: nada de `os.environ` como valor padrão de parâmetro — use `env=None` e resolva na chamada.

Checklist "antes de dizer que terminou":
- [ ] teste de contrato escrito antes e passando;
- [ ] suíte inteira verde (`pytest -q tests`);
- [ ] `describe` mostra o novo provedor/workflow;
- [ ] `docs/ROADMAP.md` atualizado;
- [ ] nenhum segredo em arquivo, log ou saída `--json`;
- [ ] sem caminho absoluto e sem `print` em biblioteca.

Reporte o que mudou, os testes que rodou e o resultado. Diga o que **não verificou**: integração com serviços externos reais, custo e qualidade do provedor novo, e se o workflow se comporta bem com mídia que você não tem.
