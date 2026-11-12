"""Contrato do `--run` de scripts/prova-kit/lxc-descartavel.sh contra um PVE SIMULADO.

Escrito pelo orquestrador (nao pela lane que implementa). Nada aqui toca o PVE
real: `ssh` e falso e executa o comando num sandbox local; `pct`/`qm`/`pveam`/
`pvesm` sao falsos e mantem estado em arquivos. O sandbox SEPARA os sistemas de
arquivos de verdade: o Mac (repo + --out), o host PVE (cwd proprio, /tmp
proprio) e o CT (/srv, /tmp, /usr/local/bin proprios). Assim o erro classico
"pct push/pull usa caminho do Mac" falha aqui em vez de falhar no hipervisor.

Cenarios (FAKE_SCENARIO): ok | existe_ct | existe_vm | ssh_quebrado |
start_falha | config_adulterada.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "prova-kit" / "lxc-descartavel.sh"
CONTRATO = Path(__file__).with_name("test_lxc_descartavel.py")

FAKE_PCT = r'''#!/usr/bin/env python3
import os, sys, shutil, subprocess, pathlib
S = pathlib.Path(os.environ["FAKE_STATE"]); sc = os.environ.get("FAKE_SCENARIO", "ok")
def log(x): open(S / "log.txt", "a").write(x + "\n")
a = sys.argv[1:]; log("pct " + " ".join(a))
def ctdir(i): return S / "ct" / str(i)
def cfg(i): return S / "cts" / f"{i}.conf"
def ctmap(i, p):
    for pre, sub in (("/srv/", "srv"), ("/tmp/", "tmp"), ("/usr/local/bin/", "usr_local_bin"), ("/root/", "root")):
        if p.startswith(pre): return str(ctdir(i) / sub / p[len(pre):])
    return p
def fail(m, rc=1): sys.stderr.write(m + "\n"); sys.exit(rc)
cmd = a[0]
if cmd == "status":
    i = a[1]
    if sc == "existe_ct" or cfg(i).exists(): print("status: stopped" if cfg(i).exists() else "status: running"); sys.exit(0)
    fail(f"Configuration file 'nodes/pve/lxc/{i}.conf' does not exist", 2)
elif cmd == "create":
    i = a[1]
    if cfg(i).exists(): fail("CT already exists")
    (S / "cts").mkdir(exist_ok=True); ctdir(i).mkdir(parents=True, exist_ok=True)
    kv = {}
    for k in range(3, len(a) - 1):
        if a[k].startswith("--"): kv[a[k][2:]] = a[k + 1]
    cfg(i).write_text(f"hostname: {kv.get('hostname','')}\ndescription: {kv.get('description','')}\n")
elif cmd == "start":
    if sc in ("start_falha", "config_adulterada"): fail("start falhou")
elif cmd == "stop":
    pass
elif cmd == "config":
    i = a[1]
    if not cfg(i).exists(): fail("does not exist", 2)
    t = cfg(i).read_text()
    if sc == "config_adulterada": t = "hostname: outro-ct\ndescription: nao-e-meu\n"
    sys.stdout.write(t)
elif cmd == "destroy":
    i = a[1]
    if not cfg(i).exists(): fail("does not exist", 2)
    cfg(i).unlink(); shutil.rmtree(ctdir(i), ignore_errors=True)
elif cmd == "push":
    i, src, dst = a[1], a[2], ctmap(a[1], a[3])
    if not os.path.exists(src): fail(f"pct push: origem nao existe NO HOST PVE: {src}")
    if not os.path.isdir(os.path.dirname(dst)): fail(f"pct push: diretorio destino ausente no CT: {a[3]}")
    shutil.copy(src, dst)
elif cmd == "pull":
    i, src, dst = a[1], ctmap(a[1], a[2]), a[3]
    if not os.path.exists(src): fail(f"pct pull: origem nao existe no CT: {a[2]}")
    if not os.path.isdir(os.path.dirname(os.path.abspath(dst))): fail(f"pct pull: diretorio destino ausente NO HOST PVE: {dst}")
    shutil.copy(src, dst)
elif cmd == "exec":
    i = a[1]; argv = a[a.index("--") + 1:]
    root = ctdir(i)
    if not (cfg(i).exists() and root.exists()): fail("CT nao existe", 2)
    for sub in ("srv", "tmp", "usr_local_bin", "root"): (root / sub).mkdir(exist_ok=True)
    def m(s):
        for pre, sub in (("/srv/", "srv"), ("/tmp/", "tmp"), ("/usr/local/bin/", "usr_local_bin"), ("/root/", "root")):
            s = s.replace(pre, str(root / sub) + "/")
        return s
    if argv[:2] == ["bash", "-lc"] or argv[:2] == ["bash", "-c"]:
        argv = ["bash", "-c", m(argv[2])]
    else:
        argv = [m(x) for x in argv]
    env = dict(os.environ, PATH=os.environ["FAKE_CTBIN"] + ":" + os.environ["PATH"])
    sys.exit(subprocess.run(argv, env=env, cwd=str(root)).returncode)
else:
    fail("pct fake: subcomando nao suportado: " + cmd)
'''

FAKE_QM = r'''#!/bin/sh
echo "qm $*" >> "$FAKE_STATE/log.txt"
if [ "$1" = status ] && [ "$FAKE_SCENARIO" = existe_vm ]; then echo "status: stopped"; exit 0; fi
if [ "$1" = status ]; then echo "Configuration file does not exist" >&2; exit 2; fi
exit 1
'''

FAKE_SSH = r'''#!/usr/bin/env python3
import os, sys, subprocess, pathlib
S = pathlib.Path(os.environ["FAKE_STATE"]); sc = os.environ.get("FAKE_SCENARIO", "ok")
a = sys.argv[1:]; rest = []; i = 0
while i < len(a):
    if a[i] == "-o": i += 2; continue
    rest.append(a[i]); i += 1
host, cmd = rest[0], " ".join(rest[1:])
open(S / "log.txt", "a").write("ssh " + cmd + "\n")
if sc == "ssh_quebrado":
    sys.stderr.write("ssh: connect to host: Connection refused\n"); sys.exit(255)
for proibido in os.environ["FAKE_MAC_PATHS"].split("|"):
    if proibido and proibido in cmd:
        sys.stderr.write(f"FAKE PVE: caminho do Mac no comando remoto: {proibido}\n"); sys.exit(97)
tmp = S / "pve_tmp"; tmp.mkdir(exist_ok=True); (S / "pve_home").mkdir(exist_ok=True)
cmd = cmd.replace("/tmp/", str(tmp) + "/")
env = dict(os.environ, PATH=os.environ["FAKE_PVEBIN"] + ":" + os.environ["PATH"])
sys.exit(subprocess.run(["sh", "-c", cmd], env=env, cwd=str(S / "pve_home")).returncode)
'''

FAKE_PVEAM = r'''#!/bin/sh
echo "pveam $*" >> "$FAKE_STATE/log.txt"
echo "NAME  SIZE"
echo "local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst  120MB"
'''

FAKE_PVESM = r'''#!/bin/sh
echo "pvesm $*" >> "$FAKE_STATE/log.txt"
echo "Name  Type  Status"
echo "vmdata  zfspool  active"
'''

CT_STUBS = {
    "ip": '#!/bin/sh\necho "2: eth0    inet 10.0.0.5/24 scope global eth0"\n',
    "apt-get": '#!/bin/sh\necho "apt-get $*" >> "$FAKE_STATE/log.txt"\nexit 0\n',
    "curl": '#!/bin/sh\necho "curl $*" >> "$FAKE_STATE/log.txt"\nwhile [ $# -gt 0 ]; do [ "$1" = -o ] && : > "$2"; shift; done\nexit 0\n',
    "google-chrome": '#!/bin/sh\necho "Google Chrome 130.0.0.0"\n',
    "node": '#!/bin/sh\necho "v22.0.0"\n',
    "npm": '#!/bin/sh\necho "npm $*" >> "$FAKE_STATE/log.txt"\necho "sha512-FAKEINTEGRITY"\n',
    "npx": '#!/bin/sh\necho "npx $*" >> "$FAKE_STATE/log.txt"\necho "0.4.0"\n',
    "systemctl": "#!/bin/sh\nexit 0\n",
    "tcpdump": "#!/bin/sh\nexit 0\n",
}


def _exec(path: Path, texto: str):
    path.write_text(texto, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _contrato():
    spec = importlib.util.spec_from_file_location("contrato_lxc", CONTRATO)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _montar(tmp_path, cenario):
    st = tmp_path / "pve"
    macbin, pvebin, ctbin = tmp_path / "macbin", st / "pvebin", st / "ctbin"
    for d in (st, macbin, pvebin, ctbin):
        d.mkdir(parents=True, exist_ok=True)
    _exec(macbin / "ssh", FAKE_SSH)
    for nome in ("scp", "rsync", "sshpass"):
        _exec(macbin / nome, f'#!/bin/sh\necho "{nome} PROIBIDO $*" >> "{st}/log.txt"\nexit 98\n')
    _exec(pvebin / "pct", FAKE_PCT)
    _exec(pvebin / "qm", FAKE_QM)
    _exec(pvebin / "pveam", FAKE_PVEAM)
    _exec(pvebin / "pvesm", FAKE_PVESM)
    for nome, txt in CT_STUBS.items():
        _exec(ctbin / nome, txt)
    out = tmp_path / "ev"
    env = dict(os.environ, PATH=f"{macbin}:{os.environ['PATH']}", FAKE_STATE=str(st),
               FAKE_SCENARIO=cenario, FAKE_PVEBIN=str(pvebin), FAKE_CTBIN=str(ctbin),
               FAKE_MAC_PATHS=f"{ROOT}|{out}|{tmp_path}/macbin", PVE_HOST="root@pve-falso")
    return st, out, env


def _rodar(tmp_path, cenario, ctid="920"):
    assert SCRIPT.is_file(), f"falta {SCRIPT}"
    st, out, env = _montar(tmp_path, cenario)
    proc = subprocess.run(["bash", str(SCRIPT), "--run", "--ctid", ctid, "--out", str(out)],
                          capture_output=True, text=True, env=env, cwd=ROOT, timeout=120)
    log = (st / "log.txt").read_text(encoding="utf-8") if (st / "log.txt").exists() else ""
    return proc, out, st, log


def _linhas(log, prefixo):
    return [x for x in log.splitlines() if x.startswith(prefixo)]


def test_ciclo_completo_gera_evidencia_valida(tmp_path):
    proc, out, st, log = _rodar(tmp_path, "ok")
    assert proc.returncode == 0, proc.stderr + "\n" + log
    assert _contrato().validar(out) == [], _contrato().validar(out)
    ciclo = json.loads((out / "lxc-ciclo.json").read_text(encoding="utf-8"))
    assert ciclo["destroy_ok"] is True and ciclo["sha256"]["local"] == ciclo["sha256"]["ct"]
    assert (out / "evidencias-920.tar.gz").is_file(), "tarball de evidencias nao chegou ao Mac"
    assert "PROIBIDO" not in log, "scp/rsync/sshpass chamados (use ssh com stdin/stdout)"


def test_ordem_e_marcador_no_ciclo(tmp_path):
    proc, out, st, log = _rodar(tmp_path, "ok")
    assert proc.returncode == 0, proc.stderr
    criar = [x for x in _linhas(log, "pct create ")]
    assert len(criar) == 1 and "forja-prova-kit-920" in criar[0]
    destruir = _linhas(log, "pct destroy ")
    assert destruir == ["pct destroy 920 --purge"], destruir
    idx = lambda p: next(i for i, x in enumerate(log.splitlines()) if x.startswith(p))
    assert idx("pct create ") < idx("pct start ") < idx("pct push ") < idx("pct pull ") < idx("pct destroy ")
    assert idx("pct config ") < idx("pct destroy "), "destroy sem confirmar marcador antes"


def test_provisao_da_base_e_kit_fixo(tmp_path):
    proc, out, st, log = _rodar(tmp_path, "ok")
    assert proc.returncode == 0, proc.stderr
    assert any("apt-get install" in x for x in log.splitlines())
    assert "@feimacode/open-design-agent-kit@0.4.0" in log
    assert "google-chrome-prova" in log, "wrapper de Chrome offline nao gravado"
    assert not list((st / "pve_tmp").glob("*920*")), "sobrou arquivo temporario no PVE"


@pytest.mark.parametrize("cenario", ["existe_ct", "existe_vm"])
def test_id_ocupado_nunca_cria_nem_destroi(tmp_path, cenario):
    proc, out, st, log = _rodar(tmp_path, cenario)
    assert proc.returncode == 2, (proc.returncode, proc.stderr)
    assert not _linhas(log, "pct create ") and not _linhas(log, "pct destroy ")


def test_ssh_quebrado_nao_e_id_livre(tmp_path):
    proc, out, st, log = _rodar(tmp_path, "ssh_quebrado")
    assert proc.returncode != 0
    assert not _linhas(log, "pct create ") and not _linhas(log, "pct destroy ")
    assert "ssh" in (proc.stderr or "").lower() or "pve" in (proc.stderr or "").lower()


def test_falha_apos_create_destroi_so_o_proprio(tmp_path):
    proc, out, st, log = _rodar(tmp_path, "start_falha")
    assert proc.returncode != 0
    assert len(_linhas(log, "pct create ")) == 1
    assert _linhas(log, "pct destroy ") == ["pct destroy 920 --purge"]
    assert not any(" 219" in x for x in _linhas(log, "pct "))


def test_config_adulterada_nao_destroi(tmp_path):
    proc, out, st, log = _rodar(tmp_path, "config_adulterada")
    assert proc.returncode != 0
    assert len(_linhas(log, "pct create ")) == 1
    assert not _linhas(log, "pct destroy "), "destruiu CT cujo marcador/hostname nao conferem"
    assert "nao destruo" in proc.stderr


def test_modo_inside_roda_fases_na_ordem(tmp_path):
    assert SCRIPT.is_file()
    raiz, bindir = tmp_path / "ct", tmp_path / "bin"
    (raiz / "scripts" / "prova-kit").mkdir(parents=True)
    bindir.mkdir()
    _exec(bindir / "node", '#!/bin/sh\necho "$@" >> "$ORDEM"\n[ "${1##*/}" = lote-csv.mjs ] && exit 3\nexit 0\n')
    for n in ("export-exato", "export-pdf", "lote-csv", "medir-rede"):
        (raiz / "scripts" / "prova-kit" / f"{n}.mjs").write_text("//", encoding="utf-8")
    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", ORDEM=str(tmp_path / "ordem.txt"),
               INSIDE_ROOT=str(raiz))
    proc = subprocess.run(["bash", str(SCRIPT), "--inside"], capture_output=True, text=True,
                          env=env, cwd=ROOT, timeout=60)
    ordem = [Path(x.split()[0]).name for x in (tmp_path / "ordem.txt").read_text().splitlines()]
    assert ordem == ["export-exato.mjs", "export-pdf.mjs", "lote-csv.mjs", "medir-rede.mjs"], ordem
    assert proc.returncode != 0, "fase com exit 3 deve falhar o --inside no fim"
    fases = json.loads((raiz / "evidencias" / "fases.json").read_text(encoding="utf-8"))
    assert {f["fase"]: f["exit"] for f in fases}["lote-csv"] == 3
