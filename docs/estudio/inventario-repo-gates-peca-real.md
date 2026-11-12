# Inventário do repo para a peça real Leo/Lions

Base: `dc2c4bdce1cbe2b2479b983b27f74784a3587683`. Lane só de leitura: nada foi executado além de `pytest`, `git`, inspeção local e da criação deste arquivo; kit, OD, Chrome, `ssh`, `scp`, `curl`, `npm` e rede não foram usados. O acervo oficial fica em `.work/fontes/lions/`; este worktree não tem `.work/fontes` (só o checkout principal tem).

## 1. Contratos G0a vermelhos relevantes

Comando rodado uma vez, sem `FORJA_PROVA_KIT`:

```bash
python3 -m pytest -q -p no:cacheprovider 2>&1 | grep -E '^FAILED' | cut -c1-150
```

Resultado: **179 linhas `FAILED`** (o pipeline retorna 0 porque o `grep` encontrou linhas; o pytest em si não foi usado como gate). Grupos que interessam a esta peça:

- **post (14/14 vermelhos)** — `tests/test_post_workflow.py`. Testes: `test_orquestrador_steps_factory_ordem_e_onze_passos`, `test_brief_run_brief_feliz_escreve_brief_json`, `test_brief_run_brief_incompleto_falha`, `test_brief_run_brief_ausente_falha_config`, `test_content_run_research_sem_fonte_falha`, `test_content_run_copy_feliz_mede_limites`, `test_compose_run_template_hash_divergente_falha`, `test_compose_run_compose_formato_fora_da_matriz_falha`, `test_compose_run_compose_asset_ausente_e_traversal_falha`, `test_kit_run_render_feliz_usa_run_injetavel`, `test_kit_run_lint_gate_reprovado_falha`, `test_inspect_run_inspect_contraste_e_dedup_falham`, `test_deliver_run_deliver_stale_falha`, `test_deliver_run_deliver_pacote_incompleto_falha`. Exige os NOVOS `forja/workflows/post.py` (`tests/test_post_workflow.py:22`), `post_brief.py` (`:30,37,44`), `post_content.py` (`:50,56`), `post_compose.py` (`:64,73,81`), `post_kit.py` (`:89,99`), `post_inspect.py` (`:106`) e `post_deliver.py` (`:115,124`). Julga a ordem dos 11 passos e `FILES` (`:24,27`), brief normalizado e `BRIEF_INCOMPLETE` (`:32-40`), fonte obrigatória no research (`:52`), hash de template (`:67-69`), formato fora da matriz (`:76-77`), asset ausente/traversal (`:84-86`), render com `run=` injetável (`:94-95`), lint reprovado (`:102`), contraste/dedup (`:110-111`), aprovação vencida (`:119-120`) e pacote incompleto (`:126-127`).
- **lote-digital (15/15 vermelhos)** — `tests/test_lote_workflow.py`. Testes: `test_orquestrador_ordena_os_8_passos`, `test_validate_converte_acentos_quebra_e_slug`, `test_validate_limite_200_linhas_e_400_arquivos`, `test_validate_colisao_de_slug_da_name_collision`, `test_validate_formato_fora_da_matriz`, `test_validate_entrada_ausente_e_vazia`, `test_validate_hostil_ponto_ponto_e_json_truncado`, `test_render_caminho_feliz_com_kit_injetado`, `test_render_sem_pre_requisito_e_provedor_falha`, `test_sample_amostra_deterministica_e_happy`, `test_sample_contraste_baixo_reprova`, `test_sample_arte_duplicada_reprova`, `test_sample_qr_longo_demais_reprova`, `test_deliver_pacote_zip_indice`, `test_deliver_aprovacao_vencida_bloqueia`. Exige `forja/workflows/lote_digital.py` (`tests/test_lote_workflow.py:16`), `lote_validate.py` (`:21,28,37,43,49,57`), `lote_render.py` (`:64,70`), `lote_sample.py` (`:79,86,94,101`) e `lote_deliver.py` (`:109,116`). Julga os 8 passos e `FILES` (`:18-19`), acentos/quebra/slug (`:23-25`), 200 linhas e 400 arquivos (`:29-31`), `NAME_COLLISION` (`:38-40`), `FORMAT_UNSUPPORTED` (`:44-46`), entrada hostil (`:58-62`), `MISSING_PREREQ`/`PROVIDER_ERROR` (`:73-77`), amostra determinística (`:82-83`), contraste (`:89-90`), dedup (`:97-98`) e QR >2000 (`:102-105`).
- **template/compose** — `forja/templates.py` está verde (`tests/test_templates.py` e `tests/test_promote_cli.py` não aparecem em `FAILED`). O vermelho de compose é o passo `post_compose.py` acima; `tests/test_compose.py` é verde, mas trata do `compose.yaml` do Docker, não do passo HTML.
- **render/lint/inspect** — os três são passos do `post` (`post_kit.run_render`, `post_kit.run_lint`, `post_inspect.run_inspect`, `tests/test_post_workflow.py:88-111`). Não há gate de render fora do workflow; `forja/kit.py` é o wrapper do kit/Chrome e existe.
- **deliver** — `post_deliver.py` (`tests/test_post_workflow.py:115,124`) e o CLI `forja deliver` (`tests/test_cli_deliver.py`, 9/9 vermelhos: `test_deliver_help_expoe_flags`, `test_deliver_by_vazio_e_uso_exit_2`, `test_deliver_sem_confirm_nao_grava`, `test_deliver_hash_alterado_e_stale_sem_transicao`, `test_deliver_aprovado_para_entregue_grava_estado_e_evento`, `test_deliver_entregue_e_idempotente`, `test_deliver_sem_aprovacao_e_gate_failed`, `test_deliver_estado_invalido_falha_fechado`, `test_deliver_pacote_falho_e_asset_missing`). O CLI atual só declara `approve`, `init`, `describe`, `status`, `doctor`, `providers`, `transcribe`, `check`, `schedule`, `mix`, `render`, `run`, `frames`, `voices`, `qa` e `mcp` (`forja/cli.py:88-125`); `deliver` não existe.
- **brand** — `tests/test_assets_index.py`, 13/13 vermelhos, exige o NOVO `brands/leo-lions/assets-index.json` (`tests/test_assets_index.py:15`), ausente no worktree. Testes: `test_top_level_schema_and_roots`, `test_assets_list_has_at_least_emblems_and_decks`, `test_asset_ids_are_unique`, `test_each_asset_has_required_fields_with_exact_types`, `test_each_asset_declares_a_known_variant`, `test_asset_paths_are_relative_and_stay_inside_root`, `test_index_has_no_embedded_binary`, `test_photos_library_is_not_duplicated_here`, `test_seven_emblems_present_with_expected_variant`, `test_emblem_filenames_match_official_sources`, `test_four_decks_with_template_id_and_variants`, `test_three_extra_decks_are_marked_optional`, `test_base_deck_pins_official_file_hash_and_bytes`. Julga `schema: forja-brand-assets/v1`, `root_env: FORJA_BRAND_SOURCES`, `root_default: .work/fontes/lions`, 11+ ativos, 7 emblemas com `variant`, 4 decks com `template_id`, 3 decks `optional`, sha256/bytes do deck base, caminhos relativos e nenhum binário embutido (`:42-120`). `tests/test_brand_lint.py`, `test_brand_manifest.py` e `test_brand_variants.py` não aparecem em `FAILED`.
- **jury** — nenhum teste de júri em `FAILED`: `tests/test_jury.py` e `tests/test_jury_data.py` estão verdes. Não há contrato vermelho de júri nesta base.
- **gates/CLI/MCP adjacentes** — `tests/test_human_gates.py` (12/12) exige `forja/workflows/human_gates.py` (`:14,33`); `tests/test_cli_workflows.py` (6/6) exige o registro de `post`/`lote-digital` em `forja/workflows/__init__.py` e no `describe`/`init`/`run`; `tests/test_mcp_tools.py` (27/27) exige 6 tools novas em `forja/mcp.py` (`forja_post_plan`, `forja_post_render`, `forja_post_inspect`, `forja_lote_validate`, `forja_lote_render`, `forja_package`).
- **outros vermelhos, fora do escopo direto** — `test_slides_workflow.py` 10 (exige `forja/workflows/slides.py`), `test_cli_slides.py` 6, `test_video_broll.py`+`test_video_broll_timeline.py` 21 (exige `forja/broll.py` com validação e timeline), `test_remotion_contract.py`+`test_remotion_root.py`+`test_remotion_theme.py` 20 (exige `remotion-template/src/VerticalBrand.jsx`, `remotion-template/src/Root.jsx` e o tema), `test_pptx_content.py` 8 (exige `brands/leo-lions/decks/modelos.json`/`modelo.yaml`), `test_memoria.py` 11 (exige `forja/memoria.py`) e `test_packaging.py` 7 (exige `packages.find include=["forja*"]` e `package-data` no `pyproject.toml`).

## 2. Gates existentes: assinatura, alcance e CLI

Nenhum dos módulos abaixo tem `add_parser` próprio em `forja/cli.py` (o único `add_parser` é o helper interno de `forja/cli.py:86`). Também não há chamada interna a eles em `forja/` ou `forja/workflows/` (busca por `lint_brand(`, `validate_media(`, `build_package(`, `build_assets(`, `verify_template(` etc. só encontra o wrapper `scripts/od/promote_template.py:55`). Ou seja, são biblioteca pronta, mas **não ligada** ao `run`/CLI.

| módulo | assinatura pública (linha) | o que lê/valida | erro | CLI? | Chrome? |
|---|---|---|---|---|---|
| `forja/brand_lint.py` | `lint_brand(html, tokens, variant, fonts=None, logos=None, rules=None) -> list[dict]` (`:191`) | string HTML/CSS; paleta da variante, fontes, emblemas, emoji, gradiente, nº de acentos, sombra, `background-image` | lista `{level,code,msg,...}`; `ForjaError` `CONFIG_INVALID`/`BRAND_VARIANT_REQUIRED` (`:71-79`) | não | não |
| `forja/qa_geometry.py` | `measure(path) -> dict|None` (`:22`); `check_safe_area(boxes,size,safe_margin=48)` (`:54`); `check_overflow(boxes,size)` (`:67`) | PNG por IHDR (não abre Pillow); largura/altura/bytes/sha256; caixas contra margem fixa | lista `{level,id,code,msg}`; `None` se ilegível | não | não |
| `forja/qa_visual.py` | `inspect_artifact(path, expected, *, brand_id="", hashes=None, contrast=None, now=None)` (`:87`); `inspect_lote(pieces, *, brand_id="", hashes=None, contrast=None, now=None)` (`:128`) | PNG via `qa_geometry.measure`; dimensão exata, dedup de 30 dias e razões de contraste **já medidas pelo chamador** | dict `{ok,issues,width,height,sha256}`; issues `GATE_FAILED`/`FORMAT_UNSUPPORTED`/`DUPLICATE_ARTIFACT`/`CONTRAST_PHOTO` | não | não |
| `forja/contrast_photo.py` | `photo_contrast(image, box, text_color, min_ratio=4.5, sample_step=2)` (`:94`); `check_photo_contrast(...)` (`:120`); `video_frame(path, at_s, run=subprocess.run)` (`:155`) | ndarray HxWx3/4; contraste sRGB pixel a pixel na caixa; frame de vídeo via `ffmpeg` | dict `{min,p5,mean,pass}`; lista `CONTRAST_PHOTO`; `ForjaError` `USAGE`/`MISSING_PREREQ`/`PROVIDER_ERROR` | não | não (ffmpeg) |
| `forja/photo/crop.py` | `crop_focal(img, focal, target, *, resample=None) -> Image` (`:18`) | PIL Image; recorte 4:5/9:16 por ponto focal, sem ampliar | `ForjaError` `USAGE` | não | não |
| `forja/photo/color.py` | `apply_cube(img, lut_path, strength=1.0) -> Image` (`:151`) | PIL/numpy; LUT `.cube` 3D | `ForjaError` `USAGE`/`MISSING_INPUT` | não | não |
| `forja/photo/detail.py` | `denoise_sharpen(img, *, denoise=3, sharpen=0.6) -> Image` (`:38`) | PIL RGB; mediana + unsharp | `ForjaError` `MISSING_INPUT` | não | não |
| `forja/photo/duotone.py` | `duotone(img,dark,light)` (`:20`); `blend(img,overlay,alpha=0.5)` (`:37`) | PIL; luminância para duotone e mistura | `ForjaError` `USAGE` | não | não |
| `forja/photo/manifest.py` | `build_manifest(*, input_sha256, output_sha256, steps, brand_id, origin, license, ai_elements, **provenance)` (`:35`); `verify_manifest(data)` (`:64`) | dict; hashes, passos, marca, origem, licença, elementos IA | lista `{level,code,msg}` (`MANIFEST_*`) | não | não |
| `forja/formats.py` | `load_formats(path=None)` (`:71`); `get(ident)` (`:83`); `constantes(ident)` (`:90`); `require_verified(ident,campo)` (`:94`); `stale_rows(data,on=None,days=90)` (`:103`); `stale(days=90)` (`:117`) | `forja/data/formats.json`; valida campos, `safe_zone`, fonte, status, data | dict/lista `FORMAT_UNVERIFIED`/`FORMAT_STALE`; `ForjaError` `CONFIG_INVALID`/`FORMAT_UNSUPPORTED` | não | não |
| `forja/media_validate.py` | `validate_media(path, spec) -> list[dict]` (`:97`) | magic bytes PNG/JPEG/GIF/WebP/MP4/MOV/AVI/FLV; dimensões via Pillow (still) ou `probe.probe_video`; bytes, pixels, razão | lista `MEDIA_*`; `ForjaError` `CONFIG_INVALID` | não | não |
| `forja/templates.py` | `promote_template(src,brand,piece,*,approve_hash,approved_by,od_project,od_artifact,design_system,preset,now,force=False)` (`:107`); `verify_template(brand,piece)` (`:146`) | HTML; `data-variant`, hex cru, hash, manifesto | `ForjaError` `TEMPLATE_HASH_MISMATCH`/`MISSING_PREREQ`/`CONFIG_INVALID`/`APPROVAL_STALE` | só `scripts/od/promote_template.py` | não |
| `forja/jury.py` | `score(piece, rubric, measured, editorial, *, passes=1)` (`:70`) | dicts; 5 critérios, pesos, mínimo, limiar, veredito | dict `{medido,editorial,total,bloqueios,veredito}` | não | não |
| `forja/delivery.py` | `build_package(root,*,brief,brand_root,formats,approvals,now=None)` (`:148`) | JSON/brief/manifesto/arte; hash aprovado, alt, hashtags, elementos IA | dict manifesto; `ForjaError` `BRIEF_INCOMPLETE`/`APPROVAL_STALE`/`FORMAT_UNSUPPORTED`/`MISSING_INPUT` | não (`forja deliver` é contrato vermelho) | não |
| `forja/assets.py` | `build_assets(root, variants=None)` (`:120`) | `incoming/manifest.json`, arquivo/hash/bytes/licença/origem/variante; copia para `work/assets/` | dict `{schema,assets}`; `ForjaError` `ASSET_MISSING`/`ASSET_HASH_MISMATCH`/`CONFIG_INVALID` | não | não |

**Quem lê o quê.** PNG: `qa_geometry`, `qa_visual` e `media_validate`; HTML: `brand_lint` (string) e `templates` (arquivo); `contrast_photo` lê pixels já decodificados e vídeo; `photo/*` trabalha com PIL/numpy; `formats`, `jury`, `delivery` e `assets` leem JSON/arquivos, não imagem. **Nenhum desses módulos precisa de navegador/Chrome.** O Chrome aparece só no caminho de render: `forja/kit.py` monta `npx --yes @feimacode/open-design-agent-kit@<versao> check|export` (`forja/kit.py:88-90,126-160`), que é o único ponto dependente de Node/Chrome.

**Lacunas e fragilidades que a leitura revela:**

- **Gate órfão.** Não há CLI nem chamada no `post`/`lote` para `brand_lint`, `qa_geometry`, `qa_visual`, `contrast_photo`, `media_validate`, `delivery`, `assets` e `jury`; só `templates` tem wrapper. O contrato vermelho do `post`/`lote` é que vai ligar isso.
- **PNG-only.** `qa_geometry.measure` exige assinatura PNG e IHDR (`:14-35`); `qa_visual.inspect_artifact` reprova qualquer coisa que não seja PNG exato (`:95-111`), embora o plano aceite PNG/PDF e o `render` possa gerar PDF (`plano:425,433`). JPEG/TIFF não passam.
- **Zona segura fixa.** `qa_geometry.SAFE_MARGIN = 48` (`:12`) ignora `forja/data/formats.json`: o story tem `top/bottom 0.15` e `left/right 0.10` (`formats.json:9`), isto é, 288 px/108 px em 1080x1920, muito acima de 48 px. Não há leitura de `safe_zone` no gate.
- **Contraste não medido.** `qa_visual` só aceita `contrast` pronto (`:87-94,122`); quem mede é `contrast_photo`, que não é chamado por ninguém e não tem CLI. `contrast_photo` depende de `numpy` (declarado em `pyproject.toml:28`) e de `ffmpeg` para vídeo (não declarado no `pyproject.toml`).
- **TIFF fora do magic bytes.** `media_validate._IMAGE_PREFIXES` cobre PNG/JPEG/GIF/WebP (`:24-29`); TIFF/BMP não são reconhecidos. Três das 12 fotos candidatas são `.tif` (linhas 68, 126, 158 do índice) e cairiam em `MEDIA_FORMAT` antes de qualquer conversão.
- **Lint de marca estreito.** `brand_lint` só reconhece hex de 6 dígitos (`:11`), não `#RGB`/`#RRGGBBAA`; só inspeciona `<img>` (`:127-168`), não `background-image`/CSS; o mínimo de logo é `24` px admitidamente conservador (`:21`); `background-image` é apenas `warning` (`:181-189`).
- **Template não valida o card.** `templates._check_html` só exige `data-variant` e nenhum hex de 6 dígitos (`:41-51`); não exige `[data-od-card]`, `[data-od-field]`, fonte local, zero CDN/emoji nem tokens `var(--...)`. O regex de `data-variant` pode casar dentro de comentário/JS, e hex de 3/8 dígitos passa.
- **Júri desalinhado do dado.** `jury.score` lê `criterios[].peso`, `limiar` e `minimo` (`:25-36,78-79`); `forja/data/rubrica.json` usa `criteria[].weight`, `threshold` e `min_criterion` (`rubrica.json:1-10`). Passar o JSON empacotado direto em `score` resulta em "rubrica sem criterios" e bloqueio; a integração não é testada.
- **Entrega sem dimensão/contraste.** `delivery.build_package` valida alt/hashtags contra a linha de formato (`:172-180`), mas não valida `max_chars`, dimensão, contraste nem safe area da arte; delega isso ao `inspect` (que ainda não está ligado).
- **Dependências não declaradas.** `forja/media_validate.py:12` e `forja/photo/crop.py:9` importam `PIL`, mas `pyproject.toml:28` não lista Pillow (ele chega via `python-pptx`); `pyproject.toml:44` fixa `packages = ["forja", "forja.workflows"]`, excluindo `forja.photo`, `forja.data` e `forja.schemas` do wheel (é o que `tests/test_packaging.py` cobra).
- **Assets não resolve o acervo.** `assets.build_assets` só aceita `incoming/` (`:59-72`), copia para `work/assets/<basename>` (`:152-153`) e grava `path` relativo ao projeto (`:159`). Não lê `.work/fontes`, não lê `assets-index.json` e não há leitor de `FORJA_BRAND_SOURCES` no repo (busca sem resultados).

## 3. Formatos

`forja/data/formats.json` tem `schema_version: 1`, `atualizado_em: 2026-11-11` (`:1-3`) e **20 linhas de formato** (`:5-24`). Números exatos:

| id | linha | largura x altura | razão | safe_zone (top/bottom/left/right) | limite | texto |
|---|---|---|---|---|---|---|
| `ig-feed-quadrado` | `formats.json:5` | 1080x1080 | 1:1 | 0.05/0.05/0.05/0.05 | 8.388.608 B | 2200 chars, 5 hashtags, alt 100 |
| `ig-feed-4x5` | `formats.json:6` | **1080x1350** | 4:5 | 0.05/0.05/0.05/0.05 | 8.388.608 B | 2200 chars, 5 hashtags, alt 100 |
| `ig-story` | `formats.json:9` | **1080x1920** | 9:16 | **0.15/0.15/0.10/0.10** | 104.857.600 B, 60 s | 2200 chars, 5 hashtags, alt 100 (plataforma null) |
| `ig-reels` | `formats.json:10` | 1080x1920 | 9:16 | 0.15/0.15/0.10/0.10 | 314.572.800 B, 900 s | 2200, 5, 100 |

No story, `0.15 x 1920 = 288 px` no topo e na base; `0.10 x 1080 = 108 px` nas laterais. `alt_max_plataforma` é `null` e `alt_max` é 100 (regra da casa). `status` é `provisorio` e `verificacao` é `DIVERGENTE` nas duas linhas de feed e no story (`formats.json:6,9`); a divergência registrada é 3:4 x 4:5 e hashtags 30 (API) x 5 (ajuda) (`formats.json:6,9`). O `load_formats` força `status: provisorio` e zera `constantes` quando `verificacao != VERIFICADO` (`forja/formats.py:66-68`).

## 4. Foto: 12 candidatas

Todas as 145 fotos de `brands/leo-lions/photos-index.json` têm `tem_pessoas: null` e `revisado_por: null` (contagem no arquivo: 145/145). Nenhuma foi aberta nesta lane; a escolha abaixo é só técnica (orientação, lado curto ≥ 2700 px, variedade de `causa`) e não opina sobre conteúdo. Não há foto quadrada no índice (130 paisagem, 15 retrato).

| # | linha | caminho relativo (sob `box-extra/G-fotos-biblioteca/`) | causa | dimensões | orientação | `tem_pessoas`/`revisado_por` |
|---|---|---|---|---|---|---|
| 1 | 20 | `_Cancer/20180522_rw_Childhood_Cancer_-188.jpg` | `_Cancer` | 4480x5706 | retrato | `null`/`null` |
| 2 | 27 | `_Cancer/20180522_rw_Childhood_Cancer_-46.jpg` | `_Cancer` | 4480x6720 | retrato | `null`/`null` |
| 3 | 32 | `_Diabetes/20180517_rw_diabetes_walk_-109.jpg` | `_Diabetes` | 6720x4480 | paisagem (recorte 4:5) | `null`/`null` |
| 4 | 53 | `_Disaster/IMG_0169.JPG` | `_Disaster` | 4368x2912 | paisagem (recorte 4:5) | `null`/`null` |
| 5 | 68 | `_Education/YTH_Philippines_001.tif` | `_Education` | 3000x4500 | retrato | `null`/`null` |
| 6 | 72 | `_Environment/2015_03_16_California_Seal Beach_Clean up_Service Project_Leos_Lions - 02.jpg` | `_Environment` | 3648x2736 | paisagem (recorte 4:5) | `null`/`null` |
| 7 | 94 | `_Food/cheese-dinner-food-41194.jpg` | `_Food` | 3744x5616 | retrato | `null`/`null` |
| 8 | 101 | `_Hunger/20180522_rw_Hunger_Pantry_-115.jpg` | `_Hunger` | 6720x4480 | paisagem (recorte 4:5) | `null`/`null` |
| 9 | 121 | `_Vision/20160829_155444.jpg` | `_Vision` | 4536x8064 | retrato | `null`/`null` |
| 10 | 126 | `_Vision/Africa_Vision Screening_Children003.tif` | `_Vision` | 3492x5010 | retrato | `null`/`null` |
| 11 | 144 | `_Youth_Activities/CampPacifica_PhotoCredit_BransonTarr_215.jpg` | `_Youth_Activities` | 5760x3840 | paisagem (recorte 4:5) | `null`/`null` |
| 12 | 158 | `_Youth_Activities/YTH_Norway_001.tif` | `_Youth_Activities` | 3000x4500 | retrato | `null`/`null` |

As paisagens têm razão 1,5 ou 1,33 e permitem recorte 4:5 (a largura do recorte é `0,8 x altura`, sempre menor que a largura original). As `.tif` (linhas 68, 126, 158) são o caso do §2: `media_validate` não reconhece TIFF e a conversão para PNG/JPEG teria de ser feita fora do repo, sem copiar o original.

## 5. Caminhos e `.gitignore`

O repo é público (MIT) e `.work/` é ignorado:

```text
$ git check-ignore -v .work/fontes/lions/README.md
.gitignore:11:.work/	.work/fontes/lions/README.md
```

O `.gitignore:11` tem `.work/`; o acervo inteiro fica fora do git. `git grep -n "\.work/fontes"` encontra **11 linhas rastreadas**:

- `brands/leo-lions/manifest.json:37` — `typography.source` aponta para `.work/fontes/lions/guia-de-marca/leo/tokens-submarcas.json`.
- `brands/leo-lions/manifest.json:40-44` — `source.variants`, `.neutrals`, `.brand`, `.brand_en` e `.index` repetem caminhos `.work/fontes`; a linha 45 é `.work/reports/plano...` (também caminho local, mas não casa com este `grep`).
- `brands/leo-lions/photos-index.json:4` — `"source_root": ".work/fontes/lions"`.
- `tests/test_assets_index.py:4,47` e `tests/test_pptx_content.py:53-54` — os contratos citam o mesmo default.

Ou seja, os **dados rastreados não embutem o acervo** (só hashes, dimensões e caminhos relativos), mas **expõem o caminho local** `.work/fontes/lions` em `manifest.json` e `photos-index.json`. Não há leitor de `FORJA_BRAND_SOURCES` no repo (`grep` sem resultados); o contrato vermelho `assets-index.json` prevê `root_env`/`root_default` (`tests/test_assets_index.py:45-47`), mas o arquivo não existe.

**Como um template rastreado referencia logo/foto/fonte sem embutir.** Hoje, a única resolução implementada é `forja/assets.py`: ele lê `incoming/manifest.json`, exige que o arquivo esteja dentro de `incoming/` (`:59-72`), valida licença/origem/hash/bytes (`:131-147`), copia para `work/assets/<basename>` (`:152-153`), grava `work/assets.json` com `path: work/assets/<nome>` relativo ao projeto (`:159,164-166`). O compose (quando existir) usa esse `assets.json`; o template pode então referenciar o caminho relativo do projeto (`work/assets/...`), sem bytes no repo e sem caminho absoluto. **Isso não resolve o acervo oficial**: `assets.py` não lê `.work/fontes`, não copia logo/fonte do guia e não tem placeholder de asset; e, ao achatar o logo para `work/assets/<nome>`, ele perde o prefixo `logos/...` que `brand_lint._image_issues` usa para reconhecer o emblema (`brand_lint.py:149-168`). O `templates.py` também não tem noção de asset: só valida `data-variant` e hex. Portanto, para a peça real, a referência a logo/foto/fonte do acervo **ainda não tem caminho implementado**; o máximo que existe é o `work/assets/` do `assets.py` para material já ingerido em `incoming/`.

## 6. `templates.py` / `promote_template`

Checagens de `promote_template` (`forja/templates.py:107-144`):

1. `piece` precisa ser texto não vazio e casar `[a-z0-9][a-z0-9-]*` (`:19,53-59`); `../fora` é recusado.
2. `src` é resolvido; se qualquer parte for `node_modules`, `.od-skills` ou `.cache`, recusa (`:18,68-70`); se não for arquivo, `MISSING_INPUT` (`:71-73`).
3. O HTML é lido como UTF-8; ilegível vira `CONFIG_INVALID` (`:34-39`).
4. Exige `data-variant` não vazio (`:21,43-46`). Regex aceita aspas simples ou duplas.
5. Recusa qualquer hex de 6 dígitos (`#RRGGBB`) no HTML; a mensagem manda usar `var(--...)` (`:20,47-51`).
6. `approve_hash` tem de ser igual ao sha256 do `src`; senão `TEMPLATE_HASH_MISMATCH` (`:114-118`).
7. O destino é sempre `brands/<id>/templates/<piece>.html`; o `resolve()` do pai tem de ficar dentro de `templates/` (`:119-126`).
8. Se o destino existe e `force=False`, `APPROVAL_STALE` ("use --force com novo --approve-hash") (`:127-130`).
9. Os metadados `approved_by`, `approved_at`, `od_project`, `od_artifact`, `design_system` e `preset` têm de ser texto não vazio (`:94-101`).
10. O manifesto é lido se existir; ausente vira default `{schema:1, brand, variants:[lions,leo,leo-lion], templates:{}}`; inválido ou sem `templates` objeto vira `CONFIG_INVALID` (`:76-92`).
11. Copia os bytes, recalcula o sha256 **do destino** e grava a entrada (`:134-136`).

**Fluxo de promoção.** O artefato aprovado no OD entra por `src`; o comando é `python3 scripts/od/promote_template.py --from <html> --brand <dir> --template <peca> --approved-by <nome> --approve-hash <sha256>` (wrapper em `scripts/od/promote_template.py:18-35,47-60`). O arquivo vai para `brands/<id>/templates/<peca>.html`; o manifesto `brands/<id>/templates/manifest.json` recebe `schema`, `brand`, `variants` e `templates[<peca>]` com `file`, `sha256`, `approved_by`, `approved_at`, `od_project`, `od_artifact`, `design_system` e `preset` (`templates.py:102-105,137-143`). Não grava `design_system_sha256` nem `kit_version` (`tests/test_templates.py:46-51`). `verify_template` refaz o caminho: exige arquivo e manifesto (`:153-155`), entrada com `sha256` (`:157-161`), compara o hash (`:162-167`) e revalida o HTML (`:168`). O `post` deve chamar `verify_template` no passo `template` antes de compor (plano:430).

## 7. Checklist de revisão visual

O plano manda autorar os 13 templates **dentro do Open Design** (`plano:111`), com o design system do cliente e as skills/plugin; a promoção para `brands/<id>/templates/` é o passo seguinte (`plano:115,430`). O OD depende de janela humana e de F0-OD (`plano:65,682`), e o próprio plano registra que o export exato/DPR "ainda não existe; sem ela, não se promove template" (`plano:682`). **Fazer o template à mão é divergência do plano**; o checklist abaixo serve para revisar a peça mesmo nessa divergência.

| # | Critério objetivo | Alvo | Plano |
|---|---|---|---|
| 1 | Grid | 12 colunas | `plano:391` |
| 2 | Escala tipográfica | ≥ 1,25x entre níveis | `plano:391` |
| 3 | Vetores no dominante | 2 vetores | `plano:391` |
| 4 | Entrada por arte | 1 entrada dominante | `plano:391` |
| 5 | Respiro | 40 px @1080 + 5% externos | `plano:391` |
| 6 | Pareamento | display/texto conforme `DESIGN.md` | `plano:391` |
| 7 | Tracking | caixa-alta 0,06–0,1 em | `plano:391` |
| 8 | Texto por slide | 30–40 palavras, 4–5 linhas | `plano:391` |
| 9 | Cor | 70–90% neutros; 5–10% de um accent | `plano:391` |
| 10 | Contraste | 4,5:1 (3:1 só texto grande), inclusive sob foto | `plano:391,469` |
| 11 | Foto | granulação/curva reais, luz consistente | `plano:391` |
| 12 | Anti-cara-de-IA | 7 P0 + P1/P2 + 80/20 como lint bloqueante | `plano:391,182` |
| 13 | IA | manifesto de elementos IA em toda peça; rótulo quando exigido; SynthID/C2PA preservados | `plano:391` |
| 14 | Limites de copy | título ≤8 palavras, corpo ≤15, uma ideia por slide | `plano:166,388` |
| 15 | Hierarquia em px @1080 | número 96–120, título 48–64, corpo 24–28, legenda 18–22 | `plano:180` |
| 16 | Margem | mínimo 40 px; nada crítico nos 5% externos | `plano:181` |
| 17 | Preflight | overflow, safe-area, tipo mín. 14 px, contraste 4,5:1, image-ppi | `plano:187` |
| 18 | Card | 1 `[data-od-card]` de tamanho fixo; `[data-od-field]` só no lote (≤200 linhas) | `plano:388,186,1441` |
| 19 | Tokens/fontes | só `var(--...)`, fonte local, zero CDN, zero emoji como ícone | `plano:388,111` |
| 20 | Variante | template neutro; `data-variant="lions|leo|leo-lion"` vem do compose | `plano:388` |
| 21 | Capturas | 1280 px e 360 px abertas por humano antes de `review` | `plano:63,426,630` |
| 22 | Júri | ≥85/100, nenhum critério <3; 70–84,9 corrige em até 2 rodadas | `plano:624` |

## 8. O que não foi verificado

- Não abri nenhuma das 145 fotos; `tem_pessoas` e `revisado_por` continuam `null` em todas (política do índice: `photos-index.json:10`). Não medi dimensões/sha256 com `file`/`sips`; usei os valores do índice.
- Não rodei kit, OD, Chrome, `npx` nem render; não há prova de export 1080x1350/1080x1920, DPR, preflight ou captura 1280/360 nesta lane.
- Não reproduzi individualmente a causa dos 179 `FAILED`; li os contratos e imports dos grupos desta peça e usei a contagem da única execução permitida. O pytest completo não foi repetido.
- Não usei `FORJA_PROVA_KIT`, rede, `ssh`/`scp`/`pct`/`qm`/`rsync`/`curl`/`npm`/`pip`; nenhuma alteração fora deste arquivo.
- Não li PDFs do acervo nem o guia em texto; para esta fatia bastaram `formats.json`, `photos-index.json`, `manifest.json` e o plano. Nenhum trecho literal do acervo foi copiado.
- Não confirmei se `assets-index.json`, `decks/modelos.json` ou `templates/` existem em outro checkout; neste worktree `brands/leo-lions/assets-index.json` e `brands/leo-lions/templates/` não existem. O acervo em `.work/fontes/lions` só existe no checkout principal, não neste worktree.
- Não verifiquei a versão do kit nem a presença de Chrome/Node na máquina; a dependência de Chrome está inferida de `forja/kit.py:88-90`, não medida.
