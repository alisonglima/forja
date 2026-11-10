Você é meu assistente de instalação. Objetivo: deixar o **Docker** funcionando nesta máquina para eu rodar o **Forja**. Não instale nada além do necessário e **peça minha confirmação antes de qualquer comando que exija administrador/sudo ou reinicie o computador**.

Passos:
1. Descubra meu sistema (Windows 10/11, Linux ou macOS), a arquitetura (`x86_64`/`arm64`) e a RAM livre. O kit precisa de **8 GB de RAM** (16 GB é melhor) e **25 GB livres em disco**. Se faltar, pare e me diga.
2. Verifique se já existe Docker: `docker --version` e `docker compose version`. Se ambos funcionarem, pule para o passo 5.
3. Instale:
   - **Windows**: Docker Desktop com backend **WSL 2** (peça para eu habilitar a virtualização na BIOS se `systeminfo` indicar que está desligada). Depois de instalar, abra o Docker Desktop e espere o ícone ficar verde.
   - **Linux**: Docker Engine + plugin Compose pelo repositório oficial da minha distribuição (docs.docker.com/engine/install). Adicione meu usuário ao grupo `docker` e me avise que preciso sair e entrar na sessão.
   - **macOS**: Docker Desktop (Intel). Em Apple Silicon o kit roda emulado em `amd64` (mais lento); o alvo suportado é `x86_64`.
4. Em Docker Desktop: Settings → Resources → dê pelo menos **4 CPUs e 8 GB de memória**.
5. Teste: `docker run --rm hello-world` e `docker compose version`.
6. Confirme a arquitetura do daemon: `docker info --format '{{.OSType}}/{{.Architecture}}'`. O esperado é `linux/x86_64`.

Critério de pronto: os dois testes do passo 5 passam. Reporte versão do Docker, versão do Compose, arquitetura, RAM/CPU/disco e qualquer aviso. Diga o que **não verificou** — em especial o pipeline do kit, que só será testado no prompt `01-preparar-kit.md`.
