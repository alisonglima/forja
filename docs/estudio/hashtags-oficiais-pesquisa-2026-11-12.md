# Hashtags oficiais do Lions e do LEO — pesquisa 12/11/2026

Pesquisa para o kit do **LEO Clube de Taquaritinga** e do **Lions Clube de Taquaritinga**. Base: `8ce0c977`. Todas as fontes foram abertas em **12/11/2026**. A lista canônica está em `brands/leo-lions/hashtags.json` (schema `forja-brand-hashtags/v1`).

**Método.** Li as notas e transcrições do acervo local e páginas públicas do Distrito LC-6 e do LEO Clube Brasil. No acervo, rodei `grep -rhoE "#[A-Za-zÀ-ú0-9_]{3,}" --include=*.md --include=*.txt` e contei por arquivo de origem. Códigos de cor em hexadecimal (`#00338D`, `#EBB700` etc.) foram descartados: não são hashtags. No site do LC-6, usei a busca interna e a API REST pública do próprio WordPress para ler o conteúdo integral dos posts; a página humana correspondente também foi aberta (HTTP 200). Não usei proxy, leitor de terceiros, cache, tradutor, espelho nem HTML de buscador.

## 1. Lista canônica

| Tag | Marca | Fonte | Vezes | Status |
|---|---|---|---|---|
| `#WeServe` | Lions e LEO | `videos-vimeo-social-media/analise/408602835/notas.md`; [LC-6 5333](https://distritolc6.org.br/acontece-no-distrito/16-de-abril-dia-nacional-do-leonismo/); [LC-6 22866](https://distritolc6.org.br/acontece-no-distrito/lc-de-sao-jose-do-rio-preto-juventude-cartinhas-do-papai-noel-2025/) | 15 (13 acervo + 2 web) | verificado |
| `#LionsClub` | Lions e LEO | `videos-vimeo-social-media/analise/408602835/notas.md`; `videos-vimeo-social-media/analise/442070084/notas.md` | 10 (acervo) | verificado |
| `#LionsGoGreen` | Lions | [LC-6 15979](https://distritolc6.org.br/acontece-no-distrito/noticias-de-lions-internacional-para-os-clubes/); `videos-vimeo-social-media/analise/909166997/notas.md` | 6 (5 acervo + 1 web) | verificado |
| `#LionsFightHunger` | Lions | `videos-vimeo-social-media/analise/564738364/notas.md` | 2 (acervo) | a-confirmar |
| `#LionsFightDiabetes` | Lions | `videos-vimeo-social-media/analise/564738364/notas.md` | 2 (acervo) | a-confirmar |
| `#LDUN` | Lions | `videos-vimeo-social-media/analise/564738364/notas.md` | 2 (acervo) | verificado |
| `#ThankYouLions` | Lions | `videos-vimeo-social-media/analise/564738364/notas.md` | 2 (acervo) | a-confirmar |
| `#PeacePoster` | Lions | `videos-vimeo-social-media/analise/564738364/notas.md` | 2 (acervo) | verificado |
| `#LCICon2021` | Lions | `videos-vimeo-social-media/analise/564738364/notas.md` | 2 (acervo) | verificado, evento vencido |
| `#LCICon2023` | Lions | `videos-vimeo-social-media/analise/909166997/notas.md` | 2 (acervo) | a-confirmar, evento vencido |
| `#LionsCon24` | Lions | `videos-vimeo-social-media/analise/909166997/notas.md` | 2 (acervo) | verificado, evento vencido |
| `#leoclub` | LEO | `videos-vimeo-social-media/analise/565616352/notas.md` | 1 (acervo) | verificado |
| `#socialservice` | LEO | `videos-vimeo-social-media/analise/565616352/notas.md` | 1 (acervo) | verificado |
| `#altruism` | LEO | `videos-vimeo-social-media/analise/565616352/notas.md` | 1 (acervo) | verificado |
| `#LCIF` | Lions | [LC-6 16765](https://distritolc6.org.br/acontece-no-distrito/lcsjriopretosullcif-projeto-fome-casa-apoio-amor-e-fe/); [LC-6 5333](https://distritolc6.org.br/acontece-no-distrito/16-de-abril-dia-nacional-do-leonismo/) | 2 (web) | verificado |
| `#DistritoLC6` | Lions (local) | [LC-6 16765](https://distritolc6.org.br/acontece-no-distrito/lcsjriopretosullcif-projeto-fome-casa-apoio-amor-e-fe/) | 1 (web) | verificado |
| `#WeServer` | Lions (local) | [LC-6 16765](https://distritolc6.org.br/acontece-no-distrito/lcsjriopretosullcif-projeto-fome-casa-apoio-amor-e-fe/) | 1 (web) | verificado |

**Resumo:** 17 tags na lista, **13 verificadas** e **4 a-confirmar**. As a-confirmar são `#LionsFightHunger`, `#LionsFightDiabetes` e `#ThankYouLions` (grafia inferida da fala nos vídeos) e `#LCICon2023` (transcrição duvidosa e evento vencido).

**Leitura da tabela.** “Acervo” é contagem de ocorrências nos arquivos `.md`/`.txt` do acervo local, não número de posts. “Web” é contagem nas páginas do LC-6 que abri. `#WeServe` aparece no acervo como `#WeServe` e `#weserve`; a contagem soma as duas grafias. `#LionsClub` soma `#LionsClub` e `#lionsclub`. As fontes de acervo são relativas à raiz do acervo local (`.work/fontes/lions/`); os caminhos no JSON não incluem essa raiz.

## 2. O que ficou fora da lista

| Tag | Vezes | Por que não entrou |
|---|---|---|
| `#FYP` | 3 (acervo) | Tag ampla de descoberta. O vídeo 909166997 [05:20] manda evitar genéricas/amplas; o 565616352 [12:40] só a registra como tática datada. Fica em `genericas_evitar`, não na lista. |
| `#ForYouPage` | 1 (acervo) | Mesma tag por extenso; mesma decisão. |
| `#WindyCityLions` | 2 (acervo) | Exemplo de hashtag de clube dado no vídeo 408602835 [15:08]; não é hashtag oficial global nem do clube de Taquaritinga. |
| `#AflacKickoff` | 1 (acervo) | Hashtag de evento de 2023, fora do ciclo atual e sem confirmação de vigência. |
| `#LionsGrow` / `#Mission1.5` | 1 / 1 (acervo) | A própria nota marca a transcrição como duvidosa [03:59–04:05]; não há grafia confirmada. |
| `#LionsClubsInternacional`, `#lionsbrasil`, `#SightFirst`, `#Diabetes`, `#Environment`, `#Hunger`, `#ChildhoodCancer` | 1 cada (web) | Aparecem em página do LC-6, mas são amplas, localizadas ou nomes de causa sem campanha vigente confirmada; não foram adotadas como padrão do kit. |

Não há hashtag local de Taquaritinga com fonte aberta. **Não invente** `#LionsClubeTaquaritinga`, `#LEOTaquaritinga` ou equivalente: se o clube criar uma, pesquise o feed, confirme que ninguém usa e registre a fonte antes de incluir.

## 3. Não acessível / não verificado

- **lionsclubs.org:** a página `https://www.lionsclubs.org/en/social-media` retornou **HTTP 403** com bloqueio Cloudflare (“Sorry, you have been blocked”). **Não acessível**; não insisti nem usei espelho, cache ou leitor de terceiros.
- **Instagram e Facebook:** exigem login para ver posts e páginas de hashtag. **Não acessíveis** nesta pesquisa; não há contagem de posts institucionais nessas redes.
- **Busca web:** a ferramenta `web_search` estava sem chave de API (`DEEPSEEK_API_KEY`). Registrado; a descoberta foi feita por URLs conhecidas e pela busca interna do site do LC-6.
- **LEO Clube Brasil:** `https://leoclubebrasil.com.br/`, `/sobre`, `/noticias` e `/documentos` abriram (HTTP 200), mas **não trazem hashtags**. A página `/documentos` estava sem documentos listados. Não é “não acessível”; é ausência de evidência.
- **Páginas humanas do LC-6:** abriram com HTTP 200, mas o extrator truncou o corpo. O conteúdo integral foi lido pela API REST pública do mesmo site (`/wp-json/wp/v2/posts/<id>`), sem proxy. As URLs citadas na tabela são as páginas humanas correspondentes.
- **Grafias a-confirmar:** `#LionsFightHunger`, `#LionsFightDiabetes` e `#ThankYouLions` foram inferidas da fala em inglês; `#LCICon2023` foi inferida de “LC Icon 2023”. Nenhuma foi confirmada em página oficial aberta nesta data.
- **Vigência:** não confirmei qual é a campanha oficial do ano em 2026, nem se `#LionsGoGreen`, `#LDUN` e as campanhas de causa continuam sendo promovidas pela LCI. As tags de evento `#LCICon2021`, `#LCICon2023` e `#LionsCon24` estão vencidas e não devem ser usadas em posts novos.
- **Regra 3–5:** a faixa vem do vídeo 909166997 [05:28] e das notas; não foi confirmada em página oficial aberta. O `formats.json` da casa já usa `max_hashtags: 5`; o mínimo de 3 ainda não tem gate automático.

## 4. Recomendação para Taquaritinga

**Lions Clube de Taquaritinga — 3 a 4 tags por feed:**

1. `#WeServe` (verificado) — marca global, sempre.
2. `#LionsClub` (verificado) — marca global, sempre.
3. Uma tag de causa, só se o post for da causa:
   - `#LionsGoGreen` (verificado) para meio ambiente;
   - `#LionsFightHunger` (**a-confirmar**) para fome;
   - `#LionsFightDiabetes` (**a-confirmar**) para diabetes.
4. Opcional: `#LCIF` (verificado) quando o projeto tiver subsídio da LCIF; `#DistritoLC6` só em post institucional do distrito, não no clube.

**LEO Clube de Taquaritinga — 3 a 4 tags por feed:**

1. `#leoclub` (verificado) — identidade LEO.
2. `#socialservice` (verificado) — serviço comunitário.
3. `#WeServe` (verificado) — ponte com o Lions.
4. Opcional: `#LionsClub` (verificado) em ação conjunta com o clube padrinho; `#altruism` (verificado) é alternativa, mas ampla.

**As 5 tags-padrão do kit:** `#WeServe`, `#LionsClub`, `#LionsGoGreen`, `#leoclub`, `#socialservice`. Para campanha de fome ou diabetes, troque `#LionsGoGreen` por `#LionsFightHunger` ou `#LionsFightDiabetes`, marcando **a-confirmar** até a grafia ser validada em fonte oficial.

**Regras de uso:**

- 3 a 5 tags por post; nunca 6 ou mais.
- Toda tag precisa ter relação explícita com o tema; não use `#PeacePoster` em post de fome, por exemplo.
- Não use tag de evento/ano vencido (`#LCICon2021`, `#LCICon2023`, `#LionsCon24`) sem evento vigente.
- `#WeServer` é variante local do Distrito LC-6, não substitui `#WeServe`; `#DistritoLC6` é tag de distrito, não de clube.
- `#FYP` e `#ForYouPage` não entram na lista: são amplas e não são marca.
- Se o clube criar uma tag própria, ela precisa ser curta, pesquisada antes e registrada com fonte; sem fonte, não entra no JSON.

## 5. Arquivos e verificação

- `brands/leo-lions/hashtags.json` — lista canônica, 17 tags, `minimo: 3`, `maximo: 5`, `genericas_evitar` com `#FYP` e `#ForYouPage`.
- `docs/estudio/hashtags-oficiais-pesquisa-2026-11-12.md` — esta pesquisa.
- Aceitação: `test -s docs/estudio/hashtags-oficiais-pesquisa-2026-11-12.md && python3 -c "import json;d=json.load(open('brands/leo-lions/hashtags.json'));assert d['schema']=='forja-brand-hashtags/v1' and d['tags']"`.
- `git status --short` deve mostrar somente estes dois arquivos; nenhum arquivo de `scripts/`, `tests/` ou `forja/` foi tocado.
