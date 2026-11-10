# Forja

**Vídeo com voz e legenda, operado pelo seu agente.** Dublagem EN→pt-BR e vídeos por cenas a partir de um `storyboard.yaml`, com as **suas contas** ou **voz local**, sem exigir chave de API.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-2ea44f.svg)](https://alisonglima.github.io/forja/)

A **forja** é uma CLI (`forja`, `python -m forja`) e um kit Docker para gerar vídeos com agentes de IA. Ela faz o trabalho determinístico — transcrever, montar a linha do tempo, mixar, renderizar e verificar o resultado — e deixa o julgamento (texto, voz, overlays, consentimento) para você.

- **Dublar**: transcreve o vídeo, adapta o texto para pt-BR, usa as vozes que você gerou ou a voz local, mixa com ducking, queima a legenda e passa um gate de qualidade.
- **Criar por cenas**: monta um vídeo do zero com clipes, narração, cards, overlays, trilha e legendas.
- **Overlays profissionais**: lower-third, título, callout, citação, CTA, logo e estatística, com tema de marca e posição/entrada/saída por camada.
- **Para agentes**: todo comando aceita `--json`, `describe`, `status` com `next_actions`, cache por hash, QA como gate e códigos de saída `0..5`.
- **Humano no comando**: `brief.yaml` registra objetivo/público/tom; `forja approve` registra a aprovação humana antes do render.

## Voz: três caminhos

| Provider | Precisa de conta/API? | Quando usar |
|---|---|---|
| `files` (padrão) | Não para o kit; você usa a sua conta/ferramenta | Você quer a sua voz/elenco e já tem um fluxo de TTS. Salve `voices/<id>.wav`. |
| `piper` | Não | Narração local neural, sem rede, com o modelo pt-BR incluído na imagem. |
| `gemini` | Sim, opcional | Automação por API com a sua chave; não é o caminho padrão. |

O provider `files` valida o WAV, normaliza, mixa e renderiza. O `piper` roda dentro da imagem (`piper-tts` + voz `pt_BR-faber-medium`, CC0/MIT). Nenhuma conta é compartilhada e nenhuma chave é obrigatória.

## Overlays

Cada camada `overlay` tem um `preset` e, opcionalmente, `text`, `subtext`, `position`, `enter`, `hold_s` e `style`:

```yaml
- type: overlay
  preset: lower_third
  text: "Ana Silva"
  subtext: "Diretora de produto"
  position: bottom-left
  enter: {anchor: scene_start, offset_s: 0.6}
  hold_s: 3.5
```

Presets: `lower_third`, `title`, `callout`, `quote`, `cta`, `logo` e `stat`. O tema vem de `brand` no `config.yaml` (cores, fonte, margem segura, logo); cada overlay pode sobrescrever `style` (cores, fonte, tamanho, raio, opacidade, largura, alinhamento). Quando um overlay fica na parte de baixo, a legenda sobe automaticamente para não colidir.

## Brief e aprovação humana

`forja init` cria `brief.yaml` e `approvals.json` e liga `project.require_approvals`. O humano preenche o brief (objetivo, público, tom, duração, restrições, consentimento); o agente escreve roteiro/storyboard/overlays e pede aprovação:

```bash
forja approve --script --voice --overlays --by "Ana"
```

O render falha com `GATE_FAILED` enquanto as aprovações exigidas não existirem. Para um teste local sem gate, use `forja init --no-require-approvals`.

## Requisitos

- Docker com Compose v2 (Windows com WSL2, Linux ou macOS).
- Máquina **x86_64** (o alvo da imagem é `linux/amd64`; em Apple Silicon roda emulado).
- 8 GB de RAM (16 GB é melhor) e 25 GB livres.
- A imagem do pipeline ocupa cerca de 1,9 GB (inclui Piper + voz pt-BR); o navegador opcional acrescenta ~2,6 GB.
- Internet no primeiro `build`, para baixar o modelo de transcrição uma vez, e para o provedor de voz que você escolher.

## Comece em 5 passos

1. **Prepare o kit**: `./kit.sh setup`.
2. **Confira o ambiente**: `./kit.sh doctor`.
3. **Construa a imagem**: `./kit.sh build`.
4. **Ensine o seu agente**: copie `prompts/02-instalar-skill-no-seu-agente.md`.
5. **Peça o vídeo**: use `prompts/03-dublagem-transcrever-e-entender.md` para dublar ou `prompts/08-video-por-cenas.md` para criar por cenas. O agente conduz `status → próximo passo → run → qa --strict` e pede as aprovações humanas.

## Documentação

O guia completo, offline e copiável está em **[alisonglima.github.io/forja](https://alisonglima.github.io/forja/)** (fonte em [`docs/index.html`](docs/index.html)). Ele cobre visão geral, brief/aprovação, voz local e por conta, arquitetura, overlays, os 14 prompts, segurança, licenças, navegador e problemas.

## Comandos do kit

| Comando | O que faz |
|---|---|
| `./kit.sh setup` | Cria `.env`, gera a senha do navegador, cria `projects/` e `models/`. |
| `./kit.sh doctor` | Confere Docker, Compose, arquitetura, disco e o provedor de voz. |
| `./kit.sh build` | Constrói a imagem `forja:0.1` (linux/amd64), com Piper e voz pt-BR. |
| `./kit.sh new <nome> <vídeo>` | Cria `projects/<nome>/` e roda `forja init` com o vídeo. |
| `./kit.sh run <args>` | Roda a CLI no container, ex.: `./kit.sh run --project /projects/meu --json status`. |
| `./kit.sh shell` | Abre um shell no container. |
| `./kit.sh browser-up` / `browser-down` / `browser-reset` | Chromium opcional em container, para logar na sua conta e usar a interface web. |

## Segurança

- **Sem chave obrigatória.** Nos modos `files`/`piper`, nenhuma credencial de TTS é necessária; o `.env` guarda a senha da tela do navegador (quando usada) e ajustes do container.
- Se você optar por um provedor por API, a chave fica só no `.env` (0600 no Linux/macOS; no Windows, restrinja a pasta do kit à sua conta) e nunca é impressa em log ou `--json`.
- O container roda com o seu UID/GID (nunca root), `cap_drop: ALL` e `no-new-privileges`.
- O navegador opcional escuta **somente** em `127.0.0.1` (`3001` para a tela, `9222` para o CDP) e exige senha. O login é feito dentro do ambiente final; não copie perfis entre máquinas.
- Leia `prompts/12-consentimento-e-aviso.md` antes de publicar: direitos, consentimento e o aviso de voz sintetizada por IA.

## Licenças

O kit é distribuído sob a **MIT License** (veja [`LICENSE`](LICENSE)). Dependências e licenças estão em [`THIRD_PARTY.md`](THIRD_PARTY.md). O Remotion é gratuito para indivíduos e empresas de até 3 pessoas; acima disso, verifique a licença comercial vigente. O `piper-tts` é GPL-3.0-or-later e a voz pt-BR é MIT/CC0; o áudio gerado não herda a GPL.

## Contribuindo

Issues e pull requests são bem-vindos. Leia [`CONTRIBUTING.md`](CONTRIBUTING.md) e [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Para reportar uma vulnerabilidade, use o canal privado descrito em [`SECURITY.md`](SECURITY.md).

## Status

Versão **0.1.0**. O que está pronto e o que está no roadmap: [`docs/ROADMAP.md`](docs/ROADMAP.md). O contrato técnico completo está em [`DESIGN.md`](DESIGN.md).
