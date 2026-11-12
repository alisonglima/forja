# Provas do kit: execução real no LXC descartável (12/11/2026)

Resultado da execução nº 5 de `scripts/prova-kit/lxc-descartavel.sh --run --ctid 920` no PVE (`root@192.168.88.32`), CT 920 **criado e destruído nesta execução** (marcador `forja-prova-kit-920-…` + hostname conferidos antes do destroy; o CT 219, referência com perfil Google logado, nunca foi destino). Início 10:08:07Z, fim 10:15:10Z (UTC). Depois: `pct status 920` inexistente, `/tmp` do PVE sem sobras, 15 CTs preservados.

Evidência: `docs/prova-kit/evidencias-execucao-2026-11-12.tar.gz` (sha256 `ae9de21b2bb632b532eeebb44825288af989b986a27d8fe9a3669696abeb0f19`, idêntico no CT e no Mac). Extrair em `.work/prova-kit/` e rodar `FORJA_PROVA_KIT=1 python3 -m pytest tests/prova_kit` (146 passam; o único vermelho é `test_aprovacao_visual`, que é humano).

Ambiente medido: Debian 12 (template local), Chrome 157.0.8103.78, Node 22.23.5, kit `@feimacode/open-design-agent-kit@0.4.0`, HyperFrames 0.9.38, Remotion 4.0.540, `CHROME_NO_SANDBOX=1`.

## O que cada prova mediu

| prova | resultado medido |
|---|---|
| p5-01 dimensões | PNG 1080×1350 (selector, preset `ig-portrait`, width/height), story 1080×1920, `--scale 2` = 2160×2700; repetições com o mesmo hash |
| p5-02 PDF | `a5` 419,528×595,276 pt (148×210 mm), `a4` A4 exato, **folder = 4 páginas** (modo página); 2 fontes embutidas em cada |
| p5-03 preflight | controle exit 0; `overflow`, `image-ppi`/`bleed-size`, `contrast`, `safe-area` exit 1 (`--fail-on warning`) |
| p5-04 lote CSV | 3 linhas → 3 PNG + PDF de 3 páginas A5; nome com acento tratado (`lote-joao-conceicao.png`) |
| p5-05 vídeo | HyperFrames e Remotion: 1080×1920, 30 fps, **150 quadros, 5,000 s**; `framemd5` idêntico nas duas repetições de cada motor; SSIM 0,915 |
| p5-06 rede | 0 bytes originados pelo CT durante `check`; só broadcast de vizinhos da LAN, separado em `ruido-lan.txt` |

## O que o plano afirmava e a fonte/medição desmentiram

1. O kit só opera **artefato registrado** (`<entry>.artifact.json`) **dentro do workspace**; saída em `<dir do entry>/exports/`; `OPEN_DESIGN_OUTPUT_DIR` e `OPEN_DESIGN_WORKSPACE_ROOT` não existem; sem `--version` (`docs/prova-kit/cli-0.4.0.md`).
2. Com `--preset a5` o kit imprime **só o primeiro** `[data-od-card]`: folder de N páginas = **modo página** sem preset (`cli-0.4.0-multipagina.md`).
3. `--viewport` é ignorado em card; contraste e safe-area são **warning** (use `--fail-on warning`).
4. HyperFrames exige `data-composition-id/-duration/-width/-height/-fps` na raiz; sem eles a duração sai da animação CSS (1,5 s, 45 quadros). Chrome do sistema via `HYPERFRAMES_BROWSER_PATH`, **não** `OPEN_DESIGN_BROWSER_PATH` (`video-0.9.38.md`).
5. Remotion no CT: `npm install` no template + `--browser-executable`, `--chrome-mode=chrome-for-testing`, `--concurrency=1`, `--gl=swangle`, `--image-format=png`.

## Defeitos do próprio ciclo (execuções 1 a 4), todos corrigidos

- O wrapper "offline" bloqueava `127.0.0.1`: **toda** prova renderizou "This site can't be reached" e as provas 03/04 saíam com exit 0 sobre a página de erro. Correção: `EXCLUDE 127.0.0.1` + checagem de sanidade na base (loopback sim, internet não), gravada em `chrome-loopback.txt`/`chrome-externo.txt`.
- Fase que falhava destruía o CT sem trazer evidência. Agora traz o tarball antes do `trap`.
- Faltava o pacote `time`; `tcpdump -nrt arq` lia o arquivo errado (certo: `-n -t -r arq`); `--version` não existe no kit.
- Lição: **exit 0 não prova nada, abra a imagem.**

## Não verificado / pendente

- **Aprovação visual K.4 é humana** (`test_aprovacao_visual`): as imagens e PDFs estão na evidência, sem veredito.
- Uma única execução bem-sucedida (determinismo entre execuções do CT não medido; o `framemd5` repetido é do mesmo build na mesma execução).
- `--no-sandbox` do Chrome ligado só por `CHROME_NO_SANDBOX=1` (CT descartável); não vale para uso fora dele.
- SSIM mínimo não fixado pelo plano (valida só `(0,1]`).
