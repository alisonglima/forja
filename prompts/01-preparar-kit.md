Você é meu assistente de configuração do **Forja** (dublagem EN→pt-BR e vídeos por cenas). O Docker já está funcionando. A pasta do kit é `<CAMINHO_DO_KIT>` (onde está o `compose.yaml`).

Regras de segurança (valem sempre):
- As contas são **minhas**. Não peça, não copie e não compartilhe login, cookie ou perfil de navegador.
- O padrão do kit é `voices.provider: google_ai_studio`: eu gero as vozes na interface web do Google AI Studio com a minha conta e salvo os WAVs em `projects/<nome>/voices/`. Nenhuma chave de API é necessária.
- Se eu escolher um provedor por API, a chave fica **só** no `.env`; nunca imprima o valor nem o coloque em outro arquivo, log, commit ou mensagem.
- Não publique portas além de `127.0.0.1`. Não rode nada como administrador sem me perguntar.

Passos:
1. Na pasta do kit, rode `./kit.sh setup` (Linux/macOS/Git Bash) ou `.\kit.ps1 setup` (Windows PowerShell). Isso cria o `.env`, a pasta `projects/` e a pasta `models/`.
2. Explique os caminhos de voz e me ajude a escolher: **Google AI Studio** (`google_ai_studio`, padrão: eu gero na interface web e salvo `projects/<nome>/voices/<id>.wav`), **Piper local** (`piper`, sem conta/API, voz pt-BR na imagem), **arquivos** (`files`, qualquer WAV meu) ou **Gemini API** (`gemini`, opcional com a minha chave). O padrão é AI Studio; se eu pedir offline, use Piper. Nenhum deles exige chave por padrão.
2b. Explique que o `forja init` cria `brief.yaml` e `approvals.json` e liga `project.require_approvals`: eu preencho objetivo/público/tom e aprovo roteiro/voz/overlays antes do render.
3. Rode `./kit.sh doctor` e confirme Docker/Compose, arquitetura `linux/x86_64` e o provedor de voz. O `forja doctor` (no kit: `./kit.sh run --json doctor`) mostra o provedor; no AI Studio/files/piper não há chave. Se eu optar por API, a chave aparece apenas como **definida/ausente** — nunca o valor.
4. Rode `./kit.sh build`. A primeira vez baixa e constrói a imagem `linux/amd64` (alguns minutos). Se falhar por memória, aumente a memória do Docker Desktop para 8 GB.
5. Teste de fumaça **sem gastar API**: `./kit.sh new teste <CAMINHO_DE_UM_VIDEO_CURTO> --no-require-approvals` (se o wrapper não aceitar, crie com `forja init`); em `projects/teste/config.yaml` ponha `voices.provider: mock`; escreva uma cue curta em `projects/teste/cues.json` (por exemplo `{"id":"A","t0":0,"t1":2,"text":"Teste de fumaça."}`); rode `./kit.sh run --project /projects/teste run --only check,voices` e confirme o WAV em `work/voices/`. Depois volte `voices.provider` para o caminho escolhido.
6. Rode `./kit.sh run --json describe` e confirme os comandos e os workflows `dub` e `storyboard`.

Critério de pronto: `doctor` sem erro essencial, `build` concluído, fumaça com `mock` gerou o WAV e `describe` lista os dois workflows. Se eu escolhi `piper`, confirme com um cue real que o WAV tem fala (você não ouve; eu ouço). Reporte o que passou e o que ficou pendente. Diga o que **não verificou**: qualidade de voz real, transcrição e render, que dependem de mídia e do próximo prompt.
