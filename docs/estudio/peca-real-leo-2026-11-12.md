# Peça real Leo (feed 1080×1350 + story 1080×1920) — registro de 12/11/2026

Objetivo: provar o pipeline com uma **peça real**, não fixture: foto oficial, emblema oficial, HTML/CSS, render pelo kit em LXC descartável e os gates do Forja sobre a saída real.
Estado: **aguardando aprovação visual do dono.** Nada foi publicado, promovido a `brands/` nem enviado.

## O que foi produzido
- Mensagem (adaptação PT de `leo/guia-leo-texto.md:63`, **não** texto oficial em PT): título "Onde há necessidade, há um Leo"; corpo "Um Leo enxerga a necessidade da comunidade e serve."; CTA "Participe do Leo".
- Foto: `box-extra/G-fotos-biblioteca/_Environment/2015_03_16_California_Seal Beach_…Leos_Lions - 02.jpg` (3648×2736), recortada por `forja.photo.crop.crop_focal`. Escolhida entre 12 candidatas **abertas e vistas**: é a única com Leos (camisetas "LEO We Serve").
- Linguagem visual: tirada dos gráficos oficiais do kit Leo (`graficos-prontos`, só referência, nada copiado) e de `guia-leo-texto.md:228-232`: painel **azul claro `#407CCA`**, título branco pesado, fio amarelo, **seta amarela** (triângulo) e faixa diagonal translúcida; emblema Leo oficial inteiro sobre o azul.
- Tipografia: **Roboto** 400/700/900 (substituta digital admitida pelo guia, `guia-pt-texto.md:924-927`), `.woff2` locais (Apache-2.0). Helvetica Neue (oficial) não existe no acervo e é comercial. Hierarquia do plano (título 64, corpo 28 px @1080) nos dois formatos.
- Arquivos finais (fora do git, © Lions): `.work/peca-leo/final/` (hashes em `peca-real-leo/SHA256SUMS-final.txt`); página: `.work/peca-leo/para-ver/index.html`.

## Provas (saída do kit 0.4.0, Chrome 157, CT 920 descartável; 4 execuções, PVE sem resíduo em todas)
- `export` PNG exato: 1080×1350 e 1080×1920, sRGB, opaco. `check --fail-on warning`: 0 erros, 0 avisos nos dois. A imagem salva do `check` do story tem 882×1568 porque o kit limita a borda a 1568 px (`MAX_IMAGE_EDGE`, `index.js:183149/183203`); o layout foi checado a 1080×1920.
- PDF (RGB, 1 página): `pdffonts` mostra Roboto Black/Regular/Bold **embutidas** num CT com 0 Roboto instalada ⇒ fontes vieram dos `.woff2` locais.
- Gates do Forja sobre a saída real: `brand_lint` 0 issues; `qa_visual.inspect_artifact` ok; `media_validate` ok; **zona segura lida do `formats.json`** ok (feed 5% = 54/68 px, story 10%/15%); contraste do texto sobre o fundo sem texto ≥ 3,73:1 (regra de texto grande, ver abaixo); `photo.manifest` da foto válido; `promote_template` + `verify_template` ok **em cópia temporária** de `brands/`.
- **Controle negativo** (os gates não são vacuosos): uma versão deliberadamente ruim reprovou em 7 regras de `brand_lint`, zona segura, estouro, contraste (texto branco na foto: 1,0:1) e dimensão.
- Revisão visual: rodadas minhas em 1080 e ~360 px; a primeira versão (painel branco, título cinza) foi **refeita** por ignorar o vocabulário oficial do Leo (revisão apontou; o inventário de marca dizia que o guia pede título verde/azul e seta).
- **O gate corrigido achou um defeito real do design:** o feed tinha 56 px de margem inferior e a zona do `formats.json` exige 68 px; corrigido (72 px) e re-renderizado.

## Correções nos gates (lanes: contrato por Muse, implementação por DeepSeek, aceitação por mim)
- `qa_geometry.check_safe_zone(boxes, size, safe_zone)`: zona **assimétrica** em frações (ceil), lida do `formats.json` (`L-GATEFIX-GEOM-01`, 37 linhas, 16 testes).
- `media_validate`: reconhece **TIFF** (`L-GATEFIX-TIFF-01`, 2 linhas, 5 testes).
- `lxc-descartavel.sh`: `EXTRA_ITENS` (recusa caminho absoluto ou com `..` antes de criar o CT; 4 testes).
- Suíte inteira após integrar: 1689 testes, **179 vermelhos = contratos G0a esperados, 0 regressões**.

## Lacunas de gate que continuam (decisões, não correções)
1. `brand_lint` reconhece emblema **só por caminho** e lê tamanho **só de atributo/`style` inline**: logo renomeado ou dimensionado por classe passa sem verificação (mitigado aqui espelhando a árvore oficial e usando `width=`).
2. `brand_lint` conta acentos pelo hex **declarado**, não pelo usado; e `variants.json` não traz neutros (estão em `manifest.json`): o chamador mescla.
3. `contrast_photo.photo_contrast` mede todos os pixels da caixa, inclusive os do texto: no PNG final dá 1,0:1. Só serve com imagem de **fundo sem texto**, que nenhum passo do pipeline produz (precisa de um passo novo).
4. `check_safe_zone` mede a caixa do elemento, não o desenho visível de um PNG com margem transparente (contornado aqui com caixa recortada).
5. Nenhum gate tem CLI nem é chamado por workflow: o contrato G0a vermelho de `post`/`lote` (179 testes) os liga. As specs `L-GATES-01`/`L-POST-*` foram geradas em `.work/specs` e **não foram disparadas**.
6. `jury.score` não foi rodado (notas editoriais são humanas; o JSON de rubrica usa `weight/threshold` e `score` lê `peso/limiar`).

## Divergências do plano / decisões que são do dono
- **Contraste:** o plano (`:469`, `:563`, `:568`) exige 4,5:1 e admite 3:1 para texto grande; o kit implementa isso. Branco sobre `#407CCA` dá 4,24:1 (3,73:1 sob a faixa diagonal) e todo texto tem ≥ 28 px, então passa como texto grande — e é o que o próprio kit oficial Leo usa. `variants.json:24` pede 4,5:1 chapado (mais rígido): **divergência a decidir**.
- **Seta amarela e faixa diagonal são interpretação minha** do "arrow shape" do guia (`guia-leo-texto.md:231`): não há arquivo de seta no acervo; desenhei um triângulo simples em CSS. Aprovar ou pedir o gráfico oficial.
- **Correção do inventário de marca:** o emblema Leo `109141433` (cinza+branco) **funciona sobre o azul claro** (o branco é o contorno do desenho, como no kit oficial). O inventário dizia que só servia em fundo claro.
- **Template feito à mão**, não no Open Design (bloqueado). Divergência do plano §4.4; a promoção para `brands/leo-lions/templates/` fica para depois da sua aprovação.
- **`source` de `manifest.json` e `photos-index.json` aponta `.work/fontes/...`** (caminho local de acervo © Lions num repo público), e os scripts deste registro (`gates.py`, `build-ws.sh`) também: decidir antes de publicar.
- **Direitos da foto:** a biblioteca não traz termos de uso e tem menores identificáveis; confirmar uso (D1 afasta bloqueio de LGPD, mas é foto de terceiros).
- **Mensagem:** adaptação PT não oficial; o guia Leo só publica headlines em inglês. **Fonte:** Roboto é substituta; Helvetica Neue exigiria licença.
- Datas de fundação 07/06 e 10/10 continuam não verificadas e **não** foram usadas.

## Reproduzir
`docs/estudio/peca-real-leo/` guarda o snapshot do ferramental (template neutro, `compose.py`, `build-ws.sh`, `fase-render.sh`, `gates.py`, `copy.json`, resultado dos gates). Rodam a partir de `.work/peca-leo/` (ativos © Lions e fontes ficam lá, fora do git). Execução: `FASE_CMD='bash .work/peca-leo/fase-render.sh' EXTRA_ITENS='.work/peca-leo/ws .work/peca-leo/fase-render.sh' CHROME_NO_SANDBOX=1 bash scripts/prova-kit/lxc-descartavel.sh --run --ctid 920 --out <dir>`.
