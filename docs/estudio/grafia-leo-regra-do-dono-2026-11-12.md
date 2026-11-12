# Grafia da marca: "LEO" no Brasil, "Leo" fora

**Regra do dono (12/11/2026).** No Brasil a sigla se escreve com **todas as letras maiúsculas: `LEO`** (plural `LEOs`), nunca `Leo`. Quando a arte ou o vídeo for em **outro idioma** e divulgado **fora do Brasil**, pode-se usar `Leo`.

| Contexto | Escrever | Não escrever |
|---|---|---|
| Português, divulgado no Brasil (post, legenda, vídeo, roteiro, alt) | `LEO`, `LEOs` | `Leo`, `Leos` |
| Outro idioma (ex.: inglês), divulgado fora do Brasil | `Leo`, `Leos` | — |

## De onde vem, e o que diverge
- É **regra do dono**, não do guia. O guia PT oficial (`guia-pt-texto.md`) escreve "Leos" ("Leões e Leos prestam…"). Onde o guia e a regra divergem, **a regra do dono manda** para o Brasil.
- O guia oficial em inglês escreve `Leo` (35 vezes em `guia-leo-texto.md`); isso vale para o material em inglês.
- Não vem de nenhum arquivo do acervo da Lions: está aqui e em `brands/leo-lions/grafia.json` (dado, versionado).

## Como o Forja aplica
- **Dado:** `brands/leo-lions/grafia.json` (por idioma). Arquivo novo; `voice.json` não foi alterado porque o hash dele é conferido pelo `brand_manifest`.
- **Verificação:** no **texto-fonte** (`copy.json`, legenda, roteiro), nunca no render, porque `text-transform: uppercase` esconderia um `Leo` errado. Padrão em pt-BR: `\bLeos?\b` ⇒ reprova. Hoje roda em `.work/peca-leo/gates.py`; virar gate do `forja/` é trabalho de lane (contrato + implementação).
- **Peça já entregue corrigida:** o texto do primeiro post ("há um Leo", "Participe do Leo") violava a regra e foi trocado por `LEO`.

## Pendências suas (o checador não decide por você)
1. Palavras derivadas em português (`Leoísmo`/`LEOísmo`, `LEOs`): o post de outro clube que você mandou mistura "LEOs" e "Leoísmo". Por enquanto o checador **não** as bloqueia.
2. O plural `LEOs` é provisório (decorre da regra; você não o definiu).
3. Grafia de **Leo-Lion** em português (`Leo-Leão`?): não definida; não usar nesta fase.
