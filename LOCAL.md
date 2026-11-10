# Forja sem Docker (execução direta)

Alternativa para quem tem uma máquina simples, não tem VPS/Docker ou só quer testar sem container. O caminho **padrão** do projeto continua sendo o kit Docker; este é um caminho **suportado pela CLI**, com menos isolamento e mais dependência do sistema.

## Quando usar

- Máquina pessoal (Windows, macOS ou Linux) sem Docker Desktop/WSL2.
- Teste rápido da CLI, do storyboard e do Remotion.
- Ambiente onde você já tem Python, Node e ffmpeg e não quer uma imagem de ~2 GB.

## O que você perde

- Não há versões presas: Python, Node, ffmpeg e Chrome são os do sistema.
- Sem isolamento de container; um comando errado pode afetar arquivos do usuário.
- O `kit.sh`/`kit.ps1` **não** são usados; você chama `python -m forja` diretamente.
- O navegador do AI Studio/Flow é o seu navegador normal, não o Chromium do kit.
- O caminho direto foi exercitado no macOS nesta rodada; Windows e Linux diretos não foram testados ponta a ponta.

## Requisitos

| Peça | Versão | Observação |
|---|---|---|
| Python | 3.9+ | `python3`/`py`; venv recomendado |
| ffmpeg + ffprobe | 5.x+ | precisa de `libx264`; confira `ffmpeg -version` |
| Node.js | 20+ | Remotion 4.0.540 |
| Chrome/Chromium | via Remotion | `npx remotion browser ensure` baixa o Headless Shell |
| RAM/disco | 8 GB / 4 GB livres | o modelo Whisper baixa ~1,6 GB na primeira vez |
| Conta Google | AI Studio + Flow | créditos do Flow são seus |

## Instalação rápida

```bash
git clone https://github.com/alisonglima/forja.git
cd forja
./scripts/local-setup.sh
```

No Windows (PowerShell):

```powershell
git clone https://github.com/alisonglima/forja.git
cd forja
.\scripts\local-setup.ps1
```

O script cria `.venv`, instala o pacote com `pip install -e ".[test]"`, instala as dependências do Remotion, baixa o Chrome Headless Shell e roda `python -m forja --json doctor`. Se o `doctor` reclamar de ffmpeg/Node, instale o que falta e rode de novo.

## Instalação manual

### Windows 10/11

```powershell
winget install Python.Python.3.12
winget install Gyan.FFmpeg
winget install OpenJS.NodeJS.LTS
winget install Google.Chrome
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
cd remotion-template
npm install --no-audit --no-fund
npx remotion browser ensure
cd ..
python -m forja --json doctor
```

### macOS

```bash
brew install python@3.12 ffmpeg node
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
cd remotion-template
npm install --no-audit --no-fund
npx remotion browser ensure
cd ..
python -m forja --json doctor
```

### Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install -y python3 python3-venv ffmpeg nodejs npm chromium
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
cd remotion-template
npm install --no-audit --no-fund
npx remotion browser ensure
cd ..
python -m forja --json doctor
```

Se o Node do apt for antigo, use o NodeSource (Node 20/22) antes do `npm install`.

## Usar

```bash
python -m forja --json describe
python -m forja --json init ~/videos/meu-video
python -m forja --json --project ~/videos/meu-video status
python -m forja --json --project ~/videos/meu-video run
python -m forja --json --project ~/videos/meu-video qa --strict
```

No Windows, troque `~/videos/meu-video` por `C:\Users\SEU_USUARIO\videos\meu-video`.

O fluxo de conteúdo é o mesmo do kit:

1. Preencha `brief.yaml` com o humano.
2. Gere a narração no **Google AI Studio** e salve em `voices/<id>.wav` (provider `google_ai_studio`).
3. Gere as cenas no **Google Flow**, baixe os MP4s para `assets/flow/` e atualize o `storyboard.yaml` (prompt 14).
4. Aprove com `python -m forja --project <projeto> approve --script --voice --overlays --by "Nome"`.
5. Rode o pipeline e o `qa --strict`.

O navegador é o seu normal; não há `./kit.sh browser-up`. Para o Flow, abra a interface no seu navegador logado, com os créditos da sua conta. O Forja **não chama AI Studio nem Flow por API**.

## Variáveis de ambiente

| Variável | Para que serve |
|---|---|
| `FORJA_REMOTION_DIR` | Caminho do `remotion-template` (default: o do repo) |
| `FORJA_MODEL_DIR` | Onde o Whisper guarda o modelo (default: `~/.cache/forja/models`) |
| `HF_HOME` | Cache do Hugging Face, se usado |
| `GEMINI_API_KEY` | Só para o provider opcional `gemini`; não é necessária no padrão |

Nunca grave chave no projeto, em log ou em `--json`.

## Piper (opcional)

O Piper **não é o setup padrão** e não vem instalado no caminho direto. Se quiser narração local offline:

```bash
python -m pip install "piper-tts==1.8.0"
# baixe o .onnx e o .onnx.json da voz pt_BR-faber-medium e aponte em config.yaml
```

Ressalvas: voz única, qualidade abaixo do AI Studio, `piper-tts` GPL-3.0-or-later, modelo MIT/CC0, sem clonagem. Para o setup real, use AI Studio.

## Limitações e segurança

- Sem isolamento de container; rode com o seu usuário, não como root/administrador.
- O `qa`/`validate` continuam gates; não contorne.
- Flow consome créditos e segue termos do Google; não contorne captcha/limite.
- Voz sintetizada de pessoa real exige consentimento e aviso; leia `prompts/12-consentimento-e-aviso.md`.
- Sem GitHub Actions; os testes são locais: `python -m pytest -q tests`.
