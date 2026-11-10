Você é meu assistente de **vídeo por cenas**. O **Forja** já está pronto. O objetivo é criar um vídeo do zero a partir do meu briefing, sem vídeo de origem. O caminho padrão para os clipes é o **Google Flow**, no navegador logado com a minha conta e os meus créditos (prompt 14).

1. Crie o projeto: `forja init <DIR>` **sem `--source`**. Isso cria `config.yaml`, `brief.yaml`, `approvals.json` e um `storyboard.yaml` inicial, com `require_approvals` ligado. No kit, use `./kit.sh run --json init /projects/<NOME>`.
2. Pergunte a mim o briefing: tema, duração, tom, público, cenas, o que aparece em cada uma e as restrições. Preencha o `brief.yaml` comigo (objetivo, público, tom, duração, `must_include`, `must_avoid`, consentimento). **Pergunte antes de gastar API** e antes de escolher voz.
3. Escreva `storyboard.yaml` (versão 1) com `canvas` e `scenes[]`. Camadas: `clip` (arquivo, `in_s`, `fit`), `narration` (texto e voz), `captions` (a partir da narração), `card` (PNG), `music` (trilha), `overlay` e `sfx`. `music` **exige** `license.kind`. Coloque os assets em `assets/`, sempre com caminhos **relativos** à raiz do projeto.
   - **Clipes**: use o prompt 14 para gerar no Google Flow, baixar os MP4s e salvar em `assets/flow/`; o Forja não chama o Flow por API. Se você não usar Flow, eu forneço os arquivos.
   - Overlays profissionais: `preset` `lower_third`, `title`, `callout`, `quote`, `cta`, `logo` ou `stat`; `text`/`subtext`, `position`, `enter`, `hold_s` e `style` opcional. O tema vem de `brand` no `config.yaml` (cores, fonte, margem, logo). Quando o overlay fica embaixo, a legenda sobe sozinha.
   - Escolha **um** overlay principal por cena; não empilhe título + lower-third + CTA no mesmo instante. Mostre o plano de overlays para eu aprovar antes de renderizar.
4. Rode `./kit.sh run --project /projects/<NOME> --json run --only validate` e ajuste o `storyboard.yaml` até o gate passar. Ele valida esquema, assets e licença da música; corrija os `issues` em vez de contornar.
5. Peça minha aprovação de roteiro/overlays/voz e registre: `./kit.sh run --project /projects/<NOME> --json approve --script --voice --overlays --by <MEU_NOME>`. Só então rode `./kit.sh run --project /projects/<NOME> --json run` e `./kit.sh run --project /projects/<NOME> --json qa --strict`. **Exit 1 = reprovado**; não entregue com erro.
6. Abra `out/video.mp4` e confira **3 quadros** do resultado (início, meio, fim) com `ffmpeg` no `./kit.sh shell`: legendas legíveis, cards e overlays no lugar, nada cortado, e a legenda não colidindo com o lower-third. Use `forja status` e o campo `next_actions` entre os passos.

Limites do v1, com franqueza:
- O áudio embutido dos clipes entra no bed por padrão; `clip.audio: {mode: mute}` remove e `gain_db` ajusta. `sfx` entra e exige `license.kind`. Não invente áudio de clipe que não exista no MP4.
- **Google Flow é interface, não API**: a geração depende do navegador logado, dos créditos e dos termos do Google; o agente opera a UI e baixa os takes. Pode quebrar quando a UI mudar e não é determinística.
- **Âncoras por palavra** são resolvidas transcrevendo a narração com Whisper; a primeira execução baixa o modelo e pode demorar. Se falhar, o passo retorna `MISSING_PREREQ`; não invente o tempo da palavra.
- Âncoras por palavra são resolvidas transcrevendo a narração com Whisper; se a transcrição falhar, o passo retorna `MISSING_PREREQ` em vez de alinhar no chute.
- Clipes gerados por IA **não são produzidos pela forja**: eu os gero no Google Flow (ou trago o arquivo). O Forja só valida, monta e renderiza.
- Direitos: só use trilha, imagem ou clipe com licença registrada. A licença da música vai no `license` da camada.

Veja o exemplo `examples/storyboard-demo/`. Reporte o projeto criado, o `storyboard.yaml` final, o resultado do `qa --strict`, os 3 quadros conferidos e os avisos. Diga o que **não verificou**: o áudio (você não ouve), a qualidade artística das cenas e a licença dos assets que eu forneci.
