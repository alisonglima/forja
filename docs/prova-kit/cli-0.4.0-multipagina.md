# PDF de várias páginas no `@feimacode/open-design-agent-kit@0.4.0` (folder A5 de 4 páginas)

Leitura da fonte em `.work/kit-src/open-design-agent-kit-0.4.0/out/index.js` (bundle de 8,8 MB, 197.386 linhas). As citações `index.js:LINHA` apontam para esse bundle. Nada foi executado; o número de páginas e o tamanho nominal abaixo são previsão pela fonte, não medição.

## 1. Como o kit decide o número de páginas de `--format pdf`

Há três caminhos, escolhidos em `plan` e em `runExport` (`index.js:192612-192616`, `index.js:192703-192709`):

- **Modo página (`page-pdf`)** — é o `pdf` de um artefato que não é deck e não caiu no caminho de impressão (`index.js:181548-181549`). A exportação chama `capturePagePdf` uma vez por linha de dados (`index.js:192943`), que faz `emulateMediaType("print")` e `page.pdf({ format: "a4", preferCSSPageSize: true, printBackground: true, margin: 0 })`, **sem `pageRanges`** (`index.js:181664-181671`). O número de páginas é o da paginação do Chromium sobre o documento inteiro: cada página CSS gerada por `@page`/`break-after`/`page-break-after` vira uma página do PDF. O kit não conta cards nesse modo.
- **Modo card/impressão (`print-pdf`)** — `printPath` só é verdadeiro quando o canvas é um formato de impressão (preset `a5`, `a4`, etc., ou `metadata.format` de impressão), o formato é `pdf` e **não** há `--width`/`--height` (`index.js:192613`). Quando é verdadeiro, o modo é forçado antes de qualquer detecção de deck (`index.js:192705-192706`). `preparePrintPage` chama `isolateCardForPrint`, que pega **o primeiro** `document.querySelector(cardSelector)`, esconde os irmãos e os ancestrais e injeta um `@page` do tamanho do bleed (`index.js:178807-178841`, `index.js:179247-179250`). `printBleedPage` chama `page.pdf` com `pageRanges: "1"` (`index.js:179251-179262`). Resultado: **uma página por linha** (o primeiro card; frente e verso podem virar duas, ver item 3).
- **Modo deck (`deck-pdf`)** — `resolveExportMode` devolve `deck-pdf` quando `isDeck` é verdadeiro (`index.js:181548-181549`). Cada slide selecionado é capturado como PNG (`index.js:181594-181615`) e `assemblePdf` embute uma imagem por página (`index.js:189114-189128`), chamado em `index.js:193042`. **Um slide = uma página**, mas a página é uma imagem, não uma página CSS.

`--selector` não combina com `--format pdf` (`index.js:192411-192412`), então não serve para recortar os quatro cards em quatro páginas.

## 2. Deck

**Detecção de slide.** O seletor é `SLIDE_SELECTOR = ".slide, [data-screen-label], .deck-slide, .ppt-slide"` (`index.js:181508`); a contagem exclui clones dentro de `.mini-slide, .overview, .notes-overlay, .thumb` (`index.js:181297-181300`, `index.js:181509`). `isDeck` é inferido por `kind === "deck"`, `renderer === "deck-html"` ou `slideCount >= 2` com `sourceSkillId` começando em `od:deck:` (`index.js:181520`); `--deck` força `isDeck` (`index.js:181521`). Deck `pdf`/`pptx` sem nenhum slide falha com `no-slides` (`index.js:181535-181536`).

**Estrutura exigida.** Basta pelo menos um elemento que case com o seletor. Não há wrapper obrigatório, mas `prepareDeckStage` esconde a chrome de apresentação (`index.js:181300-181315`, chamado em `index.js:181565-181582`) e `pinDeckStage` fixa `html`, `body`, `.deck` e o stage no tamanho medido (`index.js:181316-181319`). O tamanho do slide é lido de `width`/`height` (atributo, estilo, computado ou `offset`) ou do `deck-stage`, com padrão **1920×1080** (`index.js:181321-181379`, `index.js:181513-181514`).

**Tamanho da página do PDF de deck.** `PDF_PAGE_LONGEST_PT = 960` (`index.js:189114`); a página recebe o lado maior de 960 pt e o menor pela proporção da imagem (`index.js:189121-189123`). Um slide 1920×1080 vira página de **960×540 pt** (13,33×7,5 in), não A5.

**`--deck` com `--preset a5`.** `a5` é formato de impressão 148×210 mm (`index.js:174331`). Com `--format pdf --deck --preset a5` e sem `--width`/`--height`, `printPath` fica verdadeiro (`index.js:192613`) e o modo vira `print-pdf` (`index.js:192706`): o kit imprime **só o primeiro** `[data-od-card]`, em uma página A5 (sem `[data-od-card]` falha com `selector-no-match`, `index.js:192810`). O deck é ignorado. Se você acrescentar `--width`/`--height`, `printPath` é desligado (`index.js:192613`) e o `deck-pdf` roda, mas a página continua com 960 pt no lado maior. **Não existe combinação de `--deck` com `--preset a5` que produza 4 páginas A5 nominais.**

**`--slides`.** É uma lista de números 1-based separados por vírgula, não vazia (`index.js:195199-195206`); sem deck, falha com `not-a-deck` (`index.js:181539-181543`); fora do intervalo 1–`slideCount`, falha (`index.js:181557-181560`); no deck, captura apenas os números listados (`index.js:181596`). Com 4 slides e sem `--slides`, exporta 1, 2, 3 e 4.

## 3. Frente e verso (`cardFaces`)

`cardFaces` é lido no `pageMode` (imagem ou PDF de página/impressão): para cada `[data-od-card]`, o kit guarda `{ back: el.getAttribute("data-od-side") === "back", fields: ... }` (`index.js:192783-192785`). O verso é marcado, portanto, com **`data-od-side="back"`**; o front é qualquer `[data-od-card]` sem esse atributo. `hasBack` exige ao menos um verso e que o print house não tenha `backs: "none"` (`index.js:192786`); os índices de frente e verso são separados em `frontIndexes`/`backIndexes` (`index.js:192787-192788`) e um verso único é tratado como verso compartilhado (`index.js:192789-192790`).

No `print-pdf`, o kit imprime a **primeira frente** (`frontIndexes[0]`, `index.js:192930`), procura o verso cujo `frontsOfBack` inclui essa frente (`index.js:192931`), mostra o verso com `showCardForPrint` (`index.js:178842-178854`, `index.js:192933-192939`) e junta `[front, backPdf]` com `mergePdfs` (`index.js:192940`). Isso gera **duas páginas** (frente + verso) por linha.

**Não serve para 4 páginas.** O caminho de impressão sempre parte da primeira frente e de no máximo um verso; com 4 `[data-od-card]` sem verso o PDF continua com **1 página**, e com um verso ele chega a **2**, não a 4. `cardFaces` não é um mecanismo de paginação de N cards.

## 4. Receita para 4 páginas A5

### Receita A (recomendada): modo página, sem preset de impressão

É a mais simples e a que deve preservar texto vetorial, fontes e RGB: o PDF sai do `page.pdf` do Chromium (`index.js:181664-181671`), sem passar por `isolateCardForPrint` nem por `assemblePdf`.

**HTML completo da fixture (`fixtures/folder4.html`):**

```html
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Folder A5 — 4 páginas</title>
<style>
  @page { size: 148mm 210mm; margin: 0; }
  html, body { margin: 0; padding: 0; }
  .pagina {
    width: 148mm; height: 210mm; box-sizing: border-box;
    padding: 14mm; overflow: hidden;
    background: #f7f4ee; color: #1d2a36;
    font-family: "DejaVu Sans", "Noto Sans", sans-serif;
    break-after: page; page-break-after: always;
  }
  .pagina:last-child { break-after: auto; page-break-after: auto; }
  .faixa { height: 6mm; margin-bottom: 8mm; background: #2f6f6a; }
  h1 { margin: 0 0 6mm; font-size: 20pt; }
  p { margin: 0 0 4mm; font-size: 10.5pt; line-height: 1.5; }
</style>
</head>
<body>
<section data-od-card class="pagina"><div class="faixa"></div><h1>Capa</h1><p>Ação, Conceição e Coração</p><p>Folder de quatro páginas A5 para a prova K.2.</p></section>
<section data-od-card class="pagina"><div class="faixa"></div><h1>Boas-vindas</h1><p>Conceição recebe você</p><p>Texto selecionável na segunda página do folder.</p></section>
<section data-od-card class="pagina"><div class="faixa"></div><h1>Programação</h1><p>Ação cultural e oficinas</p><p>Agenda com títulos e horários em texto vetorial.</p></section>
<section data-od-card class="pagina"><div class="faixa"></div><h1>Contato</h1><p>Coração da comunidade</p><p>Endereço e canais de contato na última página.</p></section>
</body>
</html>
```

Cada `<section>` é um `[data-od-card]` (`index.js:192379`) e cada uma mede 148×210 mm com `break-after: page`; a última desliga o break para não criar uma quinta página vazia. O `@page` de 148×210 mm é o que o `preferCSSPageSize: true` usa (`index.js:181664-181671`).

**Sidecar (`fixtures/folder4.html.artifact.json`):**

```json
{
  "version": 1,
  "kind": "html",
  "entry": "folder4.html",
  "renderer": "html",
  "exports": ["pdf"],
  "status": "complete"
}
```

`version` é sempre 1 (`index.js:177866`); `kind: "html"` e `renderer: "html"` estão nas listas permitidas (`index.js:177881-177900`); `exports` não pode ser vazio e `pdf` é permitido (`index.js:177903`, `index.js:177949-177956`). **`metadata` deve ficar ausente** (equivale a `{}`; o importante é não ter `format` de impressão): `metadata.format` vira `recordedFormat` (`index.js:192590-192592`) e, se for um formato de impressão como `a5`, liga o `printPath` de uma página (`index.js:192613`). O sidecar tem de existir antes do `export`; sem ele o kit responde `not-registered` (`index.js:192559-192560`, leitura em `index.js:178198-178214`).

**Comando:**

```sh
cd "$WS"
OPEN_DESIGN_BROWSER_PATH=/usr/local/bin/google-chrome-prova \
npx --yes @feimacode/open-design-agent-kit@0.4.0 \
  export fixtures/folder4.html \
  --format pdf \
  --workspace "$WS"
```

`--format pdf` está na definição do subcomando (`index.js:196227`). **Não passe `--preset a5`** (ligaria `print-pdf`, uma página: `index.js:192613`/`index.js:192706`), **nem `--bleed 0`** (sem `printPath` o kit rejeita: `bleed and cropMarks apply to PDF exports of print formats`, `index.js:192645`), **nem `--selector`** (proibido com `pdf`: `index.js:192411-192412`), **nem `--deck`/`--slides`**. A saída vai para `<dir do entry>/exports/folder4.pdf` (`index.js:192455-192463`). A fixture atual (`scripts/prova-kit/export-pdf.mjs:79-81`) já tem `break-after: page` e `@page` A5; o que a transforma em 1 página é o `--preset a5` da linha 41 mais o `metadata.format: "a5"` da linha 86. O `--bleed 0` da linha 42 também tem de sair, senão o kit rejeita sem `printPath` (`index.js:192645`).

### Receita B: deck de 4 slides (4 páginas, mas não A5)

Se o requisito for "kind deck", use 4 elementos que casem com `SLIDE_SELECTOR` (`index.js:181508`), por exemplo `<section class="slide" width="1920" height="1080">…</section>` repetido 4 vezes; sidecar `{ "version": 1, "kind": "deck", "entry": "deck4.html", "renderer": "deck-html", "exports": ["pdf"], "status": "complete" }`; comando `export fixtures/deck4.html --format pdf --deck --workspace "$WS"` (sem `--preset`). O `deck-pdf` captura os 4 slides (`index.js:181594-181615`) e `assemblePdf` escreve 4 páginas de 960×540 pt (`index.js:189114-189128`, `index.js:193042`). **Perde texto selecionável e fontes embutidas**, porque cada página é um PNG; a página também não é A5.

Ordem por simplicidade: **A** (modo página) e depois **B** (deck). A deve preservar texto vetorial, fontes embutidas e RGB; B não (é imagem).

## 5. Tamanho nominal

A5 é 148×210 mm (`index.js:174331`). Com `PT_PER_MM = 72 / MM_PER_INCH` (`index.js:179235`) e `MM_PER_INCH = 25,4` (`index.js:174356`), o nominal é **419,53×595,28 pt** (148×72/25,4 = 419,5276; 210×72/25,4 = 595,2756).

A **Receita A** mantém esse nominal: o `@page { size: 148mm 210mm }` do HTML é usado por `capturePagePdf` com `preferCSSPageSize: true` (`index.js:181664-181671`). É previsão pela fonte; não foi medido. A **Receita B** não mantém: a página do deck é normalizada para 960 pt no lado maior (`index.js:189114-189123`), então um slide 16:9 sai 960×540 pt e um slide com proporção A5 sairia 676,57×960 pt — nunca 419,53×595,28 pt.

## 6. Limites

**Não encontrei limite explícito de slides ou de páginas** no caminho de exportação: `captureDeckSlides` monta `1..slideCount` sem teto (`index.js:181596`) e `validateSlideNumbers` só valida o intervalo 1–`slideCount` (`index.js:181557-181560`). O `check` de deck limita a **folha de miniaturas** a 12 slides (`SHEET_SLIDES = 12`, `index.js:183157`; uso em `index.js:183677-183700`), mas isso não limita o PDF. `MAX_OUTPUTS = 400` limita linhas de dados × shapes, não slides (`index.js:192381`, `index.js:192674-192677`).

**Com 4 slides:** sem `--slides`, os números são 1, 2, 3 e 4 (`index.js:181596`), todos são capturados e `assemblePdf` emite **4 páginas** (`index.js:189121-189127`). Com `--slides 1,3`, saem 2 páginas; com `--slides 5` em um deck de 4, o erro é `Slide number(s) 5 out of range — this deck has slides 1–4` (`index.js:181557-181560`); com zero slides e `--deck --format pdf`, o erro é `no-slides` (`index.js:181535-181536`). Na Receita A, o número de páginas é o da paginação CSS do Chromium; o kit não impõe teto.

## 7. Se não for possível produzir 4 páginas A5 pelo kit

**É possível, pela Receita A**, que é o modo página do próprio kit: 4 `[data-od-card]`, `@page` A5 e `break-after: page`, sem `--preset` de impressão. O que **a fonte não permite** é obter 4 páginas A5 **pelo modo deck**: `deck-pdf` normaliza toda página para 960 pt no lado maior (`index.js:189114-189123`) e rasteriza os slides (`index.js:181594-181615`, `index.js:189114-189128`); `--preset a5` com `--deck` cai antes no `print-pdf` de uma página (`index.js:192613`, `index.js:192706`).

Se o requisito exigir o caminho de deck e A5 exato, a alternativa mais simples **fora do kit** é exportar cada card em um PDF de uma página (quatro exports) e juntar com `qpdf --empty --pages a.pdf b.pdf c.pdf d.pdf -- folder4.pdf`; isso não usa o kit para paginar e precisa ser validado à parte. A Receita A evita essa junção.

## 8. O que NÃO foi verificado

- Nada foi executado: o número real de páginas, o `pdfinfo` (419,53×595,28 pt), `pdffonts`, `pdftotext` e `pdfimages` do PDF da Receita A não foram medidos.
- Se o Chromium da prova honra `@page { size: 148mm 210mm }` com `preferCSSPageSize: true` e se `break-after: page` produz exatamente 4 páginas sem uma quinta página vazia.
- Se as fontes `DejaVu Sans`/`Noto Sans` estão instaladas no Chrome da prova e se o PDF final embute os subsets; a fonte do kit não garante isso, quem resolve é o Chromium.
- Se o sidecar sem `metadata.format` passa em `writeArtifactManifest` e se o `export` grava os registros em `metadata.exports` sem alterar o comportamento de uma segunda execução.
- O comportamento real de `--deck --preset a5` (a leitura prevê `print-pdf` de 1 página) e do `deck-pdf` com 4 slides.
- Se o PDF da Receita A é RGB e se o texto continua selecionável; a expectativa vem de o caminho ser `page.pdf` (`index.js:181664-181671`), não de medição. A nota de RGB do kit (`index.js:179305`) é do caminho de impressão.
- A existência/executabilidade de `/usr/local/bin/google-chrome-prova`, o `npx` offline e a junção com `qpdf` da seção 7.
