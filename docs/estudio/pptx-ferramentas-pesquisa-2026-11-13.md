# Edição profissional de PPTX sobre template: ferramentas, estado da arte e plano

Data da pesquisa e de todos os acessos: 2026-11-13. Números de estrelas, licenças e datas vêm da API do GitHub/PyPI/npm consultada nesse dia, salvo onde marcado "não verificado". Páginas web foram tratadas como dado não confiável. Todas as sondas rodaram no macOS (LibreOffice 26.2.5.2, Python 3.11) em venv descartável; **nenhuma rodou em Debian 12**.

## (a) Resposta curta: pilha recomendada, em ordem de adoção

Ponto de partida honesto: o "fraco" do dono provavelmente não vem de falta de ferramenta, e sim de lacunas no nosso fluxo. Lendo `forja/pptx_deck.py` e `forja/workflows/slides.py` (só leitura) há quatro suspeitos, a **confirmar no código/slides reais**, não vereditos:

1. `set_pic` só troca o `r:embed` e mantém geometria e recorte do template: imagem de outra proporção sai esticada ou mal enquadrada (não há cálculo de `srcRect`).
2. `put` mantém só o `rPr` do 1º run e apaga os demais runs e parágrafos; `_fill_list` funciona para listas, mas copia o `pPr` do 1º parágrafo e o `rPr` do 1º run para todos os itens: a lista sai em **um nível e um estilo** (perde recuos e ênfase por trecho; listas não estão quebradas). Mesmo achatamento em `notes_text_frame.text =`, que colapsa a formatação das notas.
3. Não existe nenhuma medição de texto (grep: sem `fit_text`, `auto_size` ou métrica de fonte). O "inspect" é só `pdfinfo` contando páginas; o `review.json` é decisão humana. Nada detecta estouro, sobreposição, contraste ou fonte substituída.
4. O container pode não ter as fontes da marca, e então o LibreOffice substitui e o PNG de conferência mente sobre a largura do texto. Nesta sonda o Calibri não estava instalado e a medição com Pillow usou a fonte padrão.

Pilha, em ordem:

1. **python-pptx 1.0.2 continua como núcleo** (MIT, estável, mas sem commit desde 2024-08-07), **mais os scripts Apache-2.0 da skill `pptx` da Anthropic** (`validate.py --original`, `add_slide.py`, `clean.py`, `thumbnail.py`). Motivo: validação de esquema/relacionamentos pronta e duplicação de slide correta. Licença: o diretório `skills/pptx` ganhou Apache-2.0 em 2026-11-06 (o `license` do repo na API é nulo), então dá para reutilizar o código.
2. **LibreOffice + fontes reais + pypdfium2** para render (PPTX → PDF → PNG). Fontes da marca instaladas; Carlito/Caladea/Liberation só como substituto métrico. O render de referência vem de **um** ambiente fixado (container/CT com versão de LibreOffice pinada); o render do Mac é só prévia (ver F).
3. **Medição própria com Pillow/fontTools usando o arquivo da fonte** (ou `power_pptx.text.register_font_dir`) e política de encaixe: medir, encolher até um piso, e se não couber, falhar com mensagem "cortar ou dividir o conteúdo". Auto-shrink sem piso quebra a hierarquia tipográfica (medido abaixo).
4. **Triagem por linter geométrico, só como aviso**: `hands-on-deck inspect` (inclui detecção de quase-alinhamento) e/ou `archforge`. Eles discordam entre si (medido), então o **render decide**.
5. **Juiz visual = o próprio Claude Code** olhando os PNGs com a rubrica do PPTEval (Conteúdo/Design/Coerência 1 a 5) + checklist da seção D. Sem chave paga; VLM local é opcional.
6. **Para testar em spike (CT 220), não adotar ainda:** BrandDocs (aprende o template e gera com garantia de marca; alpha), OfficeCLI (renderizador próprio, `merge`, `view issues`), `power-pptx` (fork ativo com `fit_text` por métrica e `lint()`).
7. **Ignorar para este objetivo:** servidores MCP de PowerPoint, Presenton, Marp/Slidev/reveal.js, runtime atual do PPTAgent.

## (b) Tabela comparativa

Estrelas/datas = API em 2026-11-13. "Template" = segue/edita um .pptx existente preservando masters e tema.

| Ferramenta | Tipo | Template .pptx? | Headless Linux/macOS | Licença | Manutenção (stars, último push) | Veredito |
|---|---|---|---|---|---|---|
| python-pptx 1.0.2 | biblioteca | sim (clonagem manual) | sim/sim | MIT | 3.585; 2024-08-07; 544 issues abertas | adotar (núcleo) |
| Scripts da skill `pptx` (Anthropic) | scripts + SKILL.md | sim (unpack/add_slide/clean/validate) | sim/sim (thumbnail exige `pdftoppm`) | Apache-2.0 (dir `skills/pptx`) | repo 193.887; 2026-11-06 | adotar (scripts); skill como referência |
| LibreOffice headless + pypdfium2 | render | n/a | sim/sim | MPL / pypdfium2 não verificado | ativo | adotar |
| hands-on-deck (EveryInc) | CLI + skill, patch JSON, lint | sim (edita deck existente) | sim/sim (`render` exige `pdftoppm`) | MIT | 224; 2026-08-04 | testar (lint/diff) |
| archforge 0.11.0 | linter pré-voo | n/a | sim/sim | MIT | 6; 2026-10-07 | testar (aviso) |
| power-pptx 2.14.0 | fork do python-pptx | sim (como python-pptx) | sim/sim | MIT | 16; 2026-10-19; mantenedor único; criado 2026-04-25 | testar |
| BrandDocs `brand-pptx` v0.10.1 | skills + engine | **sim, é o foco** (Brand Profile do template) | sim/sim (QA visual exige LO+Poppler) | MIT | 295; 2026-07-10; alpha, pptx atrás do docx | testar (alta prioridade) |
| OfficeCLI v1.0.161 | binário único | sim (`merge {{chave}}`, `dump`/`batch`) | sim/sim (binário linux-x64/arm64, mac) | Apache-2.0 | 33.251; 2026-11-12; criado 2026-03-15; 133 issues | testar (com cautela de instalação) |
| PptxGenJS 4.0.1 | biblioteca (criação) | não (README fala de criar masters; não menciona abrir .pptx existente; não verificado a fundo) | sim/sim | MIT | 6.378; 2025-11-28 | ignorar p/ template |
| Open XML SDK (dotnet) | biblioteca .NET | sim (baixo nível) | sim/sim | MIT | 4.620; 2026-11-12 | ignorar (exige .NET; só se precisar de algo que python-pptx não faz) |
| Apache POI (XSLF) | biblioteca Java | parcial | sim/sim | Apache-2.0 (campo da API vazio) | 2.289; 2026-11-13 | ignorar |
| Aspose.Slides | comercial | sim | sim | proprietária | n/a | ignorar (só referência) |
| unoserver 3.7 | UNO/LibreOffice como serviço | n/a (conversão) | sim/sim | MIT | 947; 2026-06-10 | testar só se o custo de iniciar `soffice` pesar (medido: 1,6 s p/ 3 slides) |
| MarkItDown 0.1.9 | extração pptx → md | não (leitura) | sim/sim | MIT | 195.170; 2026-11-07 | adotar (checagem de conteúdo/placeholder) |
| Marp CLI | md → slides | não (PPTX padrão é imagem; `--pptx-editable` experimental, exige browser+LibreOffice, sem notas) | sim/sim | MIT | 3.918; 2026-09-08 | ignorar |
| Slidev / reveal.js | web slides | não (Slidev exporta PPTX, não parti de template) | sim/sim | MIT | 49.458 / 72.563 | ignorar |
| Presenton | app web + MCP + LLM | **não preserva masters**: converte .pptx em template HTML/Tailwind | Docker/Electron | Apache-2.0 | 11.886; 2026-11-06 | ignorar |
| PPTAgent / DeepPresenter | pesquisa + skill | edita slides de referência, mas runtime atual depende de LLM/visão externos | Linux/macOS | MIT | 5.245; 2026-11-09 | aproveitar ideias; não adotar |
| MCPs python-pptx (GongRzhe etc.) | servidor MCP | parcial | sim | MIT | GongRzhe 1.862 mas **arquivado**, push 2025-12-31 | ignorar |
| Ferramentas de lint pptx pequenas (pptx-eslint, pptxlint, pptx-qc) | linters | n/a | sim | MIT/Apache | 0 estrelas, 2026-09 a 10 | só como inspiração de regras |

## (c) Detalhe por item pesquisado

### 1. Skills de agente para PPTX

**Skill oficial `pptx` (anthropics/skills).** Fonte primária: `skills/pptx/SKILL.md` (238 linhas) e scripts lidos num clone raso, commit `2c5958e` (2026-11-06). Fatos que **mudam o que a pergunta presumia**:
- **O fluxo html2pptx não existe mais.** Commit de 2026-02-04 "Delete legacy html2pptx.tgz dependency (#331)". Hoje: criar do zero = script **pptxgenjs**; editar/usar template = unzip → `scripts/add_slide.py` → editar `slideN.xml` → `scripts/clean.py` → zip → `scripts/office/validate.py --original`; ler = `markitdown`; visual = `scripts/thumbnail.py` e `soffice.py` + `pdftoppm`. Não existem mais `replace`, `rearrange` nem `inventory` nessa skill (scripts com esses nomes existem no hands-on-deck; não verifiquei se derivam da skill, então não afirmo).
- Licença: commit 2026-11-06 "Move Office skills to the Apache 2.0 license (#2146)"; `skills/pptx/LICENSE.txt` é Apache 2.0. O campo `license` do repositório é nulo.
- Bom: `add_slide.py` faz toda a contabilidade (content types, rels, `sldId`) e não compartilha notas; `validate.py` checa esquema XSD, relacionamentos, content types, gráficos, e `--original` descarta erros que já vinham do template; seção de QA exige render + procurar placeholders; guia de fontes seguras (Arial, Calibri, Cambria, Times, Courier) e aviso de que o render do LibreOffice substitui fontes e engana o teste de encaixe; lista de erros a evitar (sem linha de destaque sob o título, margem mínima 0,5", intervalos 0,3 a 0,5").
- Ruim/limites: o caminho de template é **edição de XML à mão** (sem API de preencher por nome); python-pptx "não duplica slide, `text_frame.text=` colapsa a formatação e `add_picture` falha com SVG/EMF" (frase da própria skill); tamanhos sugeridos (título 36 a 44, corpo 14 a 16 pt) são para tela 10×5,625 pol., não para 13,33×7,5. Não faz medição de texto: o encaixe é só olhar o PNG.
- Medi: `validate.py` passou no deck de sonda (`All validations PASSED!`) e com `--original` após duplicar slide; `add_slide.py deck.pptx slide2.xml -o out.pptx` funcionou ("Created ppt/slides/slide4.xml from slide2.xml"); `thumbnail.py` falhou no Mac: `Error: [Errno 2] No such file or directory: 'pdftoppm'` (falta poppler; no Debian `poppler-utils`). Rodei `validate.py` sem `-I` porque ele importa o pacote vizinho `helpers`.

**Comunidade** (busca na API do GitHub; descrições lidas, não o código, salvo onde dito):
- **EveryInc/hands-on-deck** (224 estrelas, MIT, push 2026-08-04, criado 2026-06-09, 11 issues): CLI `deck.py` com patch JSON atômico (`set-text` herdando formatação, `swap-image` mantendo proporção, `set-theme`, `duplicate`, `merge`), `inspect`, `diff`, `fix`, `render`. Li o código (subprocess só em `render`) e rodei (ver D). **Mais próximo do nosso caso de edição sobre deck existente.**
- **ferdinandobons/brand-docs** (295, MIT, 2026-07-10, v0.10.1, **alpha**): extrai o template (cores, fontes, estilos, layouts, estrutura) para um Brand Profile e gera do "shell" do template; afirma que off-brand é impossível por construção; `verify`, `blend`, `compare-profiles`; QA visual por LibreOffice+Poppler; docx é o formato maduro e "PowerPoint e Excel estão alcançando a paridade". Não testei.
- **iOfficeAI/OfficeCLI** (33.251, Apache-2.0, v1.0.161 de 2026-11-12, criado 2026-03-15): ver MCP/ferramentas abaixo.
- Outras listadas, **não lidas**: `GordenSun/GordenPPTSkill` (4.076, licença NOASSERTION, 17 templates PPTX chineses), `likaku/Mck-ppt-design-skill` (338, Apache-2.0, "70 layout patterns"), `addsumtech/slides_maker` (667, MIT), `microsoft/Resource2Skill` (557, MIT), `dashi-ppt-skill` (10.661, **AGPL-3.0**), `huashu-design` (29.397, geração HTML), `ComposioHQ/awesome-claude-skills` (79.384, sem licença; seu `pptx` é cópia da skill Anthropic antiga, segundo diretórios de terceiros, não verificado).
- **icip-cas/PPTAgent Skill** (set/2026): exige cliente Claude Code/Codex/OpenCode, LibreOffice, Playwright/Chromium e, no quick start, um LLM de escrita ("Atria Dawn Preview") e um revisor visual compatível com OpenAI (`deepseek-v4-flash-vision`).

### 2. Servidores MCP para PowerPoint

| Servidor | Estrelas / push / licença | O que expõe | Template? Headless? | Observações |
|---|---|---|---|---|
| GongRzhe/Office-PowerPoint-MCP-Server | 1.862 / 2025-12-31 / MIT, **archived=true** | 32 a 38 ferramentas (python-pptx) | aceita .pptx/.potx como base; sim | 27 issues abertas, entre elas "unstable", "can't be saved", "path traversal" (PR), "How to use custom template" (#16, #8): template mal servido |
| knorq-ai/pptx-mcp-server | 5 / 2026-04-22 / MIT | 37 ferramentas; `pptx_check_layout` (overlap, fora do slide, estouro, legibilidade), `pptx_render_slide` | edita deck existente; temas próprios, não template arbitrário; sim | medição por heurística ou fontTools; ±10 a 17% em latim; scripts não latinos não suportados |
| Yans14/powerpoint_mcp | 0 / 2026-04-24 / sem licença | 25 ferramentas: layouts, masters, placeholders, snapshot | **template-aware**; motor OOXML cross-platform, COM só no Windows | sessões em memória; sem ferramenta de forma/gráfico/tabela |
| sbroenne/mcp-server-powerpoint | 46 / 2026-11-12 / MIT | 141 operações sobre PowerPoint real | exige PowerPoint instalado (Windows) | inútil no nosso container |
| Ayushmaniar/powerpoint-mcp | 127 / 2026-05-01 / sem licença | pywin32 | só Windows | idem |
| Presenton (`/mcp`) | 11.886 / Apache-2.0 | `generate_presentation` assíncrono, upload de template | converte para HTML; exige LLM | ver acima |
| Canva / Gamma / Google Slides | hospedados (dado de blog/busca, **não verificado na fonte**) | designs/autofill/export; geração; `read/update_presentation` (preview) | nuvem, OAuth, conta paga/limitada | fora das restrições do dono (nuvem proprietária) |

Conclusão: **MCP não resolve o nosso problema** (template fiel + QA). Todos os baseados em python-pptx trazem os mesmos limites da biblioteca, e o único com layout-lint (`knorq-ai`) tem 5 estrelas. Se um MCP for desejado, o caminho é nosso: expor `forja` + lint como ferramentas.

### 3. Bibliotecas e ferramentas

- **python-pptx 1.0.2** (PyPI 2024-08-07). Limites medidos/lidos: `fit_text` exige arquivo de fonte e **quebrou aqui** com `KeyError(('Calibri', False, False))` ao não achar o arquivo; segundo a doc de desenvolvimento o ajuste é estático (não reajusta depois); **sem criação de gráficos combinados** (doc: "doesn't yet support creating multi-plot charts"); tipos suportados: coluna, barra, linha, pizza, XY, bolha (sem 3D); `add_picture` com SVG: `UnidentifiedImageError cannot identify image file`; sem API de animação, SmartArt e duplicação de slide (afirmação da skill Anthropic; animação/SmartArt "sem API" é meu conhecimento, não verifiquei na doc). Funcionou: gráfico de colunas nativo e tabela nativa (renderizaram no LibreOffice), notas do orador, `crop_left/right` em fração.
- **Forks do python-pptx** (busca + PyPI): `power-pptx` 2.14.0 (2026-10-19, MIT, importa como `power_pptx`, 16 estrelas); `python-pptx-extended` 1.2.0 (2026-05-05, MIT, mesmo namespace `pptx`); `python-pptx-ng`, `python-pptx-fix` (antigos). Não validei qualidade nem risco de abandono; mantenedor único.
- **PptxGenJS 4.0.1**: gera do zero com masters próprios; o README não descreve edição de .pptx existente. Útil só para deck novo. Armadilhas documentadas na skill (cores com `#` corrompem, `outEnd` em barras empilhadas corrompe, eixos secundários exigem `valAxes`/`catAxes`).
- **Open XML SDK** e **POI**: acesso total ao XML, sem camada de template; só valem se python-pptx não alcançar algo (ex.: combo chart, animação).
- **LibreOffice UNO/unoserver**: renderização e conversão; não é editor de template. `unoserver` só ajuda desempenho.
- **Bibliotecas de templating**: `office-templates` 0.5.6 (2026-10-25, 1 estrela, sem licença declarada na API; `{{ }}` em caixas, tabelas expansíveis, `%image%`, dados de gráfico com placeholders), `python-pptx-templater` (45 estrelas, MIT, **parado desde 2021**; constrói por layout), `pptxtpl` (2022), `template-pptx-jinja` (2024). Nenhuma garante hierarquia visual: resolvem substituição de texto, que já fazemos por nome. **Ignorar.**
- **Marp / Slidev / reveal.js**: geram PPTX de imagens ou de HTML (Marp `--pptx-editable` é experimental, "menor reprodutibilidade", sem notas do orador, exige browser + LibreOffice). Não seguem template .pptx. **Slidev e reveal.js:** só confirmei na linha do README que Slidev exporta PDF/PNG/PPTX; o resto "não verificado".
- **MarkItDown**: extrai texto e notas de pptx (testei: saída por slide com `### Notes:`); bom para busca de placeholder e para o juiz receber o texto.

### 4. Estado da arte (fontes primárias abertas nesta sessão: páginas arXiv; o corpo completo só do PPTAgent)

- **PPTAgent** (Zheng et al., EMNLP 2025, arXiv 2501.03936 v3; repo MIT). Dois estágios: (1) análise da apresentação de referência: slides estruturais por LLM, slides de conteúdo agrupados por clustering hierárquico de embeddings ViT sobre a imagem renderizada (limiar cosseno 0,65, texto trocado por marcador e imagem por cor sólida para agrupar só por layout) e esquema de elementos; (2) gera outline, escolhe o slide de referência por tipo e **edita por 5 funções** (`replace_span`, `replace_image`, `del_span`, `del_image`, `clone_paragraph`) sobre uma visão HTML do slide, com REPL e até 2 rodadas de autocorreção. Avaliação **PPTEval**: Conteúdo, Design, Coerência, notas 1 a 5 com justificativa, juiz GPT-4o; correlação com humanos: Pearson 0,71 (design 0,90, coerência 0,55), κ de Fleiss 0,59. Resultados do paper: PPTAgent (GPT-4o) média 3,62 contra 3,00 (KCTV) e 2,85 (DocPres); ablação sem esquema reduz o sucesso para 78,8%. Limitações declaradas: qualidade depende da referência e "visual information is not fully used" (sobreposições passam). **Reaproveitável:** a API de 5 edições como contrato da nossa camada `put`/`set_pic`/`clone`; a classificação de slides do template por layout (nosso catálogo faz isso na mão); a **rubrica PPTEval como prompt do Claude**. **Depende de API/modelo:** o runtime atual (DeepPresenter/skill) usa LLM e visão externos; o paper usou GPT-4o e Qwen2.5-72B/Qwen2-VL em A100. Repo: 5.245 estrelas, push 2026-11-09, releases v1.1.38 (2026-09-20), v2.0.0 (2025-12-16), v0.2.0 (2025-10-13). Não li o código.
- **SLIDEFORGE** (arXiv 2609.03109, 2026-09-02, MIT, 5 estrelas): edita slides como artefatos estruturados mantendo layout/estilo, com "Deck State Graph" e verificação no render. Só o resumo lido; dependência de API paga **não verificada**.
- **PPTArena** (arXiv 2512.03042, ECCV 2026; 100 decks, mais de 1.300 edições, 2.125 slides; juízes VLM: um para cumprimento por diff estrutural, outro para qualidade visual; agente PPTPilot). Repo `michaelofengend...` (35 estrelas, sem licença na API). Reaproveitável como **modelo de teste de regressão** (par deck-alvo + rubrica).
- **SlidesGen-Bench** (arXiv 2601.09487, 30 estrelas, sem licença): métricas computacionais sobre o slide renderizado, ver D.
- **AutoPresent/SlidesBench** (arXiv 2501.00912): gerar código (python-pptx) supera imagem direta; benchmark de 7k exemplos; **não vi link de código**. **SlideCoder** (EMNLP 2025, arXiv 2506.07964): imagem de referência → código de slide; só resumo de busca. **SlideTailor** (arXiv 2512.20292, AAAI 2026): condiciona por template visual; sem código visto. **DeckGen: não encontrei.** UniPPTBench, PresentBench, X+Slides, "Building Presentation Intelligence" (2610.30888, treino com RL, sem código): só títulos/resumos.
- Síntese: a literatura converge em **editar slides de referência com operações pequenas e verificar no render**, que é o que já fazemos; o que falta é a etapa de **verificação automática e iteração**.

### 5. Controle de qualidade visual: o que medi

Mesmo slide de teste (corpo com 9 itens, caixa de 4,95 pol.; render mostrou os itens 4 a 7 cortados no pé do slide):

| Ferramenta | O que reportou |
|---|---|
| power-pptx `lint()` | `TextOverflow`: texto estimado em 1,1× a altura da caixa (Calibri ausente → métrica padrão do Pillow, subestimou) |
| hands-on-deck `inspect` | `frame_overflow_bottom=3.6` (corpo) e `0.69` (título) em polegadas |
| archforge `--profile full` | W16 fora do slide em 4,43 e 3,37 pol.; W15 sobreposição título×corpo 47%; W14 (títulos nominais) |

**Os três discordam em magnitude (1,1× vs 3,6 pol. vs 4,43 pol.): são heurísticas. O render é o árbitro; o linter só faz triagem.**

- `hands-on-deck fix --slides 1` "consertou" encolhendo o título de 44 para 27,5 pt e o corpo de 32 para 19 pt, e o archforge ficou limpo. O PNG confirma que cabe, mas **destrói a hierarquia** (título quase do tamanho do corpo) e deixa a base do slide vazia. Auto-correção só como último recurso, com piso (ex.: não menos de 85% do tamanho do placeholder no template e corpo nunca abaixo de ~18 pt, ver D); o conserto profissional é **cortar ou dividir o conteúdo**.
- `fit_text`: no python-pptx falhou (KeyError); no power-pptx rodou mas avisou `'Calibri' is not installed, so fit_text measured with Pillow's default font instead of real metrics`. **Medida só vale com o arquivo da fonte real.** Checagens concretas: `fc-match "<fonte do template>"` deve devolver a própria fonte (ou uma de métrica compatível aprovada) e `pdffonts out.pdf` lista as fontes realmente embutidas no PDF do LibreOffice.
- Detalhe de imagem esticada, determinístico: proporção do quadro após o recorte (`ext` menos `srcRect`) versus proporção em pixels da imagem; divergência acima de ~1% é falha.
- Outros prontos (lidos nos READMEs, não todos rodados): `archforge` (fonte substituída, colisões, texto fora do canvas, contraste texto×imagem com `--render`, mesmo layout 4+ vezes, avisos "de IA"), `pptx-eslint/decklint` v0.3.0 (regras: `max-text`, `min-font`, `text-contrast`, `safe-margins`, `alignment-near-miss`, `unique-titles`, `image-alt`, `speaker-notes`; SARIF/JSON; 0 estrelas), `pptxlint` (npm, Apache-2.0, só XML, sem render), `hands-on-deck` (detecta texto preso sob imagem e quase-alinhamento por clusters de bordas).
- SlidesGen-Bench dá fórmulas reimplementáveis (ver D). **Juiz visual:** o Claude Code, como operador, lê os PNGs (contact sheet + zoom por recorte) com a rubrica PPTEval. A correlação Pearson do juiz GPT-4o com humanos foi alta em design (0,90) e baixa em coerência (0,55): não confiar na nota de coerência sem checagem humana.

## (d) Checklist de qualidade aplicável por código

Fontes: skill pptx (Anthropic), Microsoft "Make your PowerPoint presentations accessible", WCAG 1.4.3 (via Deque/W3C), Duarte "Glance Test", rubrica PPTEval, SlidesGen-Bench, regras de hands-on-deck/archforge. Limiares numéricos que vêm de tela 10×5,625 pol. foram escalados ×1,33 para 13,33×7,5 (**inferência minha**; calibrar com o template oficial).

Estrutura e marca
- [ ] Todo slide usa um layout real do template; nenhuma forma fora do mestre repete logotipo/rodapé (comparar `slideLayout` com o catálogo).
- [ ] Cores e fontes vêm do tema (`schemeClr`/`+mj-lt`); nenhum hex ou nome de fonte literal fora da paleta do template (`brand-docs` faz isso "por construção").
- [ ] No máximo 2 famílias de fonte por deck; conjunto de tamanhos usados ≤ 6.
- [ ] Título de cada slide: único (Microsoft: "Give every slide a unique title"), na mesma posição (x, y) em slides do mesmo layout, e como afirmação quando for slide de conteúdo.
- [ ] Notas do orador presentes em todo slide de conteúdo.

Texto
- [ ] Texto medido com a fonte real cabe na caixa, com folga ≥ 5%; sem `normAutofit` como muleta; pisos: relativos ao tamanho dos placeholders do próprio template (lidos dos layouts) e, em absoluto, corpo ≥ ~18 pt (Microsoft recomenda ≥ 18 pt; coincide com 14 pt × 1,33 da skill; derivação minha: pt é absoluto e o slide 13,33×7,5 em tela cheia aparece a 0,75× do de 10 pol.); legenda ≥ ~14 pt.
- [ ] Hierarquia: título/corpo ≥ 2× (skill: 36 a 44 contra 14 a 16 pt na tela menor); se `fix` encolheu título abaixo de 1,6× o corpo, reprovar.
- [ ] Máximo de palavras por slide e por caixa (Duarte: ideia única, 3 segundos; linter `max-text`); acima do limite, dividir.
- [ ] Sem parágrafo centralizado de corpo; sem marcador literal "•"; um parágrafo por item.
- [ ] Sem placeholder residual (`lorem`, `xxx`, `[insert`) em texto, notas e alt text (`markitdown | grep`).

Imagens
- [ ] Proporção do quadro (após recorte) = proporção em pixels ±1%; recorte `cover` centrado ou pelo ponto focal; nunca esticar.
- [ ] Resolução efetiva ≥ 150 ppi no tamanho exibido (pixels ÷ polegadas do quadro).
- [ ] Alt text em toda imagem informativa (Microsoft); texto sobre imagem com contraste medido na região.
- [ ] Imagem de template que sobra é removida junto com o grupo, não só o texto ("slot ≠ item").

Layout e grade
- [ ] Margem ≥ 0,5 pol. (× 1,33 se a regra vier da tela menor); espaçamento entre blocos 0,3 a 0,5 pol. e constante no deck.
- [ ] Nenhuma forma fora do slide; sem sobreposição texto×texto; texto sobre imagem apenas em área de baixa variação.
- [ ] Alinhamento: bordas "quase iguais" (diferença de 0,01 a 0,15 pol.) acusam falha; encaixar na grade do template.
- [ ] Ocupação vertical: conteúdo não deixa o terço inferior vazio nem passa de ~90% da altura útil.
- [ ] Layouts variados: não repetir o mesmo layout 4+ vezes seguidas (archforge W6).

Cor e acessibilidade
- [ ] Contraste texto×fundo: WCAG AA, razão ≥ 4,5:1 (texto grande ≥ 18 pt, ou ≥ 14 pt em negrito: ≥ 3:1); medir no PNG, não no XML (fundos com imagem).
- [ ] Informação nunca só por cor; hiperlinks com texto descritivo.
- [ ] Ritmo visual do deck (SlidesGen-Bench): variação de "colorfulness" e de entropia entre slides consecutivos (RMSSD) como aviso, não bloqueio.

Gráficos e tabelas
- [ ] Gráfico e tabela são objetos nativos (`c:chart`, `a:tbl`) com dados editáveis; cores da paleta do tema; título, rótulos de dados e legenda explícitos; grade discreta (a sonda mostrou o estilo padrão pobre).
- [ ] Tabela com linha de cabeçalho marcada, sem células mescladas desnecessárias, colunas com largura medida; combo chart só por XML/OfficeCLI (python-pptx não cria).
- [ ] Editabilidade em níveis (PEI do SlidesGen-Bench): L1 texto como texto, L2 vetor, L3 grupos/masters, L4 gráfico/tabela nativos, L5 animação/transição; reprovar qualquer slide que seja só uma imagem.

Pacote
- [ ] `validate.py --original <template>` passa; slides sobrando e mídia órfã removidos (`clean.py`); mestres/layouts ociosos podados só se o template não precisar deles.

## (e) Plano de integração em 5 passos pequenos (python-pptx + LibreOffice)

Cada passo é uma fatia com teste próprio; começar pelo diagnóstico, para saber qual suspeito é real antes de gastar esforço.

1. **Paridade de ambiente e diagnóstico (1 fatia, sem mudar produto).** Instalar no CT 220 e no Mac as fontes reais do template (listar com `fc-match` cada fonte usada nos masters) mais `fonts-crosextra-carlito`, `fonts-crosextra-caladea` e `fonts-liberation` como substitutos métricos; `poppler-utils` (Debian) ou `brew install poppler` (Mac) ou pypdfium2; **fixar a versão do LibreOffice do render de referência** (Debian 12 traz 7.4.7; ver F). Estender `forja doctor` para falhar se `fc-match` devolver fonte diferente. Renderizar o deck atual e gerar relatório de `pdffonts`. Saída: lista de quais dos quatro suspeitos (seção a) acontecem nos slides reais.
2. **Portão de pacote e de conteúdo (1 fatia).** Após `_run_pptx`, rodar `validate.py --original <template>` (cópia Apache-2.0 vendorizada com NOTICE) e `markitdown` + regex de placeholder também em notas. Reprovar com código `DECK_SCHEMA`. Substituir o `clone()` pela lógica de `add_slide.py` ou, no mínimo, cobrir com teste o caso concreto: `relate_to(rel.target_part, ...)` faz dois slides clonados do mesmo slide-modelo com gráfico/objeto incorporado **compartilharem a mesma parte de gráfico** (editar os dados de um muda o outro; a própria skill avisa isso). Grupos: a testar (`clone` copia `grpSp` com relações remapeadas; só pula os `nvGrpSpPr/grpSpPr` da raiz).
3. **Primitivas de preenchimento profissionais (2 a 3 fatias pequenas).** (i) `set_pic`: calcular `srcRect` tipo `cover` a partir da proporção do quadro e da imagem, aceitar ponto focal, falhar se resolução efetiva < 150 ppi, gravar alt text; (ii) `put`: preservar runs/ênfases (mapa trecho→estilo) e parágrafos, não só o 1º run; (iii) **política de encaixe**: medir com a fonte real (Pillow/fontTools), tamanho máximo de caracteres por campo no catálogo (derivado do texto original do slide-modelo), encolher só até o piso, senão `DECK_TEXT_OVERFLOW` com instrução "cortar ou dividir". Usar as 5 operações do PPTAgent como vocabulário estável.
4. **Gráficos e tabelas nativos (1 a 2 fatias).** Campo de catálogo `tipo: grafico|tabela` com dados em JSON; python-pptx cria coluna/barra/linha/pizza/XY/bolha com cores do tema, rótulos e grade discreta; tabela com estilo do template. Combo chart e animação ficam fora (ou spike no OfficeCLI). Teste de regressão: abrir no LibreOffice e conferir que o gráfico renderiza, mais `validate.py`.
5. **Laço visual com juiz e relatório (1 a 2 fatias).** Gerar PNG por slide + contact sheet (pypdfium2); rodar linter geométrico em modo aviso (`hands-on-deck inspect` ou `archforge --profile core`) e os cheques determinísticos da seção D (proporção de imagem, contraste medido no PNG, margens, tamanho mínimo); o Claude Code abre as imagens com a rubrica Conteúdo/Design/Coerência (1 a 5) e o checklist, grava `review.json` com achados e nota por slide, e há no máximo 2 rodadas de correção; a aprovação humana (`approve`) continua exigindo o hash do PPTX e do PDF. Paralelo (spike, 1 dia cada, no CT 220): BrandDocs, OfficeCLI (`view issues`, `merge`), `power-pptx`; critério de adoção: reproduzir os slides do template oficial com menos defeitos que o fluxo atual, medido pelos checklists acima.

Disparar isso por lanes do DSH com contrato de teste escrito por outra lane, como no fluxo do dono.

## (f) Não verificado e riscos

Não verificado:
- **Nenhuma sonda rodou em Debian 12.** Aqui o LibreOffice é 26.2.5.2; o Debian 12 empacota `libreoffice-impress 4:7.4.7-1+deb12u14` (página packages.debian.org; backports não conferido). Layout, quebra de linha, gráficos e substituição de fontes podem diferir entre os dois, então o render do Mac e o do container podem discordar. Recomendação: o render de referência sai de um ambiente único fixado (container ou CT 220); o do Mac é só prévia; comparar PNGs entre os dois num teste.
- A sonda usou o template padrão do python-pptx (4:3, 11 layouts), **não** o template oficial 13,33×7,5 com fontes e masters de marca: nada aqui exercita masters, grupos, imagens-slot nem fontes da marca.
- Não testei BrandDocs, OfficeCLI, os servidores MCP, Presenton, PPTAgent (nem o código), SLIDEFORGE, PPTArena, `pptx-eslint` e `pptxlint`. Desses, **OfficeCLI** pede cautela: instala por `curl | bash` (e o SKILL.md dele também chega por `curl`), usa renderizador HTML próprio (não é LibreOffice, então a fidelidade em relação ao PowerPoint não foi medida) e cresceu de 0 a 33 mil estrelas em 8 meses. Se for testar, baixar o binário da release, conferir `SHA256SUMS` e rodar só no CT descartável.
- Nunca abri nada no PowerPoint real: o comportamento de `normAutofit`/`fontScale` (o PowerPoint só recalcula ao editar) e a aparência exata em PowerPoint/Keynote não foram verificados.
- Os 4 suspeitos da seção (a) vêm da leitura de `pptx_deck.py` e `slides.py`; **não** rodei o fluxo em slides reais. Também não li o template oficial.
- Servidores Canva/Gamma/Google Slides: só resumos de busca. DeckGen, SlideCoder (corpo), SlideTailor e AutoPresent (código) não confirmados. SmartArt/animações no python-pptx: conhecimento prévio, não conferido na doc. Licença do pypdfium2 e do `office-templates` não verificadas.
- Estrelas medem popularidade, não qualidade: archforge (6), power-pptx (16, um mantenedor), hands-on-deck (224, último push 2026-08-04), BrandDocs (alpha) e linters de 0 estrelas devem entrar como **aviso/spike**, nunca como portão bloqueante, até serem provados nos nossos slides.

Riscos principais: (1) auto-fix que mascara conteúdo demais, quebrando a hierarquia; (2) medição com fonte errada gera falsa confiança; (3) dependência de projetos jovens de mantenedor único; (4) divergência de render entre Mac e Debian; (5) juiz visual com coerência pouco confiável: manter a aprovação humana final.

Fontes principais (acesso 2026-11-13): github.com/anthropics/skills (skills/pptx), arxiv.org/abs/2501.03936 e arxiv.org/html/2501.03936v3, github.com/icip-cas/PPTAgent, github.com/EveryInc/hands-on-deck, github.com/ferdinandobons/brand-docs, github.com/iOfficeAI/OfficeCLI, github.com/CodeHalwell/power-pptx, github.com/Love-Ash/archforge, arxiv.org/abs/2601.09487, arxiv.org/abs/2512.03042, arxiv.org/abs/2609.03109, python-pptx.readthedocs.io (charts, fit_text), support.microsoft.com (acessibilidade PowerPoint), w3.org/WAI WCAG 1.4.3, duarte.com Glance Test, packages.debian.org/bookworm/libreoffice-impress, API do GitHub/PyPI/npm.
