# Forja

**Vídeo com voz e legenda, operado pelo seu agente.** Dublagem EN→pt-BR e vídeos por cenas a partir de um `storyboard.yaml`, com narração no **Google AI Studio** e cenas no **Google Flow** — usando as suas contas e créditos, sem exigir chave de API.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-2ea44f.svg)](https://alisonglima.github.io/forja/)

A **forja** é uma CLI (`forja`, `python -m forja`) e um kit Docker para gerar vídeos com agentes de IA. Ela faz o trabalho determinístico — transcrever, montar a linha do tempo, mixar, renderizar e verificar o resultado — e deixa o julgamento (texto, voz, overlays, consentimento) para você.

- **Dublar**: transcreve o vídeo, adapta o texto para pt-BR, usa as vozes que você gerou ou a voz local, mixa com ducking, queima a legenda e passa um gate de qualidade.
- **Criar por cenas**: monta um vídeo do zero com clipes gerados no **Google Flow**, narração no AI Studio, cards, overlays, trilha e legendas.
- **Overlays profissionais**: lower-third, título, callout, citação, CTA, logo e estatística, com tema de marca e posição/entrada/saída por camada.
- **Áudio completo**: voz, música, áudio embutido do clipe e `sfx` no mesmo bed, com ducking e loudness.
- **Âncoras por palavra**: alinha card/overlay à fala transcrita pelo Whisper, sem chute.
- **MCP**: `forja mcp serve` expõe 8 tools da CLI para agentes que preferem tools a shell.
- **Para agentes**: todo comando aceita `--json`, `describe`, `status` com `next_actions`, cache por hash, QA como gate e códigos de saída `0..5`.
- **Humano no comando**: `brief.yaml` registra objetivo/público/tom; `forja approve` registra a aprovação humana antes do render.

## Voz: Google AI Studio por padrão

| Provider | Precisa de conta/API? | Quando usar |
|---|---|---|
| `google_ai_studio` (padrão) | Não para o kit; você usa a sua conta Google no navegador | Você gera as vozes na interface web do AI Studio e salva `voices/<id>.wav`. |
| `piper` | Não | Narração local neural, sem rede, com o modelo pt-BR incluído na imagem. |
| `files` | Não | Alias genérico: qualquer WAV que você já tenha, de qualquer ferramenta. |
| `gemini` | Sim, opcional | Automação por API com a sua chave; não é o caminho padrão. |

O padrão é o **Google AI Studio**: abra a interface com a sua conta, gere cada fala e salve em `projects/<nome>/voices/<id>.wav`. O kit valida, normaliza, mixa e renderiza. O `piper` é uma **alternativa local opcional**, não o setup padrão: voz única, qualidade abaixo do AI Studio, `piper-tts` GPL-3.0 e modelo MIT/CC0; use só se quiser autonomia offline. Nenhuma conta é compartilhada e nenhuma chave é obrigatória.

## Cenas: Google Flow por padrão

O caminho padrão para os clipes é o **Google Flow**, aberto no navegador já logado com a **sua conta e os seus créditos**. O agente opera a interface (prompt 14), baixa os MP4s para `assets/flow/` e atualiza o `storyboard.yaml`; o Forja **não chama o Flow por API**, só valida, monta a timeline, mixa e renderiza.

Ressalvas que valem para todo mundo:

- **Flow é interface, não API.** A automação depende da UI, da conta e dos créditos; pode quebrar quando o Google mudar a tela.
- **Créditos e plano:** cada geração consome créditos e pode exigir plano pago; confirme antes de gerar em lote. Não contorne limites, filas, captcha ou políticas.
- **Conteúdo e direitos:** siga os termos do Google Flow/Labs e as políticas de conteúdo; vídeos podem ter marca d'água/SynthID e regras de uso comercial. Não gere pessoas reais, marcas ou cenas sensíveis sem autorização.
- **Não determinístico:** o mesmo prompt pode gerar resultados diferentes; guarde prompt, take e versão e revise com olhos humanos.
- **Áudio no Flow:** peça **somente SFX e som ambiente** — sem fala, sem narração, sem diálogo, sem música e sem legenda na imagem; a narração vem do AI Studio e a trilha é a camada `music` licenciada. O áudio embutido (só SFX) entra no bed por padrão; `audio: {mode: mute}` remove se o Flow gerar fala/música por engano. `sfx` exige `license.kind`.
- **Exceção de áudio original:** vídeo que já traz áudio que não pode ser removido (ex.: dublagem de um vídeo gravado) é trabalhado sobre o **áudio original**, que fica ao fundo com ducking sob a narração.

Se você não usar Flow, traga os clipes prontos em `assets/` e use o mesmo `storyboard.yaml`. A ferramenta não gera B-roll/imagens por IA fora do seu navegador.

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

## Áudio, sfx e âncoras por palavra

O bed do storyboard soma, na timeline:

- **Narração** (voz do AI Studio/arquivo/Piper), com ducking do bed durante a fala.
- **Música** (`music`) — `license.kind` é obrigatório.
- **Áudio embutido do clipe** (`clip.audio`) — entra por padrão; `mode: mute` remove, `gain_db` ajusta.
- **Efeitos** (`sfx`) — `asset`/`file`, `license.kind`, `gain_db`, `duration` opcional.

```yaml
- type: clip
  file: assets/flow/cena-01.mp4
  in_s: 0
  audio: {mode: keep, gain_db: -6}
- type: sfx
  file: assets/sfx/whoosh.wav
  license: {kind: "cc0"}
  gain_db: -12
  duration: 0.8
  enter: {anchor: word, word: "começa"}
```

`enter`/`exit` com `{anchor: word, word: "..."}` resolvem o tempo real da palavra. O passo `timeline` transcreve **somente as cenas que usam âncora por palavra**, com `faster-whisper`, e guarda o resultado em `work/words/<cena>.json`; a primeira execução baixa o modelo e pode demorar. Se a transcrição falhar, o passo retorna `MISSING_PREREQ` em vez de fingir que alinhou.

## MCP

Para agentes que falam MCP em vez de shell:

```bash
forja mcp serve
```

É um servidor **stdio**, JSON-RPC 2.0, uma mensagem por linha, sem SDK extra. Ele chama a mesma CLI e devolve o JSON no content da tool. Tools: `forja_describe`, `forja_providers`, `forja_status`, `forja_doctor`, `forja_init`, `forja_run`, `forja_qa`, `forja_approve`.

Exemplo de configuração (Claude Desktop/outros clientes):

```json
{
  "mcpServers": {
    "forja": {"command": "forja", "args": ["mcp", "serve"]}
  }
}
```

No modo sem Docker, use o `forja` do `.venv` (`./.venv/bin/forja`) ou `python -m forja mcp serve`. O servidor não imprime segredos e não publica porta; é stdio local. Exemplo pronto em [`examples/mcp.json`](examples/mcp.json).

## Brief e aprovação humana

`forja init` cria `brief.yaml` e `approvals.json` e liga `project.require_approvals`. O humano preenche o brief (objetivo, público, tom, duração, restrições, consentimento); o agente escreve roteiro/storyboard/overlays e pede aprovação:

```bash
forja approve --script --voice --overlays --by "Ana"
```

O render falha com `GATE_FAILED` enquanto as aprovações exigidas não existirem. Para um teste local sem gate, use `forja init --no-require-approvals`.

## Sem Docker (alternativa)

Se você não tem Docker/VPS ou quer testar numa máquina simples, a CLI roda direto no sistema (Windows, macOS ou Linux). O caminho direto é uma **alternativa** ao kit Docker, com menos isolamento:

```bash
./scripts/local-setup.sh            # macOS/Linux
.\scripts\local-setup.ps1          # Windows PowerShell
python -m forja --json doctor
```

Requisitos: Python 3.9+, ffmpeg/ffprobe, Node 20+ e Chrome via Remotion. O passo a passo completo, por sistema, está em [`LOCAL.md`](LOCAL.md). O Forja acha o `remotion` local em `remotion-template/node_modules/.bin` automaticamente. O navegador é o seu normal (AI Studio/Flow); não há `kit.sh` nesse modo.

## Requisitos (kit Docker)

- Docker com Compose v2 (Windows com WSL2, Linux ou macOS).
- Máquina **x86_64** (o alvo da imagem é `linux/amd64`; em Apple Silicon roda emulado).
- 8 GB de RAM (16 GB é melhor) e 25 GB livres.
- A imagem do pipeline ocupa cerca de 1,9 GB (inclui Piper + voz pt-BR); o navegador opcional acrescenta ~2,6 GB.
- Internet no primeiro `build`, para baixar o modelo de transcrição uma vez, e para o AI Studio/Flow (a conta e os créditos são seus).

## Comece em 5 passos

1. **Prepare o kit**: `./kit.sh setup`.
2. **Confira o ambiente**: `./kit.sh doctor`.
3. **Construa a imagem**: `./kit.sh build`.
4. **Ensine o seu agente**: copie `prompts/02-instalar-skill-no-seu-agente.md`.
5. **Peça o vídeo**: use `prompts/03-dublagem-transcrever-e-entender.md` para dublar ou `prompts/08-video-por-cenas.md` + `prompts/14-google-flow-cenas.md` para criar por cenas. O agente conduz `status → próximo passo → run → qa --strict` e pede as aprovações humanas.

## Documentação

O guia completo, offline e copiável está em **[alisonglima.github.io/forja](https://alisonglima.github.io/forja/)** (fonte em [`docs/index.html`](docs/index.html)). Ele cobre visão geral, brief/aprovação, Google AI Studio e Flow, alternativas locais/API, arquitetura, overlays, áudio/sfx/âncoras, MCP, os 15 prompts, segurança, licenças, navegador e problemas.

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

- **Sem chave obrigatória.** Nos modos `google_ai_studio`/`files`/`piper`, nenhuma credencial de TTS é necessária; o `.env` guarda a senha da tela do navegador (quando usada) e ajustes do container.
- Se você optar por um provedor por API, a chave fica só no `.env` (0600 no Linux/macOS; no Windows, restrinja a pasta do kit à sua conta) e nunca é impressa em log ou `--json`.
- O container roda com o seu UID/GID (nunca root), `cap_drop: ALL` e `no-new-privileges`.
- O navegador opcional escuta **somente** em `127.0.0.1` (`3001` para a tela, `9222` para o CDP) e exige senha. O login é feito dentro do ambiente final; não copie perfis entre máquinas.
- Leia `prompts/12-consentimento-e-aviso.md` antes de publicar: direitos, consentimento e o aviso de voz sintetizada por IA. No Flow, valem também os termos do Google e as regras de créditos/conteúdo.

## Licenças

O kit é distribuído sob a **MIT License** (veja [`LICENSE`](LICENSE)). Dependências e licenças estão em [`THIRD_PARTY.md`](THIRD_PARTY.md). O Remotion é gratuito para indivíduos e empresas de até 3 pessoas; acima disso, verifique a licença comercial vigente. O `piper-tts` é GPL-3.0-or-later e a voz pt-BR é MIT/CC0; o áudio gerado não herda a GPL. Os clipes do Google Flow seguem os termos do Google e a licença do seu plano.

## Contribuindo

Issues e pull requests são bem-vindos. Leia [`CONTRIBUTING.md`](CONTRIBUTING.md) e [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Para reportar uma vulnerabilidade, use o canal privado descrito em [`SECURITY.md`](SECURITY.md). Para uma auditoria independente da implementação, use [`VALIDATION-PROMPT.md`](VALIDATION-PROMPT.md).

## Status

Versão **0.1.0**. O que está pronto e o que está no roadmap: [`docs/ROADMAP.md`](docs/ROADMAP.md). O contrato técnico completo está em [`DESIGN.md`](DESIGN.md).
