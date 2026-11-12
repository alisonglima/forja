"""Aceitacao da lane L-PROVA-KIT-00 sem tocar no PVE (escrito pelo orquestrador).

O script `scripts/prova-kit/lxc-descartavel.sh` roda como root no hipervisor
quando chamado com `--run`. Este teste so exercita `--dry-run`, a sintaxe e as
travas de seguranca, com um `ssh`/`scp` FALSOS no PATH que denunciam qualquer
chamada de rede. A prova funcional (create->run->pull->destroy) e uma fase
humana/orquestrada, nao desta lane.

Travas exigidas: dry-run e o padrao; 219 e recusado antes de qualquer saida;
`--run` e opt-in explicito; sem `qm destroy`/`qm stop`; marcador unico no
`pct create`; o plano valida contra o validador do contrato
(`test_lxc_descartavel._plano`).
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "prova-kit" / "lxc-descartavel.sh"
CONTRATO = Path(__file__).with_name("test_lxc_descartavel.py")


def _contrato():
    spec = importlib.util.spec_from_file_location("contrato_lxc", CONTRATO)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _falsos(tmp_path):
    """bin/ com ssh, scp, pct, qm e rsync falsos: gravam a chamada e falham."""
    bindir, marca = tmp_path / "bin", tmp_path / "chamadas.log"
    bindir.mkdir()
    for nome in ("ssh", "scp", "pct", "qm", "rsync", "sshpass"):
        f = bindir / nome
        f.write_text(f'#!/bin/sh\necho "{nome} $*" >> "{marca}"\nexit 99\n', encoding="utf-8")
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    return bindir, marca


def _rodar(tmp_path, *args):
    assert SCRIPT.is_file(), f"falta {SCRIPT}"  # sem isso, recusas passariam por vacuidade
    bindir, marca = _falsos(tmp_path)
    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}")
    out = tmp_path / "ev"
    proc = subprocess.run(["bash", str(SCRIPT), *args, "--out", str(out)],
                          capture_output=True, text=True, env=env, cwd=ROOT, timeout=60)
    return proc, out, marca


def test_script_existe_e_sintaxe_ok():
    assert SCRIPT.is_file(), f"falta {SCRIPT}"
    assert subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True).returncode == 0


def test_sem_comandos_perigosos_de_vm():
    txt = SCRIPT.read_text(encoding="utf-8")
    for proibido in ("qm destroy", "qm stop", "qm shutdown", "qm rollback", "/usr/bin/ssh", "reboot"):
        assert proibido not in txt, f"proibido no script: {proibido}"
    assert "trap" in txt and "forja-prova-kit" in txt and "pct destroy" in txt


def test_dry_run_explicito_gera_plano_valido(tmp_path):
    proc, out, marca = _rodar(tmp_path, "--dry-run", "--ctid", "920")
    assert proc.returncode == 0, proc.stderr
    assert not marca.exists(), f"dry-run chamou rede/PVE: {marca.read_text()}"
    plano = json.loads((out / "lxc-plano.json").read_text(encoding="utf-8"))
    assert _contrato()._plano(plano) == []
    assert plano["dry_run"] is True and plano["ctid"] == 920
    assert "forja-prova-kit" in str(plano.get("marcador", ""))
    criar = [c for c in plano["comandos"] if "pct create" in str(c)]
    assert criar and all(plano["marcador"] in str(c) for c in criar)
    assert json.loads(proc.stdout)["ctid"] == 920


def test_padrao_e_dry_run(tmp_path):
    proc, out, marca = _rodar(tmp_path, "--ctid", "920")
    assert proc.returncode == 0, proc.stderr
    assert not marca.exists(), "sem flag o script nao pode tocar no PVE"
    assert json.loads((out / "lxc-plano.json").read_text(encoding="utf-8"))["dry_run"] is True


@pytest.mark.parametrize("modo", ["--dry-run", "--run"])
def test_recusa_219_antes_de_qualquer_saida(tmp_path, modo):
    proc, out, marca = _rodar(tmp_path, modo, "--ctid", "219")
    assert proc.returncode != 0
    assert not marca.exists(), "219 recusado so depois de chamar o PVE"
    assert not (out / "lxc-plano.json").exists()
    assert re.search(r"219", proc.stderr + proc.stdout)


@pytest.mark.parametrize("ctid", ["abc", "0", "-5", ""])
def test_ctid_invalido_recusado(tmp_path, ctid):
    proc, out, marca = _rodar(tmp_path, "--dry-run", "--ctid", ctid)
    assert proc.returncode != 0 and not marca.exists()
