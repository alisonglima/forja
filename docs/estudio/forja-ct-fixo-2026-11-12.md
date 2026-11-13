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
- Suíte completa **no CT** (Linux, Python 3.11): 1768 passam, 0 falham, 28 puladas (10 de evidência do kit e 18 do simulador do PVE, que exigem máquina sem Chrome).
- Acervo copiado: os 145 hashes `sha256` do `photos-index.json` conferem byte a byte.
- Render real no CT (Chrome + `open-design-agent-kit@0.4.0`): `lions-capa-campanha` e `leo-carrossel-miolo` com `check` e `export` exit 0; a capa é **pixel a pixel idêntica** (0 pixels diferentes) à da rodada no CT efêmero.
- Wheel: `pip wheel` constrói (85 arquivos, JSON de dados e o entry point `forja`).
- Deck real (`forja slides`, template oficial `lions-oficial-2022`, 115 slides) no CT: **6 slides** no `.pptx` e 6 páginas no PDF (LibreOffice), conferidos por imagem. **Correção de registro:** a primeira rodada do CT mostrou que `compose`/`pptx` eram esqueleto (saída com os 115 slides originais + 6 em branco, 121 no total), apesar de os passos reportarem "ok"; foram implementados de verdade (clona o slide-modelo, preenche as formas pelo catálogo, descarta os originais). Defeitos achados só pelo render e corrigidos: ícone de imagem-placeholder no slide "texto", texto de modelo vazando ("Lorem ipsum"), legenda sobrepondo no "números". Agora há trava `DECK_PLACEHOLDER_LEFT` contra texto de modelo no deck e `remover` por modelo no catálogo. **Não verificado:** os modelos `imagem_texto`, `citacao`, `agenda` e `contato` com a marca real (só testados no deck de exemplo de 6 slides e em testes sintéticos); `grafico`, `tabela` e `equipe` ficam fora (`suportado: false`).
- Peças: as **18** peças (feed, story e carrossel, Lions e LEO) renderizadas no CT com `check --fail-on warning` e `export`: 0 achado e PNG **idêntico pixel a pixel** às referências do CT descartável.
- Deck oficial com os 9 modelos suportados: 9 slides, 0 texto de modelo remanescente, conferido por imagem (agenda numerada, contato em português).
- Backup: o job de cluster `all=1` (sem exclusões) copiou o CT 220 em 13/11 às 02:41 (59 s, 4,18 GB, `tankbackup`); `zstd -t` passa, 67.892 entradas, com o repositório e o `.pptx` oficial dentro. **Restauração real não testada** (exigiria criar um CT).
- Rede: o roteador enxerga `192.168.88.58` na VLAN 40 (ARP), mas não há lease nem reserva e o pool `default-dhcp` cobre o endereço (ver Riscos).
- Suíte no CT no commit final: 1768 passam, 0 falham, 28 puladas; os 14 avisos restantes estão só em arquivos de teste.
- Uma queda de SSH ocorreu durante uma suíte longa (`Connection reset by peer`); o CT não reiniciou, sem OOM nem erro do `sshd` nos logs; **causa não determinada**, a repetição passou. Suítes longas: rodar em segundo plano no CT com log em arquivo.

## Como operar

- Atualizar o código: `ssh forja-ct 'cd /srv/forja/repo && git pull --ff-only && /srv/forja/venv/bin/pip install -q -e ".[test]"'`.
- Atualizar o acervo (a partir do Mac, só o que os índices citam): gerar a lista de caminhos dos índices de `brands/leo-lions/` e `tar cf - --no-xattrs -T lista | ssh forja-ct 'tar xf - -C /srv/forja/acervo'` (depois `find /srv/forja/acervo -name "._*" -delete`).
- Projeto de deck: o workflow `slides` resolve o template como `<raiz do projeto>/<file do catálogo>` e `--template` recebe o **id** (`lions-oficial-2022`), não o caminho. Em `/srv/forja/work/<projeto>` ligue `box` e `brands` do acervo/repo por symlink e crie `config.yaml` (`project.workflow: slides`), `brief.yaml` e `deck.yaml`.
- Suíte: `ssh forja-ct 'bash -lc "cd /srv/forja/repo && python -m pytest -q"'`.
- Reverter: `pct stop 220 && pct destroy 220` (o CT só tem dado derivado; o acervo e o código estão no Mac/GitHub).

## Riscos e pendências abertas

1. **IP `.58` está dentro do pool DHCP** (`default-dhcp` = `.10–.254`), como os outros CTs fixos (`.55–.57`), sem reserva. O ARP do roteador o vê (VLAN 40), mas não há lease. Convém uma reserva por MAC no RB5009 (escrita no roteador: do dono ou do agente DSH, que tem essa autorização). **Não verifiquei** se o RouterOS faz verificação de ping antes de entregar o endereço.
2. O acervo no CT é **cópia** de dados © Lions e de fotos com pessoas, na LAN privada do dono. Não sai do CT.
3. Uma tela do CT não existe: logins interativos do Google (kit/Flow) continuam no CT 219.
4. A restauração do backup do CT 220 não foi exercitada (só a integridade do arquivo).
