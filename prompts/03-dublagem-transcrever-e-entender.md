Você é meu assistente de dublagem. O **Forja** já está pronto (`./kit.sh doctor` passou). O vídeo original é `<CAMINHO_DO_VIDEO>`.

Ciclo desta etapa: `init` → `transcribe` → `frames` → `cues.json` → `check` → `voices` → `run` → `qa --strict`. Nesta etapa fazemos os dois primeiros.

1. Crie o projeto: `./kit.sh new <NOME> <CAMINHO_DO_VIDEO>`. Isso copia o vídeo para `projects/<NOME>/input/source.mp4`, mede duração/resolução/fps e grava `projects/<NOME>/config.yaml`.
2. Pergunte-me **qual trecho devo dublar** (início e duração em segundos). Se eu quiser cortar o começo, ajuste `input.start` e `input.duration` no `config.yaml`. Todos os tempos seguintes são **relativos ao início do trecho**.
3. Rode `./kit.sh run --project /projects/<NOME> --json transcribe`. A primeira execução baixa o modelo de transcrição (cerca de 1,6 GB, uma vez só). O resultado fica em `projects/<NOME>/work/transcript.json` (segmentos e palavras com tempo).
4. Rode `./kit.sh run --project /projects/<NOME> --json status` e leia `next_actions` para confirmar o próximo passo; não pule a ordem.
5. Leia o `transcript.json` e entregue um **resumo editorial** em português: quem parece falar em cada trecho, o tom, números e nomes próprios (que não podem ser traduzidos errado), palavras que o transcritor pode ter ouvido errado (marque as duvidosas) e quantos minutos de fala efetiva existem.
6. **Não traduza ainda.** Termine perguntando o que devo confirmar (nomes, cargos, siglas).

Regras: tempos em segundos; não invente falas que não estão no transcript; use `forja status` (no kit, `./kit.sh run --project /projects/<NOME> --json status`) e o campo `next_actions`. Reporte o caminho do projeto, a duração do trecho, o resumo editorial e as dúvidas. Diga o que **não verificou**: a qualidade da transcrição contra o áudio (você não ouve) e a identificação de falantes, que vem no próximo prompt.
