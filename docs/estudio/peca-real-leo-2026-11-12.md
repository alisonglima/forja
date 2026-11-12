# Peça real Leo (feed 1080×1350 + story 1080×1920) — registro de 12/11/2026

Objetivo: provar o pipeline com uma **peça real**, não fixture: foto oficial, emblema oficial, HTML/CSS, render pelo kit em LXC descartável e os gates do Forja sobre a saída real.
Estado: **aguardando aprovação visual do dono.** Nada foi publicado, promovido a `brands/` nem enviado.

## O que foi produzido
- Mensagem (adaptação PT de `leo/guia-leo-texto.md:63`, **não** texto oficial em PT): título "Onde há necessidade, há um Leo"; corpo "Um Leo enxerga a necessidade da comunidade e serve."; CTA "Participe do Leo".
- Foto: `box-extra/G-fotos-biblioteca/_Environment/2015_03_16_California_Seal Beach_…Leos_Lions - 02.jpg` (3648×2736), recortada por `forja.photo.crop.crop_focal`. Escolhida entre 12 candidatas **abertas e vistas**: é a única com Leos (camisetas "LEO We Serve").
- Emblema: `logos/Emblemas_de_Leos/109141433__Logo_rgb_Leo_2C.png` inteiro, sem recorte/recolor (só a caixa esconde a margem transparente).
- Tipografia: **Roboto** 400/700/900 (substituta digital admitida pelo guia, `guia-pt-texto.md:924-927`), `.woff2` locais (Apache-2.0). Helvetica Neue (oficial) não existe no acervo e é comercial.
- Cores Leo: cinza `#55565A` (texto, 7,33:1 sobre branco), amarelo `#EBB700` (barra e sublinhado), fundo branco. Sem azul 287 (proibido como dominante no Leo).
- Arquivos finais (fora do git, © Lions): `.work/peca-leo/final/` com SHA256 em `SHA256SUMS-final.txt`; página: `.work/peca-leo/para-ver/index.html`.

## Provas (saída do kit 0.4.0, Chrome 157, CT 920 descartável, 2 execuções; PVE sem resíduo)
- `export` PNG exato: 1080×1350 e 1080×1920, sRGB, opaco. `check --fail-on warning`: 0 erros, 0 avisos nos dois.
- PDF (RGB, 1 página): `pdffonts` mostra Roboto Black/Regular/Bold **embutidas** num CT com 0 Roboto instalada (`fc-list`) ⇒ as fontes vieram dos `.woff2` locais.
- Gates do Forja sobre a saída real: `brand_lint` 0 issues; `qa_visual.inspect_artifact` ok; `media_validate` ok; zona segura (feed 54 px; story 10%/15%) ok; contraste do texto sobre o fundo 7,33:1; `photo.manifest` da foto válido; `promote_template` + `verify_template` ok **em cópia temporária** de `brands/`.
- **Controle negativo** (os gates não são vacuosos): uma versão deliberadamente ruim reprovou em 7 regras de `brand_lint` (cor fora da paleta, sombra, emblema proibido, emoji, fonte, gradiente, logo pequeno), zona segura, estouro, contraste (texto branco na foto: 1,0:1) e dimensão.
- Revisão visual: 2 rodadas minhas em 1080 e ~360 px. Corrigi defeitos de CSS que eu mesmo ditei (painel frouxo, órfão "há / um Leo" → `text-wrap: balance`).

## Lacunas encontradas nos gates (a corrigir por lane; nada foi alterado em `forja/`)
1. `brand_lint` reconhece emblema **só por caminho** (`logos/` ou nome da pasta oficial) e lê tamanho **só de atributo/`style` inline**: um logo renomeado ou dimensionado por classe passa sem verificação. Mitigado aqui espelhando a árvore oficial e usando `width=`.
2. `brand_lint` conta acentos pelo hex **declarado**, não pelo usado: um `:root` com 4 cores da paleta dá `BRAND_TOO_MANY_ACCENTS` mesmo usando 1. E `variants.json` não traz neutros (estão em `manifest.json`): o chamador tem de mesclar, senão `#FFFFFF` reprova.
3. `contrast_photo.photo_contrast` mede contra **todos** os pixels da caixa, inclusive os do próprio texto: no PNG final dá 1,0:1 (falso reprovado). Só serve com imagem de **fundo sem texto**, que nenhum passo do pipeline produz.
4. `qa_geometry.check_safe_area` só aceita margem **simétrica** (default 48): não expressa a zona do story (10% laterais, 15% vertical, `formats.json`). Feito à mão aqui. E mede a caixa do elemento, não o desenho visível de um PNG com margem transparente (falso reprovado, contornado com caixa recortada).
5. `media_validate` não reconhece **TIFF**: 3 das 12 fotos candidatas são `.tif`.
6. Nenhum desses gates tem CLI nem é chamado por workflow: o contrato G0a vermelho de `post`/`lote` (179 testes) é quem os liga.
7. `jury.score` não foi rodado: exige notas editoriais (humano) e o JSON de rubrica usa chaves diferentes das que `score` lê (`weight/threshold` × `peso/limiar`) — achado do inventário `inventario-repo-gates-peca-real.md`, não exercitado aqui.

## Divergências do plano / decisões que são do dono
- **Template feito à mão**, não no Open Design (bloqueado). Divergência do plano §4.4; a promoção para `brands/leo-lions/templates/` fica para depois da sua aprovação (a prova de promoção rodou só em cópia).
- **`source` de `manifest.json` e `photos-index.json` aponta `.work/fontes/...`** (caminho local de acervo © Lions num repo público): decidir antes de publicar.
- **Direitos da foto:** a biblioteca não traz termos de uso e tem menores identificáveis; confirmar uso (D1 afasta bloqueio de LGPD, mas é foto de terceiros).
- **Mensagem:** adaptação PT não oficial; o guia Leo só publica headlines em inglês.
- **Fonte:** Roboto é substituta; para Helvetica Neue seria preciso licenciar.
- **Emblema Leo geral só existe cinza+branco** ⇒ a peça precisa de fundo claro; fundo azul escuro exigiria versão Alpha/Ômega.
- Datas de fundação 07/06 e 10/10 continuam não verificadas e **não** foram usadas.

## Reproduzir
`docs/estudio/peca-real-leo/` guarda o snapshot do ferramental (template neutro, `compose.py`, `build-ws.sh`, `fase-render.sh`, `gates.py`, `copy.json`, resultado dos gates). Rodam a partir de `.work/peca-leo/` (ativos © Lions e fontes ficam lá, fora do git). Execução: `FASE_CMD='bash .work/peca-leo/fase-render.sh' EXTRA_ITENS='.work/peca-leo/ws .work/peca-leo/fase-render.sh' CHROME_NO_SANDBOX=1 bash scripts/prova-kit/lxc-descartavel.sh --run --ctid 920 --out <dir>` (`EXTRA_ITENS` é novo em `lxc-descartavel.sh`).
