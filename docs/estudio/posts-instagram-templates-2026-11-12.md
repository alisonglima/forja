# Posts de Instagram: capa de campanha, data comemorativa e editorial

**Decisão do dono (12/11/2026):** partir do que é **oficial** (kits, logos, guias) e **no máximo aprimorar**; não reinventar. Os kits são para o **LEO Clube de Taquaritinga** e o **Lions Clube de Taquaritinga** (também usáveis por outros clubes; no ano seguinte, nas esferas de distrito). Formato: feed 4:5, 1080×1350 (`ig-feed-4x5`).

## Família 1: padrão oficial (medido nos kits do acervo)
| Peça | Lions | LEO |
|---|---|---|
| Capa de campanha | `capa-oficial-lions` | `capa-oficial-leo` |
| Data comemorativa | `data-oficial-lions` | `data-oficial-leo` |

**Receita Lions** (kit `GlobalBrand1`, medido pixel a pixel): foto sob **degradê azul → roxo** (`azul` `#00338D` embaixo à esquerda, `roxo` `#7A2582` no canto superior direito, opacidade 0,85), duas faixas diagonais claras e **cunha dourada translúcida** no canto inferior direito, assinatura horizontal branca **"Lions International"** no topo, título branco pesado, fio amarelo, subtítulo branco.
**Receita LEO** (kit `LeoAwareMonth`): foto sob **azul-claro chapado** (`#407CCA`, opacidade 0,9 sobre véu cinza 0,5), chevrons claros e **cunha amarela** no canto inferior esquerdo, emblema LEO oficial, título branco pesado, fio amarelo.

Dado e texto: tudo em `brands/leo-lions/` (paleta em `variants.json`, grafia em `grafia.json`); logo e foto vêm do acervo privado e **não** são versionados aqui.

## Família 2: editorial (menos engessada)
Inspirada no post do Dia Nacional do LEO do clube: foto inteira, tipografia gigante, data espaçada, logo discreto. `editorial-capa` (título uppercase 150 px em Roboto 900 branco, fio amarelo) e `editorial-numero` (caixa de chamada branca, numeral gigante amarelo sobre véu cinza, legenda). É desenho **nosso**, ancorado na paleta oficial; o laranja do post de referência **não** é cor do LEO (a paleta LEO é cinza, amarelo, azul-claro e verde).

## Versão Story (1080×1920, `ig-story`)
Os seis templates são **independentes do formato**: altura e margens vêm de variáveis CSS (`--h`, `--mx`, `--mt`, `--mb`) que o `compose.py` calcula a partir da `safe_zone` do `formats.json` (feed 5 %, com piso de 72 px; story 15 % em cima e embaixo e 10 % nas laterais, ou seja 288 px e 108 px). Uma peça Story é a mesma peça com `preset: ig-story` e `altura: 1920` em `pecas.json`; o feed ficou **idêntico** (contraste e gates medidos iguais antes e depois). Diferenças deliberadas no Story: sem o "Arraste" (Story não desliza), título editorial do LEO em 128 px (a palavra mais longa do exemplo estourava a zona segura a 150 px). As peças `*-story` passam nos mesmos gates (lint, zona segura, contraste, mídia, grafia).

## Contraste medido (gate `contrast_photo`, pior região sob o texto; regra: 3:1 para texto ≥ 24 px)
| Peça | mínimo |
|---|---|
| Lions capa / data | 5,3 / 6,3 |
| LEO capa / data | 3,4 / 3,4 |
| Lions editorial / LEO editorial | 4,6 / 3,5 |
| LEO número | 3,3 |

## Divergências e escolhas (registradas, não escondidas)
1. **Gradiente:** `brand_lint` proibia qualquer gradiente; o kit oficial Lions usa o degradê azul→roxo. Agora é **opt-in por peça**: `rules={"allow_brand_gradient": True}`, só com stops da paleta da variante (lane `L-LINT-GRAD-01`, contrato `tests/test_brand_lint_gradient.py`). `rgba`, nome de cor e `transparent` seguem proibidos.
2. **Check `slop-glow` do Open Design (kit 0.4.0):** o `check --fail-on warning` classifica qualquer degradê roxo-azul sobre o card como "aparência padrão de IA" e reprovou as duas peças Lions no run 7. O kit oferece exceção **por elemento**, `data-od-allow="slop-glow"` (lido em `out/index.js`, `allowed()` sobe pelos ancestrais); aplicada **só** ao `.overlay` dos templates Lions, com comentário. Os demais checks seguem ativos.
3. **Assinatura "Lions International":** o `brand_lint` só reconhece `Assinaturas_de_Lions_Clubs_International/`; a assinatura horizontal está em `Assinaturas_de_Lions_International/`, liberada por peça via parâmetro `logos` (pendência: incluir no `_EMBLEMS`).
4. **Lions com 3 acentos** (`azul`, `amarelo`, `roxo`): `max_accents: 3` só nas peças Lions de degradê.
5. **LEO sobre azul-claro:** o branco sobre o azul oficial dá ~3,4:1; só passa em texto grande. Por isso o véu cinza e a ausência de texto pequeno. A foto fica discreta (é o visual do kit).
6. **Tipografia:** Roboto 400/700/900 local é a substituta digital declarada de Helvetica Neue; Roboto Condensed **não** foi usada.
7. **Cunha dourada × "não inventar seta nem fita":** a cunha vem do kit oficial (não é seta nem fita).
8. Exemplos de foto, copy, datas (IDF 14/11, ONU 5/12) e o número `000.000` são **placeholders**; fotos da biblioteca oficial, com direitos/menores **não revisados**.
9. **Grafia:** pt-BR usa `LEO`/`LEOs` (ver `grafia-leo-regra-do-dono-2026-11-12.md`), conferida no texto-fonte.
10. **Medição de texto:** o gate usa o retângulo real do texto (DOM Range), não a caixa do elemento.

## Pendente com o dono
- Identidade própria do clube (a logo "LEO Clube de Taquaritinga" dos prints **não** está no kit oficial; não foi inventada): enviar o arquivo.
- Derivadas (`Leoísmo`) e plural `LEOs`; Leo-Lion em português.
