# R-HF-01 — composição do HyperFrames 0.9.38 e do Remotion 4.0.540 no CT

Leitura apenas; nada foi executado (nem kit, nem `hyperframes`, nem `remotion`, nem `npx`/`npm`).
Abreviações: `HF = .work/hf-src/hyperframes/package`, `R = remotion-template`,
`RR = R/node_modules/@remotion/renderer/dist`, `RC = R/node_modules/@remotion/cli/dist`,
`K = docs/prova-kit/cli-0.4.0.md`, `S = scripts/prova-kit/video-compare.mjs`.

## 1. Estrutura do pacote HyperFrames

- Versão e entrypoint: `HF/package.json:3` declara `0.9.38`; `HF/package.json:28-29` liga o binário `hyperframes` a `./bin/hyperframes.mjs`.
- `HF/bin/hyperframes.mjs:26` apenas importa `../dist/cli.js` (o bin é um launcher; a CLI real está em `dist/`).
- O subcomando `render` é definido em `HF/dist/render-GYA2H3B2.js:786-789` (`name: "render"`); os argumentos ficam logo abaixo (`:807-905`).
- Uso: o posicional é o **diretório do projeto**, não um arquivo; para um HTML específico usa-se `-c` (`HF/README.md:74-82`).
- Uma composição é um **documento HTML que define uma timeline** (`HF/dist/docs/compositions.md:3`), com um elemento raiz que tem `data-composition-id` (`:7`). O projeto precisa de `index.html` (`HF/dist/docs/troubleshooting.md:5`). Subcomposições entram por `data-composition-src` (`HF/dist/docs/compositions.md:20`).
- O diretório da fixture (`hf-abertura`) contém `index.html` + CSS/JS/PNG relativos; isso basta como “projeto”, desde que o `index.html` seja uma composição de verdade. O kit não valida o conteúdo: ele só repassa o diretório ao `hyperframes render` (`K:160-162`), que resolve o `index.html`. O sidecar `<entry>.artifact.json` é exigido por `export`/`check`, não pelo `render-video` (`K:176`, `K:193`).

## 2. Formato da composição

Atributos do elemento raiz (o seletor do runtime é `[data-composition-id]`):

| atributo | papel | fonte |
|---|---|---|
| `data-composition-id` | id único da composição; **obrigatório** | `HF/dist/docs/data-attributes.md:20`, `HF/dist/docs/compositions.md:7` |
| `data-start` | início em segundos | `HF/dist/docs/data-attributes.md:7` |
| `data-duration` | duração em segundos | `HF/dist/docs/data-attributes.md:8` |
| `data-width` / `data-height` | tamanho em px da composição | `HF/dist/docs/data-attributes.md:21-22` |
| `data-fps` | fps da raiz; sem ele o render usa 30 | `HF/dist/docs/rendering.md:17`, `HF/dist/render-GYA2H3B2.js:807-811` |

- **Duração**: a prioridade é `data-duration` declarado > duração da timeline GSAP registrada (se maior que o piso dos clipes) > maior fim entre mídias, composições aninhadas e animações CSS/WAAPI > clipes/fallback (`HF/dist/chunk-2WSLAKIR.js:4779`, funções `By`/`Gy`/`mt`; o lint resume a mesma regra em `HF/dist/chunk-TVSUPOOH.js:7961`). O número de quadros é `ceil(duração × fps)` (`HF/dist/chunk-4UQPFLJ5.js:7657-7662`).
- **FPS**: `--fps` vence; sem a flag vale `data-fps` da raiz; sem os dois, 30 (`HF/dist/docs/rendering.md:17`, `HF/dist/render-GYA2H3B2.js:807-811`).
- **Resolução**: `data-width`/`data-height` são lidos da raiz (`HF/dist/chunk-2WSLAKIR.js:4779`, `Dy`); o preflight de `--resolution` também lê esses atributos (`HF/dist/render-GYA2H3B2.js:1047-1056`). O kit não passa `--resolution` (`K:160`), então o tamanho tem de estar no HTML.
- **`--quality high`**: só escolhe o alias de qualidade/CRF (`HF/dist/chunk-XH3W57AM.js:128-134`, `:251-260`); **não** muda fps nem largura/altura (`HF/dist/render-GYA2H3B2.js:816-822`). FPS e tamanho continuam vindo de `data-fps`/`data-width`/`data-height` (ou de `--fps`/`--resolution`, que o kit não repassa).
- **Por que a execução real deu 45 quadros**: a fixture não tinha `data-duration` nem timeline GSAP; a única fonte de duração eram as animações CSS. O maior fim é `#linha`: atraso de 0,5 s + 1,0 s = **1,5 s** (`S:152-155`). `ceil(1,5 × 30) = 45`. Com `data-duration="5"` e `data-fps="30"` o mesmo HTML daria 150.

## 3. Animação determinística

- O caminho documentado é GSAP: criar a timeline com `{ paused: true }`, registrar em `window.__timelines[<data-composition-id>]` e usar posição absoluta (`HF/dist/docs/gsap.md:10-13`, `:19-21`; exemplo completo em `HF/dist/templates/blank/index.html:54-58`).
- O runtime pausa e busca a timeline por quadro com `totalTime(t, true)`/`seek(t, true)` (`HF/dist/hyperframe.runtime.iife.js:33`); o adapter GSAP do core usa `timeline.seek(targetSeconds, false)` (`HF/dist/chunk-OV3GXLBL.js:1855-1875`). Por isso a timeline precisa ser *paused* e ter duração real; não se deve deixar o relógio do `requestAnimationFrame` mandar.
- **CSS `@keyframes` funciona**: o runtime descobre `document.getAnimations()`, pausa e escreve `currentTime` por quadro (adapter WAAPI; `HF/dist/hyperframe.runtime.iife.js:43`, `HF/dist/chunk-2WSLAKIR.js:4779`). A duração inferida é o maior `endTime` dessas animações (`getInferredDurationSeconds`, mesmo bloco). Foi exatamente esse caminho que produziu os 45 quadros.
- **GSAP vem embutido?** Não no caminho de render: o template oficial carrega `https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js` (`HF/dist/templates/blank/index.html:6`, `HF/dist/docs/gsap.md:8`). O pacote até tem uma cópia em `HF/dist/vendor/npm/gsap@3.15.0/`, mas ela é servida pelo Studio; **não encontrei na fonte** um rewrite do render local para esse vendor. Sem rede, ou se vendoriza o `gsap.min.js` no diretório da composição, ou se usa CSS puro.
- Evitar `Math.random`, `Date.now`, `crypto.randomUUID` e `gsap.utils.random`: o lint avisa que cada worker reinicializa e os valores divergem entre chunks (`HF/dist/chunk-TVSUPOOH.js:5605-5612`). Para ruído, usar PRNG com seed fixa.

## 4. Composição mínima válida (1080×1920, 30 fps, 5,000 s)

Abaixo, uma composição **sem rede**: a entrada é feita com CSS e a raiz declara a duração. `data-no-timeline` faz o produtor pular o poll de 45 s por uma timeline que não existe (`HF/dist/chunk-4UQPFLJ5.js:8043-8050`; aviso em `HF/dist/chunk-TVSUPOOH.js:7628-7640`); as animações CSS continuam sendo buscadas pelo adapter WAAPI.

```html
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>abertura 5 s</title>
<style>
  html, body { margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: #0b1020; }
  #palco { position: relative; width: 1080px; height: 1920px; overflow: hidden;
           font-family: "Liberation Sans", Arial, sans-serif; color: #f6f1e8; }
  #fundo { position: absolute; inset: 0; width: 1080px; height: 1920px; object-fit: cover; }
  .cena { position: absolute; left: 96px; margin: 0; opacity: 0;
          transform: translateY(90px); animation: entra .9s ease-out both; }
  #kicker { top: 560px; font-size: 34px; letter-spacing: 6px;
            color: #c24b2a; font-weight: 700; animation-delay: .1s; }
  #titulo { top: 680px; font-size: 132px; line-height: 1.02;
            font-weight: 700; animation-duration: 1.2s; animation-delay: .3s; }
  #linha  { top: 900px; font-size: 52px; line-height: 1.2;
            color: #d8d2c6; animation-delay: .8s; }
  @keyframes entra {
    from { opacity: 0; transform: translateY(90px); }
    to   { opacity: 1; transform: translateY(0); }
  }
</style>
</head>
<body>
<!-- id obrigatório: HF/dist/docs/data-attributes.md:20; start/duration: :7-8;
     width/height: :21-22; fps da raiz: HF/dist/docs/rendering.md:17;
     data-no-timeline: HF/dist/chunk-4UQPFLJ5.js:8043-8050. -->
<div id="palco"
     data-composition-id="abertura"
     data-start="0"
     data-duration="5"
     data-width="1080"
     data-height="1920"
     data-fps="30"
     data-no-timeline>
  <img id="fundo" src="./fundo.png" alt="">
  <p id="kicker" class="cena">PROVA K.2(e)</p>
  <h1 id="titulo" class="cena">ABERTURA 5s</h1>
  <p id="linha" class="cena">HyperFrames vs Remotion</p>
</div>
</body>
</html>
```

- `fundo.png` fica ao lado do `index.html`; o render serve o diretório e resolve `./fundo.png`.
- **Quadros esperados: 150** = `ceil(5 × 30)`. A duração declarada vence a inferência (`HF/dist/chunk-2WSLAKIR.js:4779`); o fato de as animações CSS terminarem em 1,7 s não encurta o vídeo.
- Se preferir GSAP, troque o CSS por uma timeline `paused` e registre `window.__timelines["abertura"]` (`HF/dist/docs/gsap.md:10-13`); nesse caso **retire** `data-no-timeline` e carregue o `gsap.min.js` (CDN ou vendor local). Mantenha `data-duration="5"` para o render não depender da duração da timeline.

## 5. Rede e navegador do HyperFrames

- `npx` baixa o pacote `hyperframes` (rede) e o CLI exige FFmpeg (`K:162`, `HF/README.md:17`).
- O render usa Chrome headless. Sem cache, ele procura Chrome do sistema (`/usr/bin/google-chrome`, `/usr/bin/google-chrome-stable`) e só baixa `chrome-headless-shell` se não achar (`HF/dist/chunk-7IVPSA4K.js:298-299`, `:387-393`, `:400-420`, `:650-660`). O download usa `@puppeteer/browsers` (`HF/package.json:58`).
- A variável do HyperFrames é **`HYPERFRAMES_BROWSER_PATH`** (alias `PRODUCER_HEADLESS_SHELL_PATH`) (`HF/dist/chunk-WE42NVH7.js:77-78`). Caminho inexistente falha na hora (`HF/dist/chunk-7IVPSA4K.js:487-492`).
- **`OPEN_DESIGN_BROWSER_PATH` não vale para `render-video`**: o kit só monta `render <dir> --quality --output` (`K:160`), sem `--browser`; e essa variável é lida pelo kit em `export`/`check`/`preview` (`K:151`). No `dist/` do HyperFrames **não encontrei** `OPEN_DESIGN_BROWSER_PATH`. Para o CT, exporte `HYPERFRAMES_BROWSER_PATH=/usr/bin/google-chrome-stable`.
- Chrome comum não tem `HeadlessExperimental.beginFrame`; o HyperFrames avisa e cai para captura por screenshot, que funciona (`HF/dist/chunk-7IVPSA4K.js:379-381`). Se quiser o caminho otimizado, aponte para um `chrome-headless-shell`.
- A página ainda pode buscar fontes e scripts remotos: o template oficial usa o CDN do GSAP (`HF/dist/templates/blank/index.html:6`). Para o CT sem rede externa, use a composição da seção 4 (CSS puro) e fontes locais.

## 6. Remotion no CT

**(a) O que o CT precisa antes de renderizar.** O template tem `package.json` com `@remotion/cli`, `remotion`, `react` e `react-dom` fixos em 4.0.540/18.3.1 (`R/package.json:5-9`), mas **não tem `package-lock.json`** (listagem do diretório) e o CT recebe só `package.json` + `src`. Sem `node_modules`, `./node_modules/.bin/remotion` não existe — foi o erro real. É preciso `npm install --no-audit --no-fund` no diretório do template (ou copiar `node_modules` já instalado). `npm ci` não serve: exige lockfile, que não existe. O binário é exposto por `@remotion/cli` (`R/node_modules/@remotion/cli/package.json:9-13`).

**(b) Flags do `remotion render`.**

| flag | efeito | fonte |
|---|---|---|
| `--browser-executable=/usr/bin/google-chrome-stable` | usa o Chrome do sistema; não baixa Chrome | `RR/options/browser-executable.js:6`, `:11`, `:28-31`; CLI em `RC/render.js:48` |
| `--chrome-mode=chrome-for-testing` | com Chrome do sistema, usa `--headless=new`; o default é `headless-shell` | `RR/options/chrome-mode.js:5-9`, `:39`; `RR/open-browser.js:146-147`; CLI `RC/render.js:133` |
| `--concurrency=1` | um worker; reduz variação entre execuções | `RR/options/concurrency.js:6`, `:33-50`; CLI `RC/render.js:35` |
| `--gl=swangle` | backend OpenGL de software (sem GPU) | `RR/options/gl.js:6-13`, `:30`, `:45-51`; CLI `RC/render.js:102`, `:141` |
| `--image-format=png` | quadros intermediários sem perda; o default para h264 é `jpeg` | `RR/options/video-image-format.js:8`, `:53-65`; `RR/image-format.js:6-8` |
| `--props=...` | JSON de entrada; caminho resolvido a partir do `cwd` | `RR/options/props.js:5`; `RC/get-input-props.js:15-24` |

- **`--no-sandbox` não é flag do Remotion.** O launcher já acrescenta sempre `--no-sandbox` e `--disable-setuid-sandbox` (`RR/open-browser.js:149-150`); não há opção `sandbox` na lista de flags (`RC/print-help.js:77-111`). Rodar como root não exige flag extra.
- `--chrome-mode=chrome-for-testing` é o par natural de `--browser-executable`; sem ele o Remotion passa `--headless=old` (`RR/open-browser.js:146-147`), que Chrome recente pode não honrar.

**(c) Baixa Chrome em rede?** Só se `browserExecutable` for nulo. Com caminho definido, `ensureBrowser` retorna `user-defined-path` e nem checa versão (`RR/ensure-browser.js:29-31`); se o caminho não existir, falha (`:54`). Sem caminho, baixa `chrome-headless-shell` (`:41`, `RR/open-browser.js:78`), de `remotion.media`/`storage.googleapis.com` (`RR/browser/get-chrome-download-url.js:115-131`). O Chrome esperado por esta versão é 158.0.8127.2 (`RR/browser/get-chrome-download-url.js:41`).

**(d) A composição `Storyboard`.** `calculateMetadata` calcula `durationInFrames = max(1, round(props.durationS * props.fps))` e tira `fps`, `width` e `height` dos props (`R/src/Root.jsx:49-53`; defaults em `:38-48`). O `remotion-props.json` do script tem `durationS:5`, `fps:30`, `width:1080`, `height:1920` (`S:166-171`), logo **150 quadros**. `timeline.total_s` (`S:172-174`) não decide a duração do `Storyboard`: quem decide é `durationS`. O `--props` chega por arquivo JSON (`RC/get-input-props.js:19-24`) e o script passa caminho absoluto (`S:74`), então o `cwd = p.remDir` (`S:228`) não quebra o props.

## 7. Determinismo

**HyperFrames.** Fixar no HTML `data-duration="5"`, `data-fps="30"`, `data-width`/`data-height` e evitar qualquer fonte de entropia (random/Date/fontes remotas). Fixar o binário de Chrome (`HYPERFRAMES_BROWSER_PATH`) e a versão; fontes e Chrome diferentes mudam pixels (`HF/dist/docs/rendering.md:12`, `HF/dist/docs/troubleshooting.md:29`). O modo `--docker` é o único que o doc chama de determinístico (`rendering.md:10-13`), mas o kit **não** repassa `--docker` (`K:160`). O kit também não repassa `--workers`: o default é `auto` (`HF/dist/render-GYA2H3B2.js:851`), então não dá para fixar 1 worker por `render-video`; o conteúdo por quadro deve ser determinístico, mas o hash do MP4 pode variar por encoder/agendamento — medir, não presumir.

**Remotion.** `--concurrency=1`, `--image-format=png`, `--browser-executable`/`--chrome-mode` fixos e `--gl=swangle`; o template não usa `Math.random`/`Date` (varredura de `R/src/*.jsx`). O encode H.264 tende a ser determinístico para o mesmo ffmpeg/versão e os mesmos quadros; ainda assim, comparar **framemd5 dos quadros decodificados**, não o sha256 do container MP4 (metadados de mux podem variar).

## 8. O que `video-compare.mjs` faz hoje de errado

1. **Fixture sem o formato**: o `<main id="palco">` não tem `data-composition-id`, `data-width`, `data-height`, `data-duration` nem `data-fps` (`S:128-145`). O CSS fixa 1080×1920 no `#palco` (`S:146-147`), mas é a única fonte desse tamanho no fixture; isso não substitui os atributos da composição.
2. **Sem timeline e sem GSAP**: o `<script>` só chama `window.gsap` se ele já existir (`S:157-164`), e nada carrega o GSAP; `window.__timelines` nunca é registrado. As animações CSS têm fim máximo de **1,5 s** (`S:152-155`), então o runtime infere 1,5 s e `ceil(1,5×30)=45` quadros — exatamente o resultado real.
3. **Remotion sem instalação**: `cmdRem` chama `./node_modules/.bin/remotion` (`S:72-75`) com `cwd = p.remDir` (`S:228`), mas o script nunca roda `npm install`; no CT só há `package.json` + `src` (`R/package.json`, listagem), daí `No such file or directory`.
4. **Remotion sem Chrome do sistema**: faltam `--browser-executable`, `--chrome-mode`, `--concurrency`, `--gl` e `--image-format` (`S:72-75`). Sem isso, ele tenta baixar o Chrome 158 em rede e/ou usa o caminho headless antigo.
5. **HyperFrames sem browser explícito**: `envKit` só mexe em `npm_config_offline` (`S:225`); não define `HYPERFRAMES_BROWSER_PATH`. `OPEN_DESIGN_BROWSER_PATH` não chega ao `render-video` (`K:160`).
6. **Teste de determinismo falso**: o script renderiza **uma vez** e roda `framemd5` duas vezes sobre o **mesmo** MP4 (`S:236-238`); isso testa o leitor, não o render.
7. **Sem asserção de 150 quadros/5,000 s**: o `ffprobe` é gravado (`S:231-235`), mas nada compara com o esperado; 45 quadros passariam.

**Lista exata de mudanças para a lane de correção:**

1. Substituir o HTML de `S:128-145` pelo da seção 4 (ou pela variante GSAP do item 2), com a raiz `data-composition-id="abertura"`, `data-start="0"`, `data-duration="5"`, `data-width="1080"`, `data-height="1920"`, `data-fps="30"`; manter `data-no-timeline` só na variante CSS.
2. Eliminar o `abertura.js` condicional (`S:157-164`) ou trocá-lo por uma timeline GSAP `paused` registrada em `window.__timelines["abertura"]`, removendo `data-no-timeline`; se usar CDN, aceitar a dependência de rede ou vendorizar o `gsap.min.js`.
3. Em `envKit` (`S:225`), acrescentar `HYPERFRAMES_BROWSER_PATH: "/usr/bin/google-chrome-stable"` (e, se quiser o caminho otimizado, `PRODUCER_HEADLESS_SHELL_PATH`); não usar `OPEN_DESIGN_BROWSER_PATH` para isso.
4. Antes de `cmdRem`, instalar quando faltar o binário: `npm install --no-audit --no-fund` em `p.remDir` se `!existsSync(join(p.remDir, "node_modules", ".bin", "remotion"))` (acrescentar `existsSync` ao import de `node:fs`, `S:7-14`); **não** usar `npm ci` (sem lockfile).
5. Em `cmdRem` (`S:72-75`), acrescentar `--browser-executable=/usr/bin/google-chrome-stable`, `--chrome-mode=chrome-for-testing`, `--concurrency=1`, `--gl=swangle`, `--image-format=png`. **Não** acrescentar `--no-sandbox` (já é sempre passado pelo renderer).
6. Renderizar cada motor **duas vezes** em arquivos distintos (`hf.1.mp4`/`hf.2.mp4`, `remotion.1.mp4`/`remotion.2.mp4`) e gerar `framemd5` de cada arquivo; comparar os dois hashes. Não reutilizar o mesmo MP4 (`S:236-238`).
7. Após cada render, validar com `ffprobe`: `width=1080`, `height=1920`, `avg_frame_rate=30/1`, `nb_frames=150`, `duration≈5.000` (tolerância de meio quadro); falhar explicitamente se não bater.
8. Manter `--props` absoluto e `--public-dir p.public` (`S:74`), com `fundo.png` copiado antes dos renders (`S:222-223`).
9. Não tentar passar `--fps`, `--workers`, `--crf` ou `--docker` pelo `render-video`: o kit monta o argv fixo (`K:160`); o que for necessário tem de estar no HTML ou no ambiente. Se a lane quiser fixar workers, terá de chamar `npx hyperframes render` diretamente e assumir que isso deixa de medir o caminho do kit.

## 9. O que NÃO foi verificado

- Nada foi executado: exits, mensagens e conteúdo de MP4 são previsão por leitura; a única evidência de execução é a que veio no enunciado (45 quadros e o erro do binário do Remotion).
- Se `/usr/bin/google-chrome-stable` existe no CT, qual a versão, e se o Chrome do sistema funciona com `--headless=new` no Remotion 4.0.540 (o Remotion espera 158.0.8127.2; caminho de usuário pula a checagem de versão).
- Se o kit herda o env do processo ao chamar `npx` (a doc descreve `stdio: "inherit"`, mas não documenta o env); a recomendação assume herança padrão.
- Se a composição da seção 4 realmente produz 150 quadros neste build: o código prevê `ceil(5×30)`, mas não foi renderizada.
- Se `data-no-timeline` + CSS puro é aceito sem aviso no render: o produtor pula o poll (`HF/dist/chunk-4UQPFLJ5.js:8043-8050`), mas não executei o render.
- Se o `--workers auto` do HyperFrames gera MP4 byte-idêntico entre duas execuções; não foi medido.
- Se `--image-format=png` e `--gl=swangle` funcionam no CT sem bibliotecas de GPU; não executado.
- Se as fontes `Liberation Sans`/`Helvetica` estão instaladas no CT; sem isso, o Remotion e o HyperFrames podem divergir de pixels.
- Se `npm install` do template baixa só o necessário e em quanto tempo; não há lockfile para reprodutibilidade.
