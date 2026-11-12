# Comportamento real do `@feimacode/open-design-agent-kit@0.4.0`

Leitura da fonte em `.work/kit-src/open-design-agent-kit-0.4.0/` (`out/index.js`, bundle de 8,8 MB). As citações `index.js:LINHA` apontam para esse bundle. Nada foi executado.

## 1. Programa raiz e subcomandos

O programa se chama `open-design-agent-kit` (`index.js:196211`). A definição do `Command` (`index.js:196211`–`196256`) **não registra `.version()`**, então `--version` não existe e o Commander responde `error: unknown option '--version'`. Os subcomandos são: `init [path]`, `install <app>`, `uninstall <app>`, `export <entryPath>`, `check <entryPath>`, `preview [entryPath]` e `render-video <compositionDir>` (`index.js:196212`–`196251`).

`export` (`index.js:196227`):

| opção literal | valor / padrão |
|---|---|
| `--width <px>`, `--height <px>` | juntos; inteiros 16–8192; padrão é o tamanho da skill/origem |
| `--scale <n>` | 1–3; padrão 2 em deck pdf/pptx, senão 1 |
| `--format <png\|jpeg\|pdf\|pptx\|standalone\|site\|email\|paste>` | descrição; o parser também aceita `jpg`, `mp4`, `webm` e `gif` (`index.js:195193`–`195198`) |
| `--target <wechat\|notion\|newsletter\|generic>` | só `paste` |
| `--base-url <https-url>` | `site`, `email`, `paste` |
| `--embed-assets` | `standalone`: baixa e embute assets 3D remotos |
| `--max-resolution <1k\|2k\|4k>` | com `--embed-assets`; padrão 1k |
| `--quality <1-100>` | JPEG; padrão 90 |
| `--selector <css>` | cada elemento vira uma imagem; exemplo `"[data-od-card]"` |
| `--max-bytes <n>` | orçamento por arquivo; reencoda em JPEG |
| `--deck` | trata como deck (auto para `kind: "deck"`) |
| `--slides <list>` | decks: números 1-based, ex. `1,3` |
| `--editable` | só `--format pptx` |
| `--preset <format>` | id de formato de tela ou impressão (lista na seção 6) |
| `--bleed <mm>` | PDF de impressão; 0–20; padrão do formato |
| `--crop-marks` | PDF de impressão: marcas de corte |
| `--dpi <150-600>` | PNG/JPEG de formato impresso; padrão 300 |
| `--print-house <id>` | tamanho exato de gráfica; exige preset/formato gravado |
| `--check` | só preflight; não grava arquivos |
| `--data <file>` | CSV, XLSX ou JSON-array; uma saída por linha |
| `--sheet <name>` | só XLSX; primeira aba por padrão |
| `--name-field <column>` | coluna que nomeia o arquivo da linha |
| `--presets <list>` | 1–15 ids, sem repetição; exige design fluido |
| `--fps <n>` | mp4/webm/gif; 1–60; padrão 30 (15 em gif) |
| `--duration <seconds>` | mp4/webm/gif; 0,5–60; padrão da página |
| `--loop` / `--no-loop` | gif: repetir (padrão) / tocar uma vez |
| `--ffmpeg <path>` | mp4/webm/gif; padrão `OPEN_DESIGN_FFMPEG_PATH` |
| `--transparent` | PNG sem fundo |
| `--campaign-sheet`, `--shape-sheet` | folhas extras de design fluido |
| `--split` | PDF com `--data`: um PDF por linha |
| `--badge` / `--no-badge` | `standalone`/`site`; padrão ligado em site, desligado em standalone |
| `--browser <path>` | Chrome/Edge/Chromium; padrão `OPEN_DESIGN_BROWSER_PATH` |
| `--workspace <dir>` | raiz; padrão ancestral mais próximo com `.open-design/` |

`check` (`index.js:196235`): `--viewport <name:WxH>` (repetível, até 4), `--slides <list>`, `--max-images <n>` (0–6, padrão 3), `--at <seconds>` (1–6 tempos), `--views <list|none>`, `--no-states`, `--screenshots <dir>`, `--fail-on <error|warning>`, `--json`, `--browser <path>`, `--workspace <dir>`.

`render-video` (`index.js:196251`): `--output <file.mp4>` é `requiredOption`; `--quality <draft|standard|high>` tem padrão `high`.

## 2. Resolução do workspace

`resolveWorkspace(entryPath, explicit, cwd)` (`index.js:195254`):

1. Se `--workspace` foi passado, vence sempre: `root = path.resolve(cwd, explicit)`, `visible: false` (`index.js:195255`).
2. Senão parte de `dirname(path.resolve(cwd, entryPath))` e sobe diretório por diretório. O primeiro que contiver um diretório `.open-design/` vira `root` com `visible: false` (`index.js:195256`–`195259`).
3. Se o diretório atual se chamar exatamente `Open Design`: se o pai tiver `.open-design/`, `root` é o pai, `visible: true` e `designsDir: "Open Design"`; senão `root` é o próprio diretório e `designsDir: "."` (`index.js:195260`–`195262`).
4. Se chegar à raiz do sistema, `root = cwd`, `visible: false` (`index.js:195263`).

`visible`/`designsDir` mudam a saída: no layout visível, imagens/PDFs vão **ao lado do design**, sem subpasta `exports/`; no layout clássico vão para `exports/` (`index.js:195286`, `index.js:192455`–`192463`).

Não há leitura de `OPEN_DESIGN_WORKSPACE_ROOT` nem de `OPEN_DESIGN_DEFAULT_WORKSPACE`: a fonte só lê as quatro variáveis da seção 7. A precedência é, portanto, `--workspace` > ancestral com `.open-design/` > `cwd`.

Se o `entryPath` resolver para fora do workspace, `assertWorkspaceRelative` lança `entryPath escapes the workspace: <path>` (`index.js:178178`–`178184`); `export` captura e devolve `Export failed (invalid-args): ...`, exit 1 (`index.js:192552`–`192556`), e `check` idem (`index.js:183252`–`183256`).

## 3. Registro do artefato (sidecar)

O sidecar é `<entry>.artifact.json`, texto JSON (`index.js:178175`–`178177`). `MANIFEST_VERSION` é `1` (`index.js:177866`). O manifesto gravado tem `version`, `kind`, `title`, `entry`, `renderer`, `status`, `exports`, `primary`, `supportingFiles`, `createdAt`, `updatedAt`, `sourceSkillId`, `designSystemId`, `collectionId`, `collectionName`, `screenRole`, `screenIndex`, `explorationId`, `directionId`, `sources` e `metadata` (`index.js:178063`–`178088`).

A validação (`validateArtifactManifestInput`, `index.js:177934`) exige de fato:

- `kind`: string de até 64 caracteres, em `html`, `deck`, `react-component`, `markdown-document`, `svg`, `diagram`, `code-snippet`, `mini-app`, `design-system` (`index.js:177881`–`177889`);
- `renderer`: string em `html`, `deck-html`, `react-component`, `markdown`, `svg`, `diagram`, `code`, `mini-app`, `design-system` (`index.js:177890`–`177900`);
- `exports`: array não vazio, só com `html`, `pdf`, `zip`, `jsx`, `md`, `svg`, `txt`, `png`, `jpeg`, `pptx`, `standalone`, `site` (`index.js:177903`, `index.js:177949`–`177956`).

`title`, `entry`, `status`, `version` e `metadata` são opcionais na validação; `title` cai para o `entry`, `status` cai para `complete`, `entry` cai para o caminho do artefato e a gravação sempre põe `version: 1` (`index.js:178061`–`178075`). **Não existe `kind: "page"` nem `kind: "card"`**: página e card são `kind: "html"` com `renderer: "html"`; deck é `kind: "deck"` com `renderer: "deck-html"`.

Exemplos mínimos válidos (o JSON não carrega tamanho; o tamanho vem do CSS e, para o `check`, de `metadata.format`):

```json
{ "version": 1, "kind": "html", "entry": "pagina.html", "renderer": "html",
  "exports": ["html", "pdf", "png"], "status": "complete" }
```

```json
{ "version": 1, "kind": "html", "entry": "cartao.html", "renderer": "html",
  "exports": ["png"], "metadata": { "format": "ig-portrait" } }
```

```json
{ "version": 1, "kind": "html", "entry": "story.html", "renderer": "html",
  "exports": ["png"], "metadata": { "format": "story" } }
```

Para deck: `{ "kind": "deck", "renderer": "deck-html", "exports": ["pdf", "pptx"] }` (mais `entry`/`version` se quiser).

**Quem cria o sidecar:** nenhum subcomando do CLI. `init` só escreve skills e registro MCP (`index.js:196212`–`196225`). `export`/`check` apenas leem; sem sidecar devolvem `not-registered` com a mensagem `exists but isn't registered (no .artifact.json sidecar)` e exit 1 (`index.js:192557`–`192560`, `index.js:183257`–`183260`). O `export` bem-sucedido **atualiza** o sidecar com os registros de exportação, mas só depois de já ter lido um manifesto existente (`index.js:193061`–`193075`). Quem cria é a ferramenta MCP `register_open_design_artifact` (citada nas mensagens, `index.js:178157`–`178163`), não o CLI. Na prática, o script de prova tem de gravar o `<entry>.artifact.json` antes de chamar `export`/`check`.

`inferLegacyManifest` (`index.js:178102`) é o fallback do registro, não do `export`: para `.html`/`.htm` infere `kind: "html"`/`renderer: "html"` (ou `deck`/`deck-html` se o nome contiver `deck`, `slides` ou `pitch`), `exports: ["html","pdf","zip"]`; para `.md`, `markdown-document`/`markdown`; para `.svg`, `svg`/`svg`; senão devolve `null` e o registro falha com `artifactManifest is required` (`index.js:178102`–`178165`). Ele não escreve arquivo; `writeArtifactManifest` é que grava (`index.js:178186`–`178196`). `readArtifact` faz `JSON.parse` do sidecar sem validar o schema e, se o JSON for inválido, trata como ausente (`index.js:178198`–`178214`).

## 4. Saída do `export`

Layout clássico: `<dir do entry>/exports/` (`exportDirFor`, `index.js:192455`). O nome base é o `basename` do entry sem extensão (`index.js:192459`):

- PNG: `<base>.png`; JPEG: `<base>.jpg`; PDF: `<base>.pdf`; PPTX: `<base>.pptx` (`index.js:192454`, `index.js:192463`).
- `--selector` com vários elementos: `<base>-01.png`, `<base>-02.png`…; deck: `<base>-01.png`… (`index.js:192461`–`192463`).
- Com `--presets` (ou layout visível): sufixo do formato, ex. `<base>-ig-portrait.png`; no layout visível também se usa o `fileLabel` (`index.js:192756`, `index.js:192835`–`192838`, `index.js:192455`–`192457`).
- Com `--data`: sufixo do slug da linha (ou do número), antes do formato (`index.js:192203`–`192275`).
- PDF de impressão com preset: `<base>.pdf`; com `--split` e dados: um PDF por linha (`index.js:192959`–`192965`).

`OPEN_DESIGN_OUTPUT_DIR` **não existe na fonte** e não é lido por `export`/`check`; não há como redirecionar a pasta por ambiente. A única redireção é o layout visível (`Open Design`) e o próprio caminho do entry.

Stdout do `export` bem-sucedido: uma linha absoluta por arquivo, `path.join(workspaceRoot, arquivo)` (`index.js:195294`–`195295`). O resumo (`Exported N file(s)`, tamanhos, avisos, preflight) vai para **stderr** via `console.error(formatExportResult(result))` (`index.js:195296`, `index.js:193120`). Em falha, não há stdout de sucesso; stderr recebe `Export failed (<code>): <erro>` e a URL de troubleshooting (`index.js:195290`–`195291`), com exit 1. Sucesso retorna 0 (`index.js:195297`).

## 5. `check`

O `check` renderiza: página nos viewports padrão `desktop 1440x900` e `mobile 390x844` (`index.js:183138`–`183141`); app screen também testa `tablet-1024` e `tablet-768` (`index.js:183142`–`183145`); diagrama só `desktop`; card é capturado no tamanho do card, não nos viewports (`index.js:183358`–`183362`); deck é conferido slide a slide e ganha uma folha até 12 slides (`index.js:183157`, `index.js:183677`–`183700`).

Se o HTML tem `[data-od-card]`, `--viewport` é **ignorado** e o check usa o tamanho do card (`metadata.format`, senão o aspect hint da skill, senão o layout de 1920x1080) — a própria fonte emite o aviso `viewports apply to pages without a [data-od-card]` (`index.js:183358`–`183362`).

`--json` (`runCheck2`, `index.js:195370`–`195412`): em sucesso imprime um objeto com `viewports`, `ok`, `mode` (`page`/`cards`/`deck`), `findings` (cada uma com `severity`, `check`, `message`, e às vezes `selector`, `viewport`, `row`), `images` (cada uma `{label,width,height,file}`), `omitted`, `slideCount`, `slidesChecked`, `scene3d`, `warnings`, `browserPath` e `savedRun` (`checkResultJson`, `index.js:195370`–`195372`). Em falha imprime o objeto cru `{ok:false, code, error}` e sai 1 (`index.js:195384`–`195390`).

O run é gravado em `<workspace>/.open-design/.checks/<slug-do-entry>/<run-id>/run.json`, com as imagens ao lado; cinco runs são mantidos (`index.js:180623`–`180703`). O `--screenshots <dir>` grava **JPEG** (`screenshotFileName` devolve `.jpg`) em `path.resolve(cwd, dir)`, não no workspace, e sem `--screenshots` o `check` não renderiza imagem nenhuma (`index.js:195382`, `index.js:195398`–`195405`).

`--fail-on error` retorna 1 se existir finding `severity: "error"`; `--fail-on warning` também retorna 1 para `warning` (`index.js:195408`–`195409`). Sem `--fail-on`, o exit é 0 mesmo com findings. `--viewport name:WxH` é validado por regex, nomes únicos e 1–4 viewports (`index.js:195318`–`195325`, `index.js:183187`–`183194`).

## 6. Presets, dimensões e lote

`--preset` aceita **todos** os ids de `LIST` (`index.js:174304`), não só os citados na ajuda; id desconhecido produz `Unknown format "<id>". Valid format ids: ...` (`index.js:174353`).

Tela (px): `x-image` 1600×900; `ig-square` 1080×1080; `ig-portrait` **1080×1350**; `pinterest-pin` 1000×1500; `story` **1080×1920**; `xhs-card` 1080×1440; `yt-thumbnail` 1280×720; `linkedin-image` 1200×627; `og-image` 1200×630; `x-header` 1500×500; `linkedin-banner` 1584×396; `email-header` 600×200; `banner-mrec` 300×250; `banner-leaderboard` 728×90; `banner-skyscraper` 160×600; `banner-mobile` 320×50; `shop-product` 2048×2048; `shop-banner` 1920×800; `shop-collection` 1920×600 (todas em `index.js:174305`–`174323`).

Impressão (mm): `a4` 210×297; `a3` 297×420; `a2` 420×594; `a1` 594×841; `a0` 841×1189; `a5` 148×210; `a6` 105×148; `a7` 74×105; `postcard-4x6` 101,6×152,4; `business-card` 85×55; `business-card-us` 88,9×50,8; `trading-card` 63,5×88,9; `tarot-card` 69,85×120,65; `mini-card` 44,45×63,5; `letter` 215,9×279,4; `tabloid` 279,4×431,8; `poster-18x24` 457,2×609,6; `poster-24x36` 609,6×914,4 (`index.js:174324`–`174348`). `ig-portrait` e `story` existem.

Relação entre as flags:

- `--width`/`--height` precisam vir juntos e viram a viewport explícita (16–8192) (`index.js:192389`–`192394`).
- `--selector` explícito recorta cada elemento; sem ele, `--preset` (em imagem), design fluido ou imagem de impressão usam `CARD_SELECTOR3 = "[data-od-card]"` (`index.js:192379`, `index.js:192618`). `--selector` não combina com `pdf`, `pptx` ou `--slides` (`index.js:192411`–`192412`).
- `--scale` é o `deviceScaleFactor`: a imagem do elemento sai com `box × scale`, 1–3; não combina com `--dpi` (`index.js:192394`, `index.js:192700`–`192701`, `index.js:192857`–`192858`).
- `[data-od-card]` só é redimensionado pelo preset se for fluido (`data-od-fluid`); card fixo mantém o CSS e o preset só define a viewport/layout (`index.js:178854`–`178878`, `index.js:192688`, `index.js:192593`–`192597`).
- `--preset` não combina com `--presets`, `--width`/`--height` para `--presets`; `--presets` exige 1–15 ids e design fluido (`index.js:192444`–`192448`, `index.js:192593`–`192597`).
- PDF: `--bleed` 0–20 mm, `--crop-marks`, `--dpi` 150–600 só em PNG/JPEG de formato impresso; `--print-house` define tamanho/resolução e não combina com `dpi`, `scale`, `width/height`, `presets` ou `selector` (`index.js:192395`–`192399`, `index.js:192437`).
- Lote: `--data` aceita `.csv`, `.xlsx` e `.json` (array de objetos), máximo 200 linhas (`index.js:192147`, `index.js:192203`–`192226`); `--name-field` precisa ser coluna; `--split` só faz sentido em PDF e gera um PDF por linha (`index.js:192239`–`192275`, `index.js:192959`–`192965`).

## 7. Variáveis de ambiente

A fonte só lê estas variáveis `OPEN_DESIGN_*`: `OPEN_DESIGN_BROWSER_PATH` (`index.js:177144`), `OPEN_DESIGN_FFMPEG_PATH` (`index.js:189295`), `OPEN_DESIGN_SHARE_BADGE` (`index.js:191198`) e `OPEN_DESIGN_PREVIEW_BROWSER` (`index.js:194004`). Não existem `OPEN_DESIGN_OUTPUT_DIR`, `OPEN_DESIGN_WORKSPACE_ROOT` nem `OPEN_DESIGN_DEFAULT_WORKSPACE`.

| variável | efeito |
|---|---|
| `OPEN_DESIGN_BROWSER_PATH` | executável Chromium usado por `export`, `check` e `preview`; `--browser` vence, e um caminho explícito inválido falha sem auto-detecção (`index.js:177223`–`177232`) |
| `OPEN_DESIGN_FFMPEG_PATH` | ffmpeg dos formatos `mp4`/`webm`/`gif`; `--ffmpeg` vence; não é usado por `render-video` (`index.js:189350`, `index.js:189381`) |
| `OPEN_DESIGN_SHARE_BADGE` | padrão do badge “Made with Open Design” em `standalone`/`site` (`index.js:191198`) |
| `OPEN_DESIGN_PREVIEW_BROWSER` | só no `preview`: `default` usa o navegador padrão; outro valor vira caminho (`index.js:194124`) |

Chrome: `--browser` ou `OPEN_DESIGN_BROWSER_PATH` têm prioridade; se o caminho não for executável, o erro é imediato. Sem eles, o kit procura Chrome/Edge/Chromium em caminhos do sistema, cache do Puppeteer e snaps (`index.js:177217`–`177245`).

## 8. `render-video`

O kit monta exatamente `["--yes","hyperframes","render",compositionDir,"--quality",quality??"high","--output",output]` (`index.js:195299`–`195301`) e executa `npx` (ou `npx.cmd` no Windows) com `stdio: "inherit"` e `shell` só no Windows (`index.js:195302`–`195318`). Antes, cria o diretório pai do `--output`; imprime o comando em stderr (`$ npx ...`); devolve o exit code do filho ou 1 se o `npx` não iniciar (`index.js:195303`–`195317`).

Dependências: `npx` baixa o pacote `hyperframes` (rede) e o HyperFrames precisa de FFmpeg; a descrição diz “needs FFmpeg”, mas o código do CLI não procura nem valida ffmpeg nesse caminho (`index.js:196251`, `index.js:195302`). O que a `<compositionDir>` precisa conter **a fonte não diz**: o diretório é passado intacto ao `hyperframes render`, sem validação local (`index.js:195299`–`195302`).

## 9. Rede

Em `export`/`check`, o kit sobe um servidor estático **local** e abre um Chrome headless; a página pode buscar fontes, imagens, scripts e assets 3D remotos por conta própria, mas o kit não faz telemetria nem verificação de atualização nesse caminho (`index.js:180434`–`180458`). Não encontrei `fetch` de telemetria, analytics ou update-check no bundle; o único `fetch` explícito do caminho de exportação é o de `--embed-assets` (baixa assets HTTPS declarados, timeout de 30 s) (`index.js:189908`–`189940`), e o `install` baixa o zip do plugin e seu `.sha256` (`index.js:196101`–`196103`).

Para a prova de rede (f): espere loopback (servidor local + Chrome) e possíveis conexões externas causadas pelos assets da própria página; `export` PNG/PDF sem `--embed-assets` não deve baixar assets 3D pelo kit. Não há telemetria encontrada na fonte.

## 10. Divergências plano × fonte

Plano lido em `.work/reports/plano-estudio-20261111.md:2211-2344`.

| o plano afirma | a fonte mostra | impacto |
|---|---|---|
| os scripts exportam HTML “cru” | `export`/`check` exigem `<entry>.artifact.json`; sem ele, `not-registered`, exit 1 (`index.js:192557`–`192560`) | os quatro scripts de `export`/`check` falham na primeira chamada; o de vídeo não usa sidecar e nenhum sidecar é criado por `init` |
| `OPEN_DESIGN_OUTPUT_DIR` direciona a saída | essa variável não existe na fonte; a saída vai para `<dir do entry>/exports/` (ou ao lado, no layout visível) (`index.js:192455`–`192463`) | os scripts procuram arquivos no diretório errado e concluem “nenhum PNG/PDF gerado” |
| o folder A5 de quatro cards gera PDF de 4 páginas | o caminho de impressão isola **o primeiro** `[data-od-card]`, esconde os irmãos e usa `pageRanges: "1"` (`index.js:178807`–`178830`, `index.js:179247`–`179262`) | `folder.pdf` sai com 1 página, não 4; o critério do plano reprova |
| `--viewport` define o tamanho do preflight | com `[data-od-card]`, `--viewport` é ignorado e o check usa o tamanho do card (`index.js:183358`–`183362`) | o caso `a5:1748x2480` não mede o que o plano pensa; o `card:1080x1350` também não |
| `--preset` e `--width/--height` dão a mesma assinatura | o layout da viewport é diferente (preset de card usa largura 1920; explícito usa 1080) (`index.js:192688`) | para card fixo o recorte pode coincidir, mas não está provado; para card fluido o preset muda o shape |
| `--version` responde à versão | o programa não registra `.version()` (`index.js:196211`) | `--version` é “unknown option” (já refutado na primeira execução) |
| `--bleed 0` impede margem extra | `bleed` 0 é aceito e vira bleed 0 no PDF (`index.js:192614`, `index.js:179247`–`179250`) | o plano está correto nesse ponto |
| o kit declara não ter telemetria | não encontrei telemetria/update-check no caminho de export/check | consistente; a prova de rede ainda precisa medir loopback e assets da página |

## 11. Como cada script usa o kit hoje (previsão por leitura)

| script | chamadas ao kit | erro que a fonte prevê |
|---|---|---|
| `scripts/prova-kit/export-exato.mjs` | 6 `export`: selector+width/height (`cartao`), `--preset ig-portrait`, width/height sem selector, `--preset story`, repetição e `--scale 2` | falta `fixtures/cartao.html.artifact.json` e `fixtures/story.html.artifact.json` → primeiro `export` sai 1 com `not-registered`; se o sidecar existisse, `OPEN_DESIGN_OUTPUT_DIR` é ignorado e os PNGs vão para `fixtures/exports/`, então `pngs(dir)` não acha nada |
| `scripts/prova-kit/export-pdf.mjs` | 3 `export --format pdf --preset a5/a4/a5 --bleed 0` | falta sidecar em `a5.html`, `a4.html`, `folder.html` → `not-registered`; mesmo com sidecar, os PDFs vão para `fixtures/exports/`, não para `ev`, e `garantirPdf` falha; `folder` sairia com 1 página, não 4 |
| `scripts/prova-kit/preflight-provocado.mjs` | 5 `check --viewport ... --json --fail-on error [--screenshots ...]` | falta sidecar nos cinco fixtures → `not-registered`; o JSON seria `{ok:false,code:"not-registered",...}` e exit 1 (o controle também sai 1, embora o plano espere 0); nos cards, `--viewport` é ignorado |
| `scripts/prova-kit/lote-csv.mjs` | 2 `export`: PDF `--preset a5 --bleed 0 --data --name-field nome`; PNG `--preset ig-portrait --data --name-field nome` | falta `fixtures/lote.html.artifact.json` → `not-registered`; se corrigido, a saída vai para `fixtures/exports/`, não `out/saida`; o card fixo com `width:100%` não é redimensionado pelo preset, então o PNG não sai 1080×1350; o PDF de 3 linhas sem `--split` deve sair com 3 páginas |
| `scripts/prova-kit/video-compare.mjs` | 1 `render-video <fixtures/hf-abertura> --output <abs> --quality high` | não precisa de sidecar; o risco é `npx` baixar `hyperframes` (rede) e o FFmpeg; a fonte não valida nem descreve o conteúdo da composição, então o formato de `hf-abertura` não está garantido |

## 12. O que NÃO foi verificado

- Nenhum comando do kit foi executado: exit codes, mensagens reais e conteúdo de stdout/stderr são previsão pela fonte.
- Se o HyperFrames aceita a composição `hf-abertura` (HTML/CSS/JS/PNG) e quais arquivos ele exige: a fonte não diz.
- Se um card fixo com `--preset` e com `--width/--height` produz pixels idênticos: depende do layout do navegador; não executado.
- Os códigos exatos de preflight (`overflow`, `contrast`, `image-ppi`, `safe-area`): não foram provocados nem lidos em execução.
- A existência/executabilidade de `/usr/local/bin/google-chrome-prova` e o comportamento do `npx` offline.
- Se o sidecar de exemplo passa em `writeArtifactManifest` e se o `export` atualiza `metadata.exports` sem efeitos colaterais: não executado.
- O número real de páginas do `folder.pdf` e o tamanho nominal dos PDFs: a leitura prevê 1 página e página A5 com `--bleed 0`, mas não foi medido.
- Qualquer tráfego externo real durante `export`/`check` (apenas a leitura do código foi feita).
