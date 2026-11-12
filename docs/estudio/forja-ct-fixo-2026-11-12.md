# CT fixo da Forja no PVE (padrão do setup pessoal)

Decisão do dono (12/11/2026): no setup pessoal a Forja roda num **CT fixo do PVE**, não em Docker nem no Mac. O CT efêmero 920 do `lxc-descartavel.sh` continua existindo só para **provas** (criado e destruído a cada rodada); este é o ambiente de trabalho.

## O que é

| Item | Valor |
|---|---|
| CT | `220` `lab88-forja`, Debian 12, não privilegiado (`nesting=1`), `onboot=1` |
| Recursos | 4 cores, 8 GB de RAM, 1 GB de swap, 40 GB em `vmdata` |
| Rede | `192.168.88.58/24`, gw `.1`, `vmbr0`, MAC `BC:24:11:84:11:1A`, sem firewall de CT |
| Usuário | `forja` (sem root por SSH; `AllowUsers forja`, só chave) |
| Código | `/srv/forja/repo` (clone de `alisonglima/forja`, branch `studio/integracao`), venv em `/srv/forja/venv` |
| Acervo | `/srv/forja/acervo` (só os 158 arquivos que os índices da marca referenciam, 2,3 GB; **privado, © Lions**) |
| Ferramentas | Python 3.11, Node 22, Chrome 157 (`forja-chrome`, `--no-sandbox`), LibreOffice 7.4 (Impress), ffmpeg 5.1, poppler, ImageMagick, qpdf, fontes Roboto/Liberation/DejaVu |
| Ambiente | `/etc/profile.d/forja.sh`: `PATH` do venv, `FORJA_BRAND_SOURCES=/srv/forja/acervo`, `OPEN_DESIGN_BROWSER_PATH`, `OPEN_DESIGN_FFMPEG_PATH` |

Criação e reprodução: `scripts/pve/forja-ct.sh create|provision|keys|verify|status` (idempotente; `--dry-run` só imprime).

## Como acessar

| De onde | Comando | Observação |
|---|---|---|
| MacBook | `ssh forja-ct` | alias em `~/.ssh/config`; o Mac está na mesma LAN |
| Host OCI | `ssh forja-ct` | alias em `~/.ssh/config` do `ubuntu`; sai por `wg1` (a origem vista pelo CT é `10.99.3.2`) |
| Agente DSH (container `dsh`) | `ssh forja-ct` | alias com `ProxyJump proxmox` (o agente já alcança o PVE) |
| PVE | `pct exec 220 -- bash -lc '…'` | sem SSH |

Todos usam as chaves que o PVE já aceita (Mac, `dsh-agent@oci`, `ubuntu@oci-lab88` com `from="10.99.3.2"`). Exemplo de uso: `ssh forja-ct 'bash -lc "forja doctor"'`.

## Verificações medidas em 12/11/2026

- `forja-ct.sh verify`: 6 de 6 (CT em execução, `onboot=1`, Mac, host OCI, agente DSH, root recusado). Conferido também com `hostname` por cada caminho, não só pelo código de saída.
- Suíte completa **no CT** (Linux, Python 3.11): 1744 passam, 0 falham, 28 puladas (10 de evidência do kit e 18 do simulador do PVE, que exigem máquina sem Chrome).
- Acervo copiado: os 145 hashes `sha256` do `photos-index.json` conferem byte a byte.
- Render real no CT (Chrome + `open-design-agent-kit@0.4.0`): `lions-capa-campanha` e `leo-carrossel-miolo` com `check` e `export` exit 0; a capa é **pixel a pixel idêntica** (0 pixels diferentes) à da rodada no CT efêmero.
- Wheel: `pip wheel` constrói (85 arquivos, JSON de dados e o entry point `forja`).
- Backup: o job de cluster é `all=1` sem exclusões e `not-backed-up` está vazio; a primeira cópia do CT 220 é a de 13/11 às 02:30 (`tankbackup`, snapshot, `keep-daily 7`, `weekly 4`, `monthly 3`). **Restauração não testada.**

## Como operar

- Atualizar o código: `ssh forja-ct 'cd /srv/forja/repo && git pull --ff-only && /srv/forja/venv/bin/pip install -q -e ".[test]"'`.
- Atualizar o acervo (a partir do Mac, só o que os índices citam): gerar a lista de caminhos dos índices de `brands/leo-lions/` e `tar cf - --no-xattrs -T lista | ssh forja-ct 'tar xf - -C /srv/forja/acervo'` (depois `find /srv/forja/acervo -name "._*" -delete`).
- Projeto de deck: o workflow `slides` resolve o template como `<raiz do projeto>/<file do catálogo>` e `--template` recebe o **id** (`lions-oficial-2022`), não o caminho. Em `/srv/forja/work/<projeto>` ligue `box` e `brands` do acervo/repo por symlink e crie `config.yaml` (`project.workflow: slides`), `brief.yaml` e `deck.yaml`.
- Suíte: `ssh forja-ct 'bash -lc "cd /srv/forja/repo && python -m pytest -q"'`.
- Reverter: `pct stop 220 && pct destroy 220` (o CT só tem dado derivado; o acervo e o código estão no Mac/GitHub).

## Riscos e pendências abertas

1. **IP `.58` está dentro do pool DHCP** (`default-dhcp` = `.10–.254`), como os outros CTs fixos (`.55–.57`), sem reserva. Hoje não há lease nem ARP para `.58`. Convém uma reserva por MAC no RB5009 (escrita no roteador: do dono ou do agente DSH, que tem essa autorização). **Não verifiquei** se o RouterOS faz verificação de ping antes de entregar o endereço.
2. O acervo no CT é **cópia** de dados © Lions e de fotos com pessoas, na LAN privada do dono. Não sai do CT.
3. Uma tela do CT não existe: logins interativos do Google (kit/Flow) continuam no CT 219.
4. A restauração do backup do CT 220 não foi exercitada.
