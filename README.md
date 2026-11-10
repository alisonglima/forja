# Forja

**Vídeo com voz e legenda, operado pelo seu agente.** Dublagem EN→pt-BR e vídeos por cenas a partir de um `storyboard.yaml`, com as **suas contas** e sem exigir chave de API.

[![CI](https://github.com/alisonglima/forja/actions/workflows/ci.yml/badge.svg)](https://github.com/alisonglima/forja/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-2ea44f.svg)](https://alisonglima.github.io/forja/)

A **forja** é uma CLI (`forja`, `python -m forja`) e um kit Docker para gerar vídeos com agentes de IA. Ela faz o trabalho determinístico — transcrever, montar a linha do tempo, mixar, renderizar e verificar o resultado — e deixa o julgamento (texto, voz, consentimento) para você.

- **Dublar**: transcreve o vídeo, adapta o texto para pt-BR, usa as vozes que você gerou, mixa com ducking, queima a legenda e passa um gate de qualidade.
- **Criar por cenas**: monta um vídeo do zero com clipes, narração, cards, trilha e legendas.
- **Para agentes**: todo comando aceita `--json`, `describe`, `status` com `next_actions`, cache por hash, QA como gate e códigos de saída `0..5`.

## Por que sem chave de API?

O padrão é `voices.provider: files`: **você gera as vozes com a conta e a ferramenta que já usa** (a interface web do seu provedor, um estúdio local, um serviço que você assina) e salva os arquivos em `projects/<nome>/voices/<id>.wav`. O kit valida o WAV, normaliza, mixa e renderiza. Nenhuma conta é compartilhada e nenhuma chave é obrigatória.

Provedores por API são **opcionais**: `voices.provider: gemini` continua disponível para quem quiser automatizar a síntese com a própria chave. O contrato de provedores é extensível (`forja/registry.py`, entry points) para STT, TTS, render e clipe.

## Requisitos

- Docker com Compose v2 (Windows com WSL2, Linux ou macOS).
- Máquina **x86_64** (o alvo da imagem é `linux/amd64`; em Apple Silicon roda emulado).
- 8 GB de RAM (16 GB é melhor) e 25 GB livres.
- A imagem do pipeline ocupa cerca de 1,8 GB; o navegador opcional acrescenta ~2,6 GB.
- Internet no primeiro `build`, para baixar o modelo de transcrição uma vez, e para o provedor de voz que você escolher.

## Comece em 5 passos

1. **Prepare o kit**:
   ```bash
   ./kit.sh setup
   ```
2. **Confira o ambiente**:
   ```bash
   ./kit.sh doctor
   ```
3. **Construa a imagem**:
   ```bash
   ./kit.sh build
   ```
4. **Ensine o seu agente**: copie o prompt `prompts/02-instalar-skill-no-seu-agente.md` para ele.
5. **Peça o vídeo**: use `prompts/03-dublagem-transcrever-e-entender.md` para dublar ou `prompts/08-video-por-cenas.md` para criar por cenas. O agente conduz o ciclo `status → próximo passo → run → qa --strict`.

No modo padrão, o agente pede que você gere as vozes na interface do seu provedor (com a sua conta) e salve os WAVs em `projects/<nome>/voices/`. O prompt `06-dublagem-elenco-e-vozes.md` explica o formato e o teste barato de elenco.

## Documentação

O guia completo, offline e copiável está em **[alisonglima.github.io/forja](https://alisonglima.github.io/forja/)** (fonte em [`docs/index.html`](docs/index.html)). Ele cobre:

- visão geral e o ciclo de trabalho;
- modo conta/navegador e modo API opcional;
- arquitetura e o que sai da sua máquina;
- os 14 prompts na ordem, com botão de copiar;
- segurança, licenças, consentimento e aviso de voz sintetizada;
- problemas comuns e códigos de saída.

## Comandos do kit

| Comando | O que faz |
|---|---|
| `./kit.sh setup` | Cria `.env`, gera a senha do navegador, cria `projects/` e `models/`. |
| `./kit.sh doctor` | Confere Docker, Compose, arquitetura, disco e o provedor de voz. |
| `./kit.sh build` | Constrói a imagem `forja:0.1` (linux/amd64). |
| `./kit.sh new <nome> <vídeo>` | Cria `projects/<nome>/` e roda `forja init` com o vídeo. |
| `./kit.sh run <args>` | Roda a CLI no container, ex.: `./kit.sh run --project /projects/meu --json status`. |
| `./kit.sh shell` | Abre um shell no container. |
| `./kit.sh browser-up` / `browser-down` / `browser-reset` | Chromium opcional em container, para logar na sua conta e usar a interface web. |

## Segurança

- **Sem chave obrigatória.** No modo `files`, nenhuma credencial de TTS é necessária; o `.env` guarda a senha da tela do navegador (quando usada) e ajustes do container.
- Se você optar por um provedor por API, a chave fica só no `.env` (0600 no Linux/macOS; no Windows, restrinja a pasta do kit à sua conta) e nunca é impressa em log ou `--json`.
- O container roda com o seu UID/GID (nunca root), `cap_drop: ALL` e `no-new-privileges`.
- O navegador opcional escuta **somente** em `127.0.0.1` (`3001` para a tela, `9222` para o CDP) e exige senha. O login é feito dentro do ambiente final; não copie perfis entre máquinas.
- Leia `prompts/12-consentimento-e-aviso.md` antes de publicar: direitos, consentimento e o aviso de voz sintetizada por IA.

## Licenças

O kit é distribuído sob a **MIT License** (veja [`LICENSE`](LICENSE)). Dependências de terceiros e suas licenças estão em [`THIRD_PARTY.md`](THIRD_PARTY.md). O Remotion é gratuito para indivíduos e empresas de até 3 pessoas; acima disso, verifique a licença comercial vigente.

## Contribuindo

Issues e pull requests são bem-vindos. Leia [`CONTRIBUTING.md`](CONTRIBUTING.md) e [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Para reportar uma vulnerabilidade, use o canal privado descrito em [`SECURITY.md`](SECURITY.md).

## Status

Versão **0.1.0**. O que está pronto e o que está no roadmap: [`docs/ROADMAP.md`](docs/ROADMAP.md). O contrato técnico completo está em [`DESIGN.md`](DESIGN.md).
