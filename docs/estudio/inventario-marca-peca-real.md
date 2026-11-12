# Inventário de MARCA para a peça real — Leo/Lions (R-PECA-01A)

Levantamento **somente por leitura** do acervo oficial em `.work/fontes/lions/` (base `dc2c4bd`). Todos os caminhos de acervo abaixo são relativos a essa pasta; os de repositório começam por `brands/`. O acervo é © Lions Clubs International e não foi copiado para o repositório. Citações literais ficam abaixo de ~25 palavras; o resto é paráfrase. Onde não achei, está escrito "não encontrei".

## 1. Tipografia oficial

O guia não define uma família para título e outra para texto: define uma **primária** com hierarquia de pesos (título maior/negrito, subtítulo médio, corpo leve) — `guia-de-marca/guia-pt-texto.md:859-864`; `guia-de-marca/leo/guia-leo-texto.md:194-198`.

| Marca | Título / texto | Secundária | Sistema / digital |
|---|---|---|---|
| Lions | Helvetica Neue, pesos 35 Thin a 97 Black Condensed (`guia-de-marca/guia-pt-texto.md:803-857`) | Adobe Caslon Pro, só texto longo abaixo de títulos; nunca em título/subtítulo (`:872-875`) | Helvetica/Arial/Times para Word e comunicação interna (`:901-904`); Roboto para digital/web (`:924-927`) |
| Leo | Helvetica Neue (`guia-de-marca/leo/guia-leo-texto.md:145-147`) | **não encontrei** família secundária; o texto de p.8 fala em "secondary typefaces", mas não a nomeia (`:184-185`) | Helvetica/Arial/Times como padrão (`:182-185`); sem menção a Roboto no guia Leo |
| Leo-Lion | Helvetica Neue (`guia-de-marca/leo/guia-leo-lion-texto.md:147-149`) | **não encontrei** família secundária; o texto de p.8 fala em "secondary typefaces", mas não a nomeia (`:186-187`) | Helvetica/Arial/Times como padrão (`:184-187`); sem menção a Roboto |

O `brands/leo-lions/manifest.json:29-37` registra `official: Helvetica Neue`, fallback Helvetica/Arial/Times e `digital_substitute: Roboto`, mas aponta como fonte só o `guia-de-marca/leo/tokens-submarcas.json`, não os guias.

**Arquivos de fonte no acervo:** `find .work/fontes/lions` com `*.ttf`, `*.otf`, `*.woff*` retorna **9 arquivos, nenhum da marca**: 8 cópias de `MinionPro-Regular.otf` e 1 `TypeNo3.otf`, fontes de documentos do Box B (`box/B-jornal-promocional-outdoor/.../01_Fontes do documento/`). **Não há** Helvetica Neue, Adobe Caslon Pro nem Roboto; **não há** `.ttf`, `.woff` ou `.woff2`. No repositório também não há fonte (`find` = 0).

**Licença e embutir em PNG/PDF:** o único registro é `guia-de-marca/tokens-oficiais.json:24`: Helvetica Neue e Caslon são comerciais, "não redistribuir". **Não encontrei EULA** no acervo. Não há base para afirmar que o guia permita embutir o arquivo `.ttf/.otf` em PDF — embutir o arquivo é redistribuí-lo. Em PNG o texto vira pixel e o arquivo da fonte não acompanha, mas isso não resolve a licença de uso da fonte; confirmar com o dono.

**Substituta aberta admitida:** sim, **Roboto**, mas só para aplicações online quando primária/secundária não existem (`guia-de-marca/guia-pt-texto.md:924-927`; `guia-de-marca/tokens-oficiais.json:23-24`). O próprio token a chama de "aberta" (`guia-de-marca/tokens-oficiais.json:24`), porém **não há arquivo Roboto no acervo nem no repositório**; o guia não admite outra família aberta como substituta.

**Fallback mais fiel disponível hoje:** no macOS, `/System/Library/Fonts/HelveticaNeue.ttc` (família exata "Helvetica Neue", 4,47 MB; conferido com `mdls`). Serve para rasterizar/provar localmente, **não pode ser levado para o LXC**. Para o LXC/HTML não há fonte da marca: decidir entre licenciar Helvetica Neue, obter Roboto offline ou aceitar Helvetica/Arial — que também não estão instaladas no Linux.

Divergência menor: `guia-de-marca/leo/tokens-submarcas.json:36` diz "35 a 96"; o guia lista também 97 Black Condensed (`guia-de-marca/guia-pt-texto.md:839-841`).

## 2. Logo

Todos os PNGs abaixo passam em `sips -g hasAlpha` com `hasAlpha: yes`; dimensões e conteúdo útil foram conferidos com `sips` e leitura de pixels (sem editar). Caminhos relativos a `.work/fontes/lions/logos/`.

### Leo (emblema do programa)

| Arquivo | px | Variante | Fundo para o qual serve |
|---|---:|---|---|
| `Emblemas_de_Leos/109141433__Logo_rgb_Leo_2C.png` | 1501×1501 | Leo 2C, **sem designação** (grupo geral); só o emblema, cinza + branco | claro; é o único geral |
| `Emblemas_de_Leos/109141431__Logo_rgb_Leo_2C_Alpha_GrayText.png` | 1501×1501 | Alpha, texto cinza | claro; só conteúdo de Alpha |
| `Emblemas_de_Leos/109141430__Logo_rgb_Leo_2C_Alpha_WhiteText.png` | 1501×1501 | Alpha, texto branco | escuro; só conteúdo de Alpha |
| `Emblemas_de_Leos/109141432__Logo_rgb_Leo_2C_Omega_GrayText.png` | 1501×1501 | Ômega, texto cinza | claro; só conteúdo de Ômega |
| `Emblemas_de_Leos/109141435__Logo_rgb_Leo_2C_Omega_WhiteText.png` | 1501×1501 | Ômega, texto branco | escuro; só conteúdo de Ômega |

**Melhor candidato da variante Leo para fundo azul escuro:** `109141430` (Alpha) ou `109141435` (Ômega), ambos com texto branco — **mas só se a peça falar a Alpha ou a Ômega**. Para o grupo geral não existe PNG do emblema Leo com texto branco: o `109141433` é cinza + branco e o cinza `#55565A` sobre `#00338D` dá **1,54:1** (sobre `#0D2240`, 2,17:1), insuficiente. Sem versão branca geral, a peça de fundo azul escuro para o público geral **não tem logo compliant** (ver §7).

**Melhor candidato para fundo claro:** `109141433` (geral, só emblema). Se o conteúdo for exclusivo de Alpha/Ômega, `109141431`/`109141432` (texto cinza). O guia determina que, para os dois grupos, só o emblema Leo, sem designação, pode ser usado (`guia-de-marca/leo/guia-leo-texto.md:85-90`) — por isso o geral não leva a palavra "Leo".

### Leo-Lion

| Arquivo | px | Variante | Fundo |
|---|---:|---|---|
| `Logotipos_de_Leo_a_Leão/109141436__Logo_rgb_Leo-Lion_3C_BlueText.png` | 1501×1501 | assinatura primária 3C, plaqueta azul, texto azul | claro/branco ou foto simples; **não** sobre azul |
| `Logotipos_de_Leo_a_Leão/109141439__Logo_rgb_Leo-Lion_3C_WhiteText.png` | 1501×1501 | primária 3C, plaqueta branca, texto branco | escuro/foto simples; **não** sobre azul |
| `Logotipos_de_Leo_a_Leão/109141434__Logo_rgb_Leo-Lion_1C_Blue.png` | 1501×1501 | secundária 1C azul | claro, com contraste |
| `Logotipos_de_Leo_a_Leão/109141428__Logo_rgb_Leo-Lion_1C_White.png` | 1501×1501 | secundária 1C branca | qualquer fundo com contraste, **inclusive azul** |

Para **fundo azul escuro** da variante Leo-Lion: `109141428` (1C branca), pois a primária 3C não vai sobre azul (`guia-de-marca/leo/guia-leo-lion-texto.md:79-82`). Para **fundo claro**: `109141436` (3C texto azul).

### Lions

| Arquivo | px | Variante | Fundo |
|---|---:|---|---|
| `Emblemas_do_Lions/91189054__LCI_emblem_2color_web.png` | 1296×1296 | emblema 2 cores (azul + amarelo) | claro; 3C/2C pedem fundo claro |
| `Emblemas_do_Lions/91189052__LCI_emblem_black_white_web.png` | 1295×1295 | emblema preto/branco | claro |
| `Emblemas_do_Lions/91189053__LCI_emblem_blue.png` | 1670×1580 | emblema 1C azul | claro |
| `Emblemas_do_Lions/90878825__LCI_emblem_black.png` | 1670×1580 | emblema 1C preto | claro |
| `Emblemas_do_Lions/90878829__LCI_emblem_white.png` | 1670×1580 | emblema 1C branco | escuro |
| `Assinaturas_de_Lions_International/147645614__Logo_rgb_LI_Signature_Vert1_1C_Black.png` | 360×360 | LI vertical 1C preto | claro/qualquer fundo com contraste |
| `Assinaturas_de_Lions_International/147645615__Logo_rgb_LI_Signature_Vert1_1C_Blue.png` | 360×360 | LI vertical 1C azul | claro/qualquer fundo com contraste |
| `Assinaturas_de_Lions_International/147645616__Logo_rgb_LI_Signature_Vert1_1C_White.png` | 360×360 | LI vertical 1C branco | escuro |
| `Assinaturas_de_Lions_International/147645617__Logo_rgb_LI_Signature_Vert1_2C_BlueText.png` | 360×360 | LI vertical 2C texto azul | claro |
| `Assinaturas_de_Lions_International/147645618__Logo_rgb_LI_Signature_Vert1_3C.png` | 360×360 | LI vertical 3C | claro |
| `Assinaturas_de_Lions_International/153581917__Logo_rgb_LI_Signature_Horz1_1C_Black.png` | 360×360 | LI horizontal 1C preto | claro/qualquer fundo com contraste |
| `Assinaturas_de_Lions_International/153581916__Logo_rgb_LI_Signature_Horz1_1C_Blue.png` | 360×360 | LI horizontal 1C azul | claro/qualquer fundo com contraste |
| `Assinaturas_de_Lions_International/153581919__Logo_rgb_LI_Signature_Horz1_1C_White.png` | 360×360 | LI horizontal 1C branco | escuro |
| `Assinaturas_de_Lions_International/153581918__Logo_rgb_LI_Signature_Horz1_2C_BlueText.png` | 360×360 | LI horizontal 2C texto azul | claro |
| `Assinaturas_de_Lions_International/153581915__Logo_rgb_LI_Signature_Horz1_3C.png` | 360×360 | LI horizontal 3C | claro |
| `Assinaturas_de_Lions_Clubs_International/90875979__LCI_primary_sig_3color.png` | 1780×300 | LCI horizontal 3C | claro |
| `Assinaturas_de_Lions_Clubs_International/90875984__LCI_primary_sig_2color.png` | 1780×300 | LCI horizontal 2C | claro |
| `Assinaturas_de_Lions_Clubs_International/90875988__LCI_primary_sig_black.png` | 1780×300 | LCI horizontal 1C preto | claro/qualquer fundo com contraste |
| `Assinaturas_de_Lions_Clubs_International/90875992__LCI_primary_sig_blue.png` | 1780×300 | LCI horizontal 1C azul | claro/qualquer fundo com contraste |
| `Assinaturas_de_Lions_Clubs_International/90875994__LCI_primary_sig_white.png` | 1780×300 | LCI horizontal 1C branco | escuro |
| `Assinaturas_de_Lions_Clubs_International/90875997__LCI_secondary_sig_stacked_horiz_gray.png` | 1389×467 | secundária vertical LCI, 3C | claro |
| `Assinaturas_de_Lions_Clubs_International/90876000__LCI_secondary_sig_stacked_center_gray.png` | 736×598 | secundária vertical LCI, 3C | claro |

Para **fundo azul escuro** da variante Lions: `90878829` (emblema 1C branco, 1670×1580) ou `90875994` (assinatura LCI 1C branca, 1780×300). Para **fundo claro**: `90875979` (LCI 3C, 1780×300) ou `147645618` (LI 3C, 360×360). Há um trade-off: a LCI 3C tem resolução, mas cores legadas; a LI 3C tem as cores corretas, mas só ~268×166 px de conteúdo útil — baixa para 1080 px. Antes do arquivo, decidir a **marca**: o guia separa Lions International (mestre), Lions Clubs International (governança/advocacia) e LCIF (arrecadação) (`guia-de-marca/guia-pt-texto.md:47-61`), e o `brands/leo-lions/variants.json:18` trata as pastas de LI e LCI como equivalentes para a variante `lions`.

**Deriva de cor nos PNGs Lions (achado material):** o PNG 2C `91189054` usa `#00529B` e `#FFCF06`; as assinaturas LCI usam `#00529B`, `#FFCF06` e `#54565B`, não os oficiais `#00338D`, `#EBB700` e `#55565A` (`guia-de-marca/tokens-oficiais.json:5-13`). O EPS `Emblemas_do_Lions/76039635__lionlogo_2c.eps` tem no cabeçalho `LCI emblem_2C_287+7406.eps`, ou seja, a arte de impressão é 287+7406; o desvio está nos PNGs web. Para peça fiel, decidir entre usar o PNG legado, renderizar o EPS (exige Illustrator/ferramenta) ou aceitar a diferença.

## 3. Regras de uso do logo (guia)

- **Área de respiro (clearspace):** o mínimo ao redor da assinatura é a **altura do "L" no centro do emblema** (`guia-de-marca/guia-pt-texto.md:428-429`). O espaço deve ficar livre de outros textos e gráficos (`:422-423`), inclusive em e-mail e aplicativos digitais (`:424-427`).
- **Tamanho mínimo:** só há regra **impressa**: preferido 0,5625 pol (1,42875 cm) para primária/secundária e 0,75 pol (1,905 cm) para terciária; mínimo 0,375 pol (0,9525 cm) de altura, com aprovação adicional para exceções (`guia-de-marca/guia-pt-texto.md:434-440`). **Não encontrei tamanho mínimo digital em pixels** no guia.
- **Proibido:** distorcer, trocar a fonte, recortar, inclinar, colocar sobre desenho, reconfigurar elementos, alterar cores (só as combinações do item 2.3) e alterar a nitidez das cores (`guia-de-marca/guia-pt-texto.md:656-663`). A lista "não é completa" (`guia-de-marca/guia-pt-texto.md:648-650`) e vale para as três marcas: Lions International, LCI e LCIF (`:665-666`).
- **Posição recomendada:** **não encontrei** posição fixa (canto, alinhamento etc.). O guia só exige respeitar o clearspace ao redor (`guia-de-marca/guia-pt-texto.md:424-427`).
- **Leo e Leo-Lion:** os guias próprios **não repetem** clearspace nem tamanho mínimo. O Leo só diz que o emblema não pode ser reconstruído/alterado (`guia-de-marca/leo/guia-leo-texto.md:76-78`); o Leo-Lion repete a proibição de recriar/redesenhar e veda a primária sobre azul (`guia-de-marca/leo/guia-leo-lion-texto.md:76-82`). Aplicar as regras de Lions ao Leo é decisão, não regra publicada.
- **Uso autorizado:** associados têm autorização automática para materiais de clube/distrito e mídia digital; fora disso, permissão escrita da sede (`guia-de-marca/guia-pt-texto.md:339-352`). É proibido usar o emblema em item vendido para arrecadar fundos (`paginas-vivas/logos-emblems.json:5`).

## 4. Paleta e papéis de cor

### Cores oficiais e para que servem

| Cor | Lions | Leo | Leo-Lion | Papel |
|---|---|---|---|---|
| Azul 287 `#00338D` | primária | **não** | primária | grandes áreas, tratamento tipográfico e destaque (Lions); Leo-Lion usa com branco e foto |
| Amarelo 7406 `#EBB700` | primária | primária | primária | idem |
| Roxo 2612 `#7A2582` | primária | não | não | idem |
| Azul claro 660 `#407CCA` | secundária | primária | primária | extensão/destaque com moderação (Lions); cor de peso no Leo |
| Azul marinho 289 `#0D2240` | secundária | não | não | destaque/contraste |
| Cinza Cool Gray 11 `#55565A` | secundária | primária | primária | neutro de texto/emblema |
| Cinza Cool Gray 5 `#B3B2B1` | secundária | não | não | neutro claro |
| Verde 3405 `#00AB68` | secundária | primária | não | destaque; no Leo, títulos verdes/azuis |
| Laranja 171 `#FF5B35` | secundária | não | não | destaque |

Lions: primárias em grandes áreas, tipografia e destaque; secundárias com moderação (`guia-de-marca/guia-pt-texto.md:677-693`). Leo: a paleta primária é azul claro, cinza, verde e amarelo, mais brilhante que a Lions, usada extensivamente em áreas, tipografia e acentos (`guia-de-marca/leo/guia-leo-texto.md:100-108`). Leo-Lion: azul, azul claro, cinza e amarelo, com muito branco e fotografia (`guia-de-marca/leo/guia-leo-lion-texto.md:100-110`).

### Pares aprovados / proibidos

O guia **não tabela pares hexadecimais**: dá direção e exemplos. Aprovado: cores claras (amarelo, branco, cinza frio) sobre tons escuros e ricos, checando contraste/legibilidade (`guia-de-marca/guia-pt-texto.md:729-734`; `guia-de-marca/leo/guia-leo-texto.md:110-115`); assinaturas 3C/2C/1C sobre fundo claro (`:398-400`; `:490-492`); assinaturas 1C sólidas em qualquer fundo com contraste (`:401-402`; `:493-494`); foto se a área for simples e contrastada (`:403-405`); no Leo-Lion, a primária não vai sobre azul e a 1C sólida vai em qualquer fundo com contraste (`guia-de-marca/leo/guia-leo-lion-texto.md:79-82`). Proibido: alterar cores fora das combinações do item 2.3 (`guia-de-marca/guia-pt-texto.md:662`), usar 287 como primária/dominante no Leo (`guia-de-marca/leo/guia-leo-texto.md:100-105`; `guia-de-marca/leo/tokens-submarcas.json:4`; `brands/leo-lions/variants.json:50`) e pôr a primária Leo-Lion sobre azul (`guia-de-marca/leo/guia-leo-lion-texto.md:79-80`).

O `brands/leo-lions/variants.json:24` exige "contraste ≥4.5:1", número que **não aparece no guia** (ele só diz "contraste suficiente"). Medindo os pares mais prováveis: passam branco/`#00338D` 11,3:1, amarelo/`#00338D` 6,08:1, branco/`#0D2240` 15,91:1, cinza/`#FFFFFF` 7,33:1, azul/`#FFFFFF` 11,3:1; falham verde/`#FFFFFF` 2,99:1, azul claro/`#FFFFFF` 4,24:1, cinza/amarelo 3,95:1, cinza/`#0D2240` 2,17:1 e cinza/`#00338D` 1,54:1. Ou seja, a regra de 4,5:1 do `brands/leo-lions/variants.json` não é satisfeita por toda a paleta.

### Divergências entre guia, tokens e `brands/leo-lions/variants.json`

1. **`brands/leo-lions/manifest.json:15-28`** tem paleta só de neutros (`#FFFFFF`, `#F4F4F2`, `#0D2240`, `#55565A`, `#B3B2B1`) e `default_variant: "lions"` (`:7`). `#F4F4F2` não está no guia e faltam `#00338D`, `#EBB700` e `#7A2582`; um renderizador que use essa paleta produz peça Lions em cinza.
2. **`brands/leo-lions/variants.json:6-16`** lista as 9 cores Lions sem separar primárias de secundárias; verde e laranja são secundárias de uso moderado (`guia-de-marca/guia-pt-texto.md:686-693`), não cores de área principal.
3. **`brands/leo-lions/variants.json:31`** define `accent: #00AB68` para Leo; o guia não elege um "accent" único, apenas diz que a paleta primária inteira serve para áreas/tipo/acentos (`guia-de-marca/leo/guia-leo-texto.md:106-108`) e que títulos usam verde e azul com pesos pesados (`:228-230`).
4. **`guia-de-marca/leo/tokens-submarcas.json:29`** diz plaqueta `"Leo"`; o guia Leo-Lion diz nameplate **"Leo-Lion"** (`guia-de-marca/leo/guia-leo-lion-texto.md:73-75`).
5. **`guia-de-marca/tokens-oficiais.json:33`** afirma que "o guia NÃO tem seção própria de Leo" e que os ativos estão só em kits/logos; está **desatualizado** face aos guias separados de Leo e Leo-Lion (README.md:24-26 e §7).
6. **`guia-de-marca/leo/tokens-submarcas.json:36`** diz "35 a 96"; o guia inclui 97 Black Condensed (`guia-de-marca/guia-pt-texto.md:839-841`).
7. **PNGs Lions com cores legadas** `#00529B`/`#FFCF06`/`#54565B` contra `#00338D`/`#EBB700`/`#55565A` dos tokens (ver §2).
8. **Arredondamentos:** o laranja é RGB 255/92/53 (converte para `#FF5C35`) mas o HTML do guia é `#FF5B35` (`guia-de-marca/tokens-oficiais.json:15,17`); o verde é RGB 0/172/105 (`#00AC69`) e o HTML é `#00AB68` (`guia-de-marca/leo/tokens-submarcas.json:11`).
9. **`guia-de-marca/tokens-oficiais.json:33`** lista `LEO1` e `LL1` como se ambos fossem ativos de Leo; `LL1` é o kit **Leo-Lions** (`canva-links/canva-kits.json:456`; `graficos-prontos/manifesto.json:403-483`).
10. **`brands/leo-lions/variants.json:18`** trata `Emblemas_do_Lions/` e `Assinaturas_de_Lions_Clubs_International/` como fontes da mesma variante `lions`, mas o guia separa Lions International (mestre), LCI (governança/advocacia) e LCIF (arrecadação) (`guia-de-marca/guia-pt-texto.md:47-61`); usar assinatura LCI com texto "Lions International" troca a marca.

## 5. Marca Leo

**O que é.** Leo clube é atividade juvenil de Lions clubes; os membros são responsáveis, voltados à comunidade e têm paixão por servir (`guia-de-marca/leo/guia-leo-texto.md:46-50`).

**Cores.** Paleta primária própria: cinza Cool Gray 11, amarelo 7406, azul claro 660 e verde 3405; mais brilhante que a Lions para diferenciar, e **sem** o azul 287 como primária (`guia-de-marca/leo/guia-leo-texto.md:100-108`). O texto do guia não descreve a "forma" do emblema; a arte `109141433` mostra a cabeça de leão estilizada, e o guia qualifica o emblema como "refreshed", em Cool Gray 11 (`:72-75`). As únicas interpretações aceitáveis são as da página; não se pode reconstruir nem alterar; há versões com texto cinza e texto branco (`:76-84`). Alpha e Ômega têm designações próprias; para os dois grupos, só o emblema Leo, sem designação (`:85-90`).

**Tipografia e elemento gráfico.** Helvetica Neue como primária, Helvetica/Arial/Times como padrão (`:145-147`, `:182-185`); seta como elemento gráfico primário e títulos em verde/azul com pesos mais pesados (`:228-232`).

**Tom.** O guia pede sagacidade e brincadeira como no Lions, mas energético, comprometido e apaixonado; sem frases excessivamente coloquiais; títulos diretos e vivos (`:54-59`). Exemplos oficiais: "Leos get things done.", "Leo like you mean it.", "Where there's a need, there's a Leo." (`:61-63`).

**Lema oficial em português.** **Não encontrei** lema de Leo em português. O guia Leo (EN) não tem seção "motto"; os três exemplos acima são "HEADLINE EXAMPLES", não lema. O lema oficial do Lions em PT é "Nós Servimos" (`guia-de-marca/guia-pt-texto.md:219`), que não é lema de Leo. Uma tradução de "Where there's a need, there's a Leo." seria adaptação, não texto oficial.

**Leos com Lions.** O programa Leo-Lion é o caminho de ex-Leos que se tornam Lions; a comunicação deve falar a Leos e Lions, ecoando a voz Lions e construindo sobre a identidade Leo (`guia-de-marca/leo/guia-leo-lion-texto.md:46-52`). A assinatura primária tem três componentes — emblema Lions International, plaqueta "Leo-Lion" e setas — e não pode ser recriada; a primária não vai sobre azul, e as 1C sólidas vão em qualquer fundo com contraste (`:73-82`). A fita azul ancora as composições (`:257-259`); todos os Lions podem servir em clubes Leo-Lion, que são multigeracionais (`:222-226`).

**Kits e página de logotipos.** O manifesto agrupa 7 gráficos do kit `leos` (`graficos-prontos/manifesto.json:333-393`) e 9 do kit `leolions` (`:403-483`), em formatos como 1080×1080, 1080×1920, 1920×1080 e 820×462. Os modelos Canva aparecem como "Leos – LEO1" (`canva-links/canva-kits.json:339,363,380,411`) e "Leo-Lions – LL1" (`:456,487`); são raster/visualização, não editáveis sem OAuth (`README.md:58-64`). A página de logotipos lista as seções "Emblemas de Leos" e "Logotipos de Leo a Leão" e explica que PNG é o formato para fundo transparente e EPS o vetorial (`paginas-vivas/logos-emblems.json:5`).

**A nota do README está desatualizada?** A frase do `README.md:24-26` **não está**: ela diz que o guia *geral* não tem seção de Leo, mas existem guias separados de Leo e Leo-Lion, e remete ao §7. O que está desatualizado é `guia-de-marca/tokens-oficiais.json:33`, que fala como se não houvesse guia próprio e só cita kits/logos. Se a nota for lida sem a palavra "geral", ela envelhece; com ela, está correta.

## 6. Voz e mensagem

`brands/leo-lions/voice.json:19-30` define o tom Leo como "espírito brincalhão como o do Lions, mas energético, comprometido e apaixonado; títulos diretos e vivos, sem coloquialismo excessivo". Os `termos_proibidos` são só "coloquialismo excessivo" (`:26-28`); **não há lista de palavras proibidas** para Leo, e a própria nota diz que o guia proíbe frases "too colloquial" (`:30`). Para Lions, o `brands/leo-lions/voice.json:11-15` proíbe "LI", "LCI" e "Lions"/"Lions Clubs" como substituto de "Lions Clubs International"; o guia confirma não abreviar "LI" (`guia-de-marca/guia-pt-texto.md:201`) e evitar "LCI" (`:231-232`).

O `brands/leo-lions/voice.json` **não tem campo "formato"**. O formato vem do guia: título de alto nível/emotivo, subtítulo explicativo, corpo com ritmo e CTA forte, convidativo e claro (`guia-de-marca/guia-pt-texto.md:294-312`). Para Leo, acrescentar títulos diretos e vivos, sem coloquialismo (`guia-de-marca/leo/guia-leo-texto.md:54-59`).

**3 mensagens candidatas para feed Leo** (título ≤8 palavras, corpo ≤15, um CTA; nenhuma usa datas, números ou fatos não verificados):

| # | Título (palavras) | Corpo (palavras) | CTA | Âncora no acervo |
|---|---|---|---|---|
| 1 | **Leos fazem acontecer** (3) | Energia, compromisso e paixão para servir a comunidade. (8) | **Conheça o Leo.** (3) | `guia-de-marca/leo/guia-leo-texto.md:46-50` (comunidade/paixão), `:54-59` (energético/comprometido/apaixonado), `:61` ("Leos get things done.") |
| 2 | **Onde há necessidade, há um Leo** (6) | Um Leo enxerga a necessidade da comunidade e serve. (9) | **Participe do Leo.** (3) | `guia-de-marca/leo/guia-leo-texto.md:63` (headline oficial), `:46-50` (serviço à comunidade) |
| 3 | **Serviço jovem com energia Leo** (5) | Clubes de jovens que servem com paixão e espírito. (9) | **Saiba mais em lionsclubs.org.** (4) | `guia-de-marca/leo/guia-leo-texto.md:46` (atividade juvenil), `:57` (energético); `guia-de-marca/guia-pt-texto.md:177` (lionsclubs.org) |

As três são **adaptações em PT** de tom/posicionamento, não traduções oficiais: o guia Leo só publica headlines em inglês (`:61-63`). A #2 é a mais literal; se o dono exigir texto oficial, usar o inglês ou aprovar a adaptação. Nenhuma promete resultado, número ou data; "jovens" vem de "youth activity" (`:46`), não de estimativa.

## 7. Lacunas

| Lacuna | Evidência | O que decidir com o dono |
|---|---|---|
| **Fonte da marca** | 0 `.ttf/.woff`; 9 `.otf` que são MinionPro/TypeNo3; Helvetica Neue, Caslon e Roboto ausentes (`find`); Roboto é a única substituta aberta admitida (`guia-de-marca/guia-pt-texto.md:924-927`) | licenciar Helvetica Neue; obter Roboto offline para o LXC; ou aceitar Helvetica/Arial (também ausentes no Linux) |
| **Logo Leo em fundo azul escuro** | só há texto branco nas versões Alpha (`109141430`) e Ômega (`109141435`); o geral `109141433` é cinza e dá 1,54:1 sobre `#00338D` | manter azul escuro (exige peça de Alpha/Ômega) ou trocar para fundo claro/da paleta Leo e usar `109141433` |
| **Logo Leo com palavra "Leo" para o grupo geral** | o guia manda usar só o emblema quando o conteúdo é para Alpha e Ômega (`guia-de-marca/leo/guia-leo-texto.md:85-90`); o PNG geral é só emblema | aceitar emblema sem wordmark ou definir que a peça é de um grupo (Alpha/Ômega) |
| **Regras Leo/Leo-Lion** | os guias próprios não têm clearspace, tamanho mínimo nem posição; só o guia Lions tem (`guia-de-marca/guia-pt-texto.md:422-440`) | aplicar as regras Lions por analogia (decisão registrada) ou pedir aprovação à marca |
| **PNGs Lions com cor legada** | `#00529B/#FFCF06/#54565B` vs `#00338D/#EBB700/#55565A`; EPS diz 287+7406 (§2) | usar PNG legado, renderizar EPS (ferramenta/licença) ou aceitar o desvio |
| **Assinatura LI em alta** | PNGs LI só 360×360, conteúdo útil ~268×166; LCI 3C tem 1780×300 | usar LCI 3C (cor legada) ou obter/renderizar arte vetorial |
| **Mensagem oficial em PT** | não há lema nem headline de Leo em PT; só exemplos EN (`guia-de-marca/leo/guia-leo-texto.md:61-63`) | aprovar as 3 adaptações ou produzir versão oficial com a marca |
| **Foto e direitos** | biblioteca sem termos de uso; pessoas exigem autorização (`README.md:108-109`) | escolher foto autorizada com espaço negativo e confirmar uso |
| **Datas de fundação** | 07/06 e 10/10 continuam **não verificadas** (`README.md:78`) | não usar em copy; se necessário, verificar na fonte oficial |
| **Canva editável** | OAuth do dono pendente (`README.md:62`) | decidir se a produção fica no código (HTML/CSS + logos) ou no Canva |

**Não verificado:** não reexecutei `shasum -a 256 -c SHA256SUMS.txt` sobre os 1.285 arquivos; não abri os PDFs, usei os textos extraídos; não há EULA de fonte no acervo; não há regra de posição nem mínimo digital para Leo; não há guia Leo em PT (o README:79 diz que não foi verificado em todos os idiomas); não testei renderização no LXC (rede/kit proibidos nesta lane).
