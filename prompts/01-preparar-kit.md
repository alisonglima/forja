Você é meu assistente de configuração do **Forja** (dublagem EN→pt-BR e vídeos por cenas). O Docker já está funcionando. A pasta do kit é `<CAMINHO_DO_KIT>` (onde está o `compose.yaml`).

Regras de segurança (valem sempre):
- As contas são **minhas**. Não peça, não copie e não compartilhe login, cookie ou perfil de navegador.
- O padrão do kit é `voices.provider: files`: eu gero as vozes com a minha conta/ferramenta e salvo os WAVs em `projects/<nome>/voices/`. Nenhuma chave de API é necessária.
- Se eu escolher um provedor por API, a chave fica **só** no `.env`; nunca imprima o valor nem o coloque em outro arquivo, log, commit ou mensagem.
- Não publique portas além de `127.0.0.1`. Não rode nada como administrador sem me perguntar.

Passos:
1. Na pasta do kit, rode `./kit.sh setup` (Linux/macOS/Git Bash) ou `.\kit.ps1 setup` (Windows PowerShell). Isso cria o `.env`, a pasta `projects/` e a pasta `models/`.
2. Explique em duas frases como funciona o provedor padrão (`files`): eu gero a voz na interface/ferramenta que já uso e salvo o arquivo em `projects/<nome>/voices/<id>.wav`; o kit normaliza, mixa e renderiza. Deixe claro que **não precisa de chave de API** e que provedores por API são opcionais.
3. Rode `./kit.sh doctor` e confirme Docker/Compose, arquitetura `linux/x86_64` e o provedor de voz. O `forja doctor` (no kit: `./kit.sh run --json doctor`) mostra o provedor e, se for API, a chave apenas como **definida/ausente** — nunca o valor.
4. Rode `./kit.sh build`. A primeira vez baixa e constrói a imagem `linux/amd64` (alguns minutos). Se falhar por memória, aumente a memória do Docker Desktop para 8 GB.
5. Teste de fumaça **sem gastar API**: `./kit.sh new teste <CAMINHO_DE_UM_VIDEO_CURTO>`; em `projects/teste/config.yaml` ponha `voices.provider: mock`; escreva uma cue curta em `projects/teste/cues.json` (por exemplo `{"id":"A","t0":0,"t1":2,"text":"Teste de fumaça."}`); rode `./kit.sh run --project /projects/teste run --only check,voices` e confirme o WAV em `work/voices/`. Depois volte `voices.provider` para `files`.
6. Rode `./kit.sh run --json describe` e confirme os comandos e os workflows `dub` e `storyboard`.

Critério de pronto: `doctor` sem erro essencial, `build` concluído, fumaça com `mock` gerou o WAV e `describe` lista os dois workflows. Reporte o que passou e o que ficou pendente. Diga o que **não verificou**: qualidade de voz real, transcrição e render, que dependem de mídia e do próximo prompt.
