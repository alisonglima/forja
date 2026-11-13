# Modelo default de peças Instagram (LEO / Lions) — documentação completa

Data: 2026-11-13. Branch: `studio/integracao`. Aprovado pelo dono na página de validação (versão 6), com a frase "Agora, sim, eu gostei".

Este documento registra o que foi feito, **por que**, como foi medido, o que deu errado, o que ainda está aberto e como reproduzir. Os números vêm de medição por pixel nos gráficos oficiais; onde algo não foi verificado, está escrito.

---

## 1. Resumo

- Existe agora uma **estrutura de dois níveis** em `estudio/modelos/`: `default/` (a referência, que as personalizações não podem alterar) e `personalizacoes/` (só configuração, herdando do default).
- O **default** reproduz a **parte artística** dos gráficos oficiais do kit Leo-Lion (overlay, faixas a 60°, cunha amarela em degradê, tipografia, posições), com o **emblema LEO** no lugar do lockup do programa. Dois formatos prontos: vertical 1080×1920 e quadrado 1080×1080.
- As páginas do dono são **só LEO e Lions**. O programa Leo-Lion não aparece no default (nem lockup, nem "Become a Leo-Lion", nem "#ProudLeoLion").
- Foram analisados os **18 vídeos oficiais** de redes sociais (14 por legenda do Vimeo, 4 por transcrição Whisper local) e os **guias de marca**. Os relatórios estão em `docs/estudio/pesquisa-videos-guias-2026-11-13/`.
- **Ainda não existe:** horizontal 1920×1080, gate de paridade automatizado, resolvedor de herança, personalizações aplicadas (só esqueletos), slot para o logo do AL. Ver seção 11.

---

## 2. Decisões do dono que governam este trabalho

| Decisão | Origem | Efeito |
|---|---|---|
| "Não reinvente a roda; no máximo, aprimore o que já temos." | Regra permanente | Base = arquivos oficiais do acervo. Só aprimorar. |
| Primeiro 1:1 com o oficial, depois criatividade | 2026-11-12/13 | Paridade medida antes de qualquer variação. |
| Modelo de referência numa pasta `default`; customizações em pastas à parte (clube, distrito, distrito LEO, distrito Lions) | 2026-11-13 | Estrutura da seção 4. |
| Nomes: "Distrito LEO LC-6" e "Distrito LC-6" (Lions) | 2026-11-13 | Pastas `distrito-leo-lc6` e `distrito-lc6`. |
| Só LEO e Lions. Do Leo-Lion, só a parte artística. | 2026-11-13 (correção) | Default sem lockup/texto do programa. Memória: `feedback_so-leo-e-lions-sem-leo-lion`. |
| Regra de equivalência do emblema (ver 5.4) | 2026-11-13 | Onde o oficial usa logo colorida → emblema LEO colorido; logo toda branca → emblema LEO todo branco, sem Alpha/Ômega e sem texto. |
| Texto de exemplo no default | 2026-11-13 | "Faça a diferença" etc. |
| Story: default a 110 px da base como o oficial; elevação só na personalização do story | 2026-11-13 | `formatos.story.elevacao_zona_segura` nos `custom.json` de marca. |
| Transcrever os 4 vídeos sem legenda | 2026-11-13 | Whisper local, seção 8. |
| Licença da fonte não é preocupação ("se o Lions Internacional usa, nós também poderemos usar") | 2026-11-12/13 | Arial instalada no CT; TTFs fora do git. |
| Nome do clube em toda peça: "LEO Clube de Taquaritinga" (LEO) e "Lions Clube de Taquaritinga" (Lions); LEO em maiúsculas em pt-BR | Regra permanente | Entra na personalização do clube, não no default. |
| Logo oficial do AL (clube e distrito) ao lado do emblema, **futuramente** | 2026-11-13 | Slot a desenhar depois (seção 9). |

---

## 3. Fontes oficiais usadas

Tudo fica no acervo local (`.work/fontes/lions/`, origem `forja-acervo`, privado). **Nenhum arquivo oficial (imagem, logo, fonte) está neste repositório.**

- Gráficos prontos do Social Media Kit Leo-Lion: `157443765` (vertical 1080×1920), `157443769` (quadrado 1080×1080), `157443764` (horizontal 1920×1080).
- Emblema LEO geral, 2 cores: `logos/Emblemas_de_Leos/109141433__Logo_rgb_Leo_2C.png` (1501×1501, área visível 1049×975).
- Guia de marca (pt e en), guia Leo e guia Leo-Lion em texto; `tokens-oficiais.json`, `tokens-submarcas.json`.
- 18 vídeos do Vimeo (`videos-vimeo-social-media/`).
- As fotos do kit oficial (convenção de Boston) **não** estão na biblioteca baixada. O default usa fotos da biblioteca como substituto.

---

## 4. Estrutura criada

```
estudio/modelos/
  README.md                       regras de herança e do que cada camada pode mudar
  default/
    templates/
      capa-vertical-oficial.html      vertical 1080x1920
      quadrado-caixa-oficial.html     quadrado 1080x1080 (caixa branca + chevrons)
    pecas.json                    4 pecas: 2 default + 2 de teste de variante de emblema
    medidas.json                  medidas do oficial (entrada do futuro gate de paridade)
  personalizacoes/
    leo/custom.json
    leo/distrito-leo-lc6/custom.json
    leo/distrito-leo-lc6/clube-taquaritinga/custom.json
    lions/custom.json
    lions/distrito-lc6/custom.json
    lions/distrito-lc6/clube-taquaritinga/custom.json
```

**Herança:** `default` → marca (`leo`/`lions`) → distrito → clube. Cada `custom.json` tem `extends` para o nível acima.

**Pode mudar numa personalização:** `nome`, `marca`, `textos`, `logos` (principal e extras), `hashtags`, `fotos`, e, no story, a elevação do bloco de texto.

**Não pode mudar:** fonte, paleta, opacidades, geometria de faixas e cunha, posição e tamanho dos elementos (tudo o que está em `medidas.json`). Quem precisar disso altera o default.

Hoje os `custom.json` são **esqueletos** (campo `status: "esqueleto"`). Não há resolvedor de herança ainda.

---

## 5. O modelo default

### 5.1 O que foi mantido do oficial (parte artística)

| Elemento | Valor medido no oficial |
|---|---|
| Fonte | Arial (Bold nos títulos, Regular nos subtítulos). Sobreposição de pixels do título vertical: Arial Bold IoU 0,83; Helvetica Bold 0,80; Helvetica Neue Bold 0,70. O guia de marca (3.5) lista Arial como fonte de sistema. |
| Faixas | 3 faixas brancas **chapadas** (sem degradê) a 60°, opacidade ≈ **0,077** (vertical 0,066 / 0,069 / 0,087; horizontal 0,076 / 0,082 / 0,077; aplicado 0,077). Bordas a **434 / 356 / 274 px** da borda direita no rodapé (vertical); **464 / 386 / 304** (horizontal). Altura de cada faixa = 1,732 × largura. |
| Cunha amarela | Cor #EBB700, **degradê**: opacidade **0,30** na borda diagonal caindo linear até ~0 em **~105 px** (vertical) / ~160 px (horizontal). Base da cunha 162 px (vertical), 192 px (horizontal). |
| Overlay vertical | Azul, **escuro no topo e claro embaixo**. Sombras da foto por altura: (13,52,113) no topo, (16,52,112), (25,63,123), (42,83,138) na base. Opacidade ≈ 0,79 no topo caindo a ≈ 0,59 na base. |
| Overlay quadrado | Azul quase plano e escuro (sombras ≈ (5,35,89)), opacidade ≈ 0,50. **Sem faixas nem cunha.** |
| Vertical 1080×1920 | Margem esquerda 110 px, inferior 110 px. Título Arial Bold **107 px**, entrelinha **112 px**. Régua amarela **520×10 px**, pontas redondas. Subtítulo **45 px / 55 px**. |
| Quadrado 1080×1080 | Caixa branca **796 px** de largura em (63,733); título Arial Bold 64 px azul; linha secundária 55 px cinza; **3 chevrons** amarelos presos ao canto inferior direito da caixa. |

### 5.2 O que foi trocado

- O lockup oficial Leo-Lion foi substituído pelo **emblema LEO**.
- O texto oficial em inglês foi substituído por um **texto de exemplo em português**.

### 5.3 Texto de exemplo

- Vertical: título "Faça a diferença"; subtítulo "Seja LEO." / "Ajude sua comunidade."
- Quadrado: título "Faça a diferença"; linha secundária "#SejaLEO" (**hashtag de exemplo**, o dono define a real).

### 5.4 Regra de equivalência do emblema

Onde o gráfico oficial usa a logo **colorida**, o default usa o emblema LEO **colorido** (2 cores, geral, sem Alpha/Ômega e sem texto, arquivo `109141433`). Onde usa a logo **toda branca**, o default usa o emblema LEO **todo branco**, sem texto.

- Vertical oficial usa a logo toda branca (`109141428 … Leo-Lion_1C_White`) → default usa o emblema LEO branco.
- Quadrado oficial usa a logo colorida com texto branco (`109141439 … Leo-Lion_3C_WhiteText`) → default usa o emblema LEO colorido.
- As duas variantes foram testadas nos dois formatos (peças `teste-vertical-colorido` e `teste-quadrado-branco`) e ambas funcionam. A página de validação mostra a comparação.

**Como o lockup oficial foi identificado:** `cv2.matchTemplate` (TM_CCORR_NORMED, com máscara do alfa) do arquivo candidato contra a região do logo no gráfico oficial, variando a escala. Vertical: `1C_White` a 280 px, correlação **0,995**. Quadrado: `3C_WhiteText` a 205 px, correlação **0,987**, com o menor erro médio absoluto (17,5 contra 22,5 da versão texto azul).

### 5.5 O emblema LEO todo branco é derivado, não oficial

A biblioteca oficial do LEO tem só versões de **2 cores** (com texto cinza, com texto branco, e o emblema geral). Não existe versão toda branca.

- Foi gerada a partir do emblema oficial `109141433`: a silhueta cinza virou branca (alfa proporcional ao quanto o pixel é cinza) e os detalhes brancos e o halo ficam vazados (transparentes). É o mesmo princípio do emblema Lions em 1 cor branca. Nenhum traço foi redesenhado.
- Arquivo: `.work/fontes/lions/logos/Derivados_LEO/Leo_1C_White_derivado.png` (fora do repositório, como todo arquivo oficial ou derivado de oficial).
- **Conflito com o guia:** o guia do LEO diz que o emblema "não pode ser reconstruído nem alterado de forma alguma" e mostra só as versões com texto cinza e texto branco. O dono pediu a versão branca e foi usada, mas **ela não está no guia**. Para segurança formal: trademarkuse@lionsclubs.org (canal indicado no guia).
- Usado o **emblema geral**, que o guia prevê para conteúdo dirigido aos dois grupos (Alpha e Ômega). A designação Alpha ou Ômega só entra se o conteúdo for exclusivo de um grupo.

### 5.6 Dimensões do emblema

Vertical: altura visível ≈ 183 px (a mesma do lockup oficial), largura 200 px (branco) / 197 px (colorido), borda esquerda visível em x ≈ 117. Quadrado: altura ≈ 134 px, largura 146 px (branco) / 144 px (colorido), posição (73,66).

### 5.7 Posições conferidas por pixel (vertical e quadrado)

| Elemento | Nossa | Oficial |
|---|---|---|
| Lockup/emblema vertical | x118–395, y1187–1368 *(medido ainda com o lockup; o emblema LEO tem outra proporção e foi alinhado pela altura)* | x118–395, y1189–1368 |
| Título (2 linhas) | 1417–1514, 1549–1606 | 1417–1512, 1546–1603 |
| Subtítulo | 1711–1742, 1766–1806 | 1711–1743, 1766–1798 |
| Caixa do quadrado | x63–858, y733–980 | x63–859, y733–981 |
| Chevrons do quadrado | x563–832, y908–1019 | x568–834, y908–1020 |

Atenção: a linha da tabela do emblema vertical foi medida na versão com o lockup oficial, antes da troca pelo emblema LEO. A posição vertical do emblema LEO foi definida pelo mesmo bloco CSS (topo em y ≈ 1187) e **não foi remedida por pixel** depois da troca. As medidas da tabela de título e subtítulo foram feitas com o texto oficial em inglês; com o texto de exemplo em português **não foram remedidas**. A segunda linha do subtítulo terminava 8 px abaixo do oficial (1806 contra 1798) e **a causa não foi investigada** (pode ser limiar de medição sobre o JPEG oficial, não deslocamento do bloco).

---

## 6. Método de medição (o que funcionou)

1. **Estimar a opacidade do overlay** pelos extremos da foto por faixa de altura (percentis de sombras e claros), não por um ponto.
2. **Estimar a opacidade de faixa e de cunha por regressão no degrau**: amostrar pixels a 4–9 px dos dois lados de cada borda e, nos três canais, `alfa = Σ d·(cor−P) / Σ (cor−P)²`, com `P` = pixel fora, `d` = dentro − fora. Milhares de pixels por borda.
3. **Perfil de profundidade da cunha**: alfa em função da distância à hipotenusa (4, 16, 28, … 100 px). Foi o que revelou o degradê.
4. **Identificar fonte por IoU** da máscara do título oficial contra o texto renderizado em cada candidata.
5. **Rodar o mesmo estimador no render nosso** (ida e volta) e comparar.
6. **Comparar perfis, não números únicos.** A cunha casava no degrau e estava errada em profundidade; o overlay casava num ponto e estava invertido.

Perfil oficial da cunha vertical (alfa × distância em px): 4 → 0,300; 16 → 0,268; 28 → 0,243; 40 → 0,202; 52 → 0,189; 64 → 0,138; 76 → 0,084; 88 → 0,053; 100 → 0,036.

---

## 7. Pipeline de renderização

- **Render:** CT 220 `lab88-forja` (`ssh forja-ct`, usuário `forja`, sem sudo). `/srv/forja/work/render-ids.sh <ids…>` roda o `check --fail-on warning` do Open Design kit 0.4.0 e exporta o PNG.
- **Workspace local de build:** `.work/peca-leo/` (`build-ws.sh`, `compose.py`, `gates.py`, `template/`, `pecas.json`). Não versionado; os templates e `pecas.json` de referência estão em `estudio/modelos/default/` e em `docs/estudio/peca-real-leo/`.
- **Fluxo:** editar o template em `estudio/modelos/default/templates/`, copiar para `.work/peca-leo/template/`, `bash build-ws.sh` (**não esconder a saída**: falha silenciosa gera render sem HTML), empacotar o workspace (`COPYFILE_DISABLE=1 tar --no-xattrs`), enviar ao CT, `render-ids.sh`, trazer `ws/exports/*.png` por `scp`, rodar `python3 -W error::RuntimeWarning gates.py evid11`.
- **Arial no CT:** passo adicionado em `scripts/pve/forja-ct.sh` que instala `/srv/forja/fonts/arial/*.ttf` em `/usr/local/share/fonts/arial` (root, na provisão). No CT atual está instalada por usuário em `~/.local/share/fonts/arial`. `fc-match Arial` → Arial. **Os TTFs não estão no git.**
- **Lint de marca (`forja/brand_lint.py`):** sem hexadecimal cru em templates (nem `#000`), paradas de gradiente só com hex da paleta ou `var(--x)` declarado com hex (sem `transparent` e sem cor de máscara), `data-od-allow="slop-glow"` na sobreposição em degradê, `regras.allow_brand_gradient: true`. Solução para degradê com alfa: `linearGradient` em SVG inline com `style="stop-color: var(--yellow); stop-opacity: …"`.
- **Marca interna das peças default:** `marca: "leo-lion"` em `pecas.json` é só o **identificador da paleta** do pipeline (azul #00338D, amarelo #EBB700, azul claro #407CCA, cinza #55565A), usado para manter o azul escuro do oficial. Não aparece em nenhuma peça. Ver pendência 11.2.

### Resultado dos gates nas 4 peças (render de 2026-11-13)

| Peça | grafia | lint de marca | zona segura | overflow | mídia | contraste mínimo |
|---|---|---|---|---|---|---|
| `default-vertical` | 0 | 0 | 0 | 0 | 0 | título 2,31 / subtítulo 2,60 |
| `default-quadrado` | 0 | 0 | 0 | 0 | 0 | título 11,3 / data 7,33 |
| `teste-vertical-colorido` | 0 | 0 | 0 | 0 | 0 | 2,31 / 2,60 |
| `teste-quadrado-branco` | 0 | 0 | 0 | 0 | 0 | 11,3 / 7,33 |

O **contraste do vertical (2,31 e 2,60) está abaixo de 3:1.** Causa provável: a foto de substituição é bem mais clara que a do oficial. Com a foto certa do kit deve melhorar, mas **não foi medido**. O preset do default vertical é `ig-capa-reels`, sem zona segura; por isso `zona=0`. Em preset `ig-story` o mesmo bloco a 110 px da base aciona o aviso de zona segura (decisão da seção 2: a elevação vive na personalização do story).

Suíte do repositório: **1792 passando, 10 ignorados**.

---

## 8. Análise dos vídeos e dos guias

Relatórios completos em `docs/estudio/pesquisa-videos-guias-2026-11-13/`:

| Arquivo | Conteúdo | Linhas |
|---|---|---|
| `an-videos-lions-01.md` | 14 vídeos com legenda: recomendações por vídeo, checklist consolidado de 55 itens, 15 itens aplicáveis à capa de Instagram | 433 |
| `an-tr-NA_442070084.md` | Instagram Basics for Your Lions Club (o mais próximo do nosso caso) | 122 |
| `an-tr-NA_285353115.md` | New Voices: guia de marketing em redes sociais | 134 |
| `an-tr-NA_408602835.md` | Getting Started on Social Media | 109 |
| `an-tr-NA_425548031.md` | Social Media 101: Facebook | 85 |
| `an-guias-lions-01.md` | Guias de marca: 212 regras em 9 seções | 322 |

### Achados relevantes para o modelo

- Os kits são feitos para **trocar só foto e texto**; a foto vai **atrás** das camadas de logo e texto.
- **Feed em 1:1 e story vertical** (cerca de 90% seguram o celular na vertical). Os feeds 4:5 de versões anteriores divergiam disso.
- 3 a 5 hashtags relevantes; título grande e em negrito; rostos de membros; foto autêntica do clube; "link na bio" em vez de link clicável; vídeo de story de 15 s.
- **Guia de marca sobre logo de distrito ou clube ao lado do emblema: o guia não trata disso.** Não há regra de co-branding, separador, proporção ou hierarquia. A única regra aplicável é o **espaço livre ao redor da assinatura, igual à altura do "L" central do emblema**; o logo extra deve ficar fora desse espaço. É proibido **reconfigurar os elementos** da assinatura, então o AL vai ao lado, nunca dentro do bloco do emblema.
- O guia **não define tamanho mínimo em pixels para tela** (só para impressão: mínimo 0,375", preferido 0,5625") nem margens de Instagram.
- **Conflitos:** frequência de posts (vídeo 9: 3–5 por dia × vídeo 11: mínimo 1 por semana); plataforma única (vídeo 7: só Facebook × vídeos 12 e New Voices: diversificar); compartilhar post de outra pessoa (Instagram Basics, [06:13] × [11:46]); 5 entre fontes de guia (paleta e tipografia do template PowerPoint × guia; "Helvetica e Arial" × página com Times no guia Leo; tradução PT de "screen back colors"; plaqueta "Leo" × "Leo-Lion" nos tokens). Nenhum muda o default.

### Transcrição dos 4 vídeos sem legenda

- Modelo: `ggml-large-v3-turbo-q5_0` do repositório público do whisper.cpp (574.041.195 bytes, tamanho igual ao informado pelo servidor), `whisper-cli`, idioma `en`, local, sem enviar áudio a nenhum serviço.
- Tempo: ~2 min por vídeo de ~31 a 58 min.
- Limite: nomes próprios e siglas podem estar errados; as lanes marcaram `[trecho incerto]` (ex.: "Lincoln.bio", "smile page", "Vengage" provavelmente Venngage). **As minutagens não foram conferidas contra a reprodução dos vídeos.**
- As transcrições em si (`.vtt`/`.txt`) **não** foram versionadas (conteúdo de terceiros). Ficam em `.work/transcricoes/`. Script: `.work/transcrever.sh`.

### Como as análises foram feitas

Lanes de pesquisa do DSH (headless, DeepSeek), uma por vídeo ou por conjunto, com spec contendo fonte, formato e regra "só o que a fala diz, com minutagem". O verificador marcou **REPROVOU** em todas só no critério `nao_vazio` (o arquivo de relatório é novo e não conta como diff); escopo, protegidos, tamanho e aceitação passaram. Os relatórios foram lidos e existem; a causa da reprovação não foi investigada.

---

## 9. Logos do AL (clube e distrito): plano

- Entram na **personalização**, ao lado do emblema principal, **nunca dentro do bloco do emblema**.
- Restrições vindas do guia: respeitar o espaço livre (altura do "L" central) em volta do emblema; não reconfigurar a assinatura; usar arte oficial e contraste suficiente.
- **O que falta:** os arquivos dos logos do AL (nenhum fornecido); decidir tamanho e posição do slot (o guia não define, então é decisão de design nossa dentro das duas restrições); medir o espaço livre no `default`.
- Os `custom.json` já têm entradas `logos.extras` com `arquivo: null` e `status: "pendente"`.

---

## 10. Histórico de erros e correções (para não repetir)

1. **Overlay invertido** (escuro embaixo): achado pelas sombras por faixa de altura; corrigido.
2. **Cunha chapada** onde o oficial é degradê: o dono apontou; o perfil de profundidade mostrou queda linear; refeita com `stop-opacity` em SVG porque o lint proíbe `transparent`.
3. **Hex cru `#000` numa máscara** derrubou o `compose`; um `>/dev/null` no `build-ws.sh` escondeu o erro e produziu render sem HTML (`check=1`). Regra: nunca esconder a saída do build.
4. **Fonte errada** (Liberation Sans no lugar de Arial): identificada por IoU; o CT não tinha sudo, então Arial foi instalada no diretório do usuário.
5. **Afirmações de "reproduzido" erradas várias vezes.** O olhar do dono estava certo todas as vezes. Regra: medir exatamente o elemento que o dono aponta, por perfil.
6. **Escopo de marca errado (13/11):** o default foi feito como cópia do gráfico Leo-Lion inteiro, com o lockup e o texto do programa, removendo o emblema LEO. Decisão minha, sem consultar. Corrigido nesta versão; ver memória `feedback_so-leo-e-lions-sem-leo-lion`.
7. **`find /` na raiz** rodando sem parar foi interrompido; evitar buscas na raiz.
8. **Caminho relativo de spec** no `dsh-delegate.sh` é resolvido dentro do repositório-alvo (`.work/specs: No such file`): usar caminho absoluto.
9. **Monitor com array associativo** foi barrado pela verificação de segurança do shell; reescrito com variáveis simples.

---

## 11. Pendências

### 11.1 Próximos passos já combinados
1. **Horizontal 1920×1080**: a largura de 1080 px está fixa nos templates, no `compose.py` (`--mx`) e no `render-ids.sh --width 1080`. Precisa ser parametrizada.
2. **Gate de paridade automatizado**, a partir do `medidas.json`: perfil de profundidade da cunha, faixas de altura do overlay, cada degrau das faixas, caixas de lockup/título/régua/subtítulo, com o mesmo estimador no oficial e no render. Deve ser escrito por **outra lane** que não a do executor da migração, e com o contrato de teste antes.
3. **Resolvedor de herança** e validação de que `custom.json` não sobrescreve medidas.
4. **Personalizações**: LEO → Distrito LEO LC-6 → LEO Clube de Taquaritinga; Lions → Distrito LC-6 → Lions Clube de Taquaritinga. A personalização do story aplica a elevação do bloco de texto (valor a medir com o gate de zona segura).
5. **Slot do logo do AL** (seção 9).
6. Medir e converter os demais gráficos oficiais um a um para o `default`: horizontal, Lions, LEO em azul claro.

### 11.2 Perguntas abertas ao dono
- **Paleta do default LEO:** manter o azul escuro do oficial ou usar a paleta do LEO do guia (azul claro, cinza, verde, amarelo)? Hoje o default mantém o azul escuro.
- **Degradê da cunha:** o dono disse que "melhorou um pouco, mas ainda não está perfeito" e ainda não disse o que vê diferente (intensidade do amarelo, comprimento do degradê ou posição). A cunha **não foi remedida** na versão atual.
- **Hashtag oficial** da página (a atual é exemplo).

### 11.3 Verificações pendentes e riscos conhecidos
- Contraste do vertical abaixo de 3:1 com a foto de substituição (seção 7).
- Emblema LEO branco é derivado, fora do guia (seção 5.5); confirmar com a sede se for publicar em escala.
- Posição do emblema LEO no vertical não foi remedida por pixel depois da troca (seção 5.7).
- Fotos de exemplo da biblioteca: direitos de imagem e presença de menores **não revisados**.
- Transcrições Whisper: minutagem não conferida contra a reprodução.
- Restauração de backup do CT não testada; reserva DHCP do CT 220 pendente (precisa `/export` de backup do MikroTik e autorização).
- Planos antigos ainda abertos: melhoria do PPTX (5 slides), modelos de deck gráfico/tabela/equipe não suportados.

---

## 12. Commits deste trabalho (branch `studio/integracao`)

| Commit | Conteúdo |
|---|---|
| `a835ed5` | Métricas medidas pixel a pixel nos gráficos oficiais (título, régua, caixa, chevrons, overlay) |
| `4cc93f1` | Faixas 0,077 e cunha medidas; geometria vertical; Arial como fonte |
| `b2ea2c2` | Overlay escuro no topo e claro embaixo; bloco ancorado a 110 px da base |
| `2c07a82` | Cunha amarela em degradê (0,30 → 0 em 105 px) |
| `0c30e95` | Estrutura `estudio/modelos/` (default + personalizações), `medidas.json` |
| `8e9d3f6` | Correção: default sem Leo-Lion, emblema LEO (branco/colorido), texto de exemplo, templates renomeados |
| (este) | Documentação detalhada e relatórios de pesquisa (vídeos e guias) |
