# Dependências e licenças de terceiros

Este arquivo lista o que foi **verificado nos pacotes e imagens reais** durante a preparação do kit
(10/11/2026). Onde não foi possível ler a licença da fonte, está marcado **a verificar** — não trate
como licença confirmada. O Forja é distribuído sob a MIT License (veja `LICENSE`).

## Python (dentro da imagem `forja:0.1`)

Versões medidas com `docker run --rm --entrypoint /opt/venv/bin/pip forja:0.1 freeze`.

| Pacote | Versão | Licença | Como foi verificado |
|---|---:|---|---|
| PyYAML | 6.0.3 | MIT | classificador do pacote (`License :: OSI Approved :: MIT License`) |
| numpy | 2.4.6 | BSD-3-Clause | classificador do pacote (`BSD License`) |
| scipy | 1.17.1 | BSD-3-Clause | classificador do pacote (`BSD License`) |
| faster-whisper | 1.2.1 | MIT | metadado do PyPI (`license: MIT`) |
| ctranslate2 | 4.8.5 | MIT | metadado do PyPI |
| tokenizers | 0.23.3 | Apache-2.0 | classificador do PyPI |
| huggingface_hub | 2.4.0 | Apache-2.0 | metadado do PyPI |
| onnxruntime | 1.31.1 | MIT | metadado do PyPI |
| av (PyAV) | 18.1.0 | BSD-3-Clause | **a verificar** (o PyPI não declara no metadado; conferir no pacote) |
| demais transitivas | — | MIT/BSD/Apache em geral | **a verificar** caso a caso (`pip freeze` lista todas) |

O `pyproject.toml` declara apenas `pyyaml`, `numpy`, `scipy` e `faster-whisper`; as demais entram
como dependências dessas.

## Node / Remotion

| Pacote | Versão | Licença | Como foi verificado |
|---|---:|---|---|
| remotion | 4.0.540 | Remotion License (`SEE LICENSE IN LICENSE.md`) | metadado do npm; página oficial em 10/11/2026: gratuito para **indivíduos e empresas de até 3 pessoas**; acima disso, licença comercial |
| @remotion/cli | 4.0.540 | Remotion License | metadado do npm |
| react | 18.3.1 | MIT | metadado do npm |
| react-dom | 18.3.1 | MIT | metadado do npm |
| Chrome Headless Shell | baixado pelo Remotion | termos do Google Chrome for Testing | **a verificar** antes de redistribuir a imagem |

O texto integral da licença do Remotion está em `remotion-template/node_modules/remotion/LICENSE.md`
depois do `npm install`; leia-o antes de usar o kit em uma empresa com mais de 3 pessoas.

## Sistema e imagem

| Componente | Versão | Licença | Como foi verificado |
|---|---:|---|---|
| ffmpeg (Debian) | 5.1.9-0+deb12u1 | **GPL** (build com `--enable-gpl --enable-libx264`) | `ffmpeg -version` dentro da imagem |
| Node.js (imagem base) | 22 (bookworm-slim) | MIT (Node.js) + pacotes Debian com licenças próprias | imagem oficial `node:22-bookworm-slim` |
| Python | 3.11 (Debian) | PSF | pacote `python3` do Debian |
| tini | Debian | MIT | pacote `tini` do Debian |
| fontes Liberation / DejaVu / Noto Color Emoji | Debian | OFL / Bitstream Vera / OFL | **a verificar** nos arquivos `/usr/share/doc/*/copyright` da imagem |
| imagem `lscr.io/linuxserver/chromium` (opcional) | latest | GPL-3.0 (repositório LinuxServer.io) | API do GitHub em 10/11/2026; componentes internos **a verificar** |
| imagem `alpine/socat` (opcional) | latest | GPL-2.0 para o socat | **a verificar** no pacote Alpine |
| modelo Whisper (baixado em runtime) | tiny/large conforme config | MIT (OpenAI Whisper) | repositório oficial do modelo |

## Serviços externos (não são dependências empacotadas)

| Serviço | Condição |
|---|---|
| Provedor de voz por API (opcional; ex.: Gemini) | termos e preços do provedor que você escolher; no plano gratuito do Google o conteúdo pode ser usado para melhorar produtos. No modo padrão (`files`) nenhum serviço de voz é chamado. |
| Interface web do provedor de voz (ex.: Google AI Studio) | termos da conta do provedor usada no navegador |

## Como reconferir

```bash
# dentro do kit, com a imagem construída
docker run --rm --entrypoint /opt/venv/bin/pip forja:0.1 freeze
docker run --rm --entrypoint npm forja:0.1 ls --depth=0 --prefix /opt/forja/remotion
docker run --rm --entrypoint ffmpeg forja:0.1 -version
```

Se você redistribuir a imagem ou o kit, revise as licenças acima e as obrigações de fonte do GPL
(ffmpeg, imagem do Chromium e socat) antes de publicar.
