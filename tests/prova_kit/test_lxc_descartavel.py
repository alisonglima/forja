"""Contrato da prova LXC descartavel (plano:2125-2210, 2345-2405).

Congela o plano de `--dry-run` e o `lxc-ciclo.json`: ctid/template/rootfs,
recursos fixos (4 vCPU, 6144 MB, 1024 swap), create->run->pull->destroy,
`destroy_ok=true`, `pct status` final sem o CT e sha256 igual dos dois lados
(plano:2192,2399). O `.mjs`/`.sh` so executa e grava; nenhum assert de
aceitacao vive nele (plano:2347-2351). Amostras sinteticas, sem rede/LXC.
"""
# LACUNA: o plano nao fixa o nome do JSON do --dry-run, o schema do sha256
# nem a representacao do status final; usa-se `lxc-plano.json` e campos claros.
# DIVERGENCIA: plano:2129 preserva o 920 se ele existir e usa 921+; plano:2398
# exemplifica --ctid 920. O contrato aceita qualquer ctid != 219.
from __future__ import annotations
import json
import os
import re
from pathlib import Path
import pytest

SHA = "a" * 64

def _json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8")), None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        tipo = "arquivo ausente" if isinstance(e, FileNotFoundError) else "JSON invalido/truncado"
        return None, f"{tipo}: {p}"

def _ler(ev):
    if isinstance(ev, dict):
        p, c = ev.get("plano"), ev.get("ciclo")
        if c is None and "destroy_ok" in ev:
            c = ev
        return p or (c or {}).get("plano"), c, []
    b = Path(ev)
    pp = b / "lxc-plano.json" if b.is_dir() else b.with_name("lxc-plano.json")
    cp = b / "lxc-ciclo.json" if b.is_dir() else (b if b.name == "lxc-ciclo.json" else b.with_name("lxc-ciclo.json"))
    (p, ep), (c, ec) = _json(pp), _json(cp)
    if isinstance(c, dict) and not isinstance(p, dict):
        p, ep = c.get("plano"), None
    return p, c, [e for e in (ep, ec) if e]

def _idx(cmds, *ms):
    return next((i for i, c in enumerate(cmds) if any(m in str(c).lower() for m in ms)), -1)

def _plano(p):
    q = []
    if p.get("dry_run") is not True: q.append("plano: dry_run deve ser true")
    ct = p.get("ctid")
    if not isinstance(ct, int) or isinstance(ct, bool) or ct <= 0: q.append("plano: ctid invalido")
    elif ct == 219: q.append("plano: 219 e referencia, nao destino")
    t, r = p.get("template"), p.get("rootfs")
    if not isinstance(t, str) or not ("debian-13-standard" in t or "debian-12-standard" in t): q.append("plano: template Debian 13/12")
    if not isinstance(r, str) or r.rsplit(":", 1)[-1] != "16" or not r.rsplit(":", 1)[0]: q.append("plano: rootfs <storage>:16")
    if p.get("hostname") != f"prova-kit-{ct}": q.append("plano: hostname prova-kit-<ctid>")
    for k, v in (("cores", 4), ("memoria_mb", 6144), ("swap_mb", 1024)):
        if p.get(k) != v: q.append(f"plano: {k}={v}")
    if p.get("unprivileged") is not True or p.get("nesting") is not True: q.append("plano: unprivileged/nesting true")
    cmds = p.get("comandos")
    if not isinstance(cmds, list) or not cmds: return q + ["plano: comandos ausentes"]
    c, r = _idx(cmds, "pct create"), _idx(cmds, "pct start", "pct exec")
    u, d = _idx(cmds, "pct pull"), _idx(cmds, "pct destroy")
    if any(i < 0 for i in (c, r, u, d)): q.append("plano: faltam create/run/pull/destroy")
    elif not c < r < u < d: q.append("plano: ordem create->run->pull->destroy")
    if c >= 0 and not any("pct status" in str(x).lower() and "qm status" in str(x).lower() for x in cmds[:c]): q.append("plano: falta ID livre antes do create")
    if d >= 0 and "--purge" not in str(cmds[d]).lower(): q.append("plano: destroy --purge")
    st = [i for i, x in enumerate(cmds) if "pct status" in str(x).lower()]
    if d >= 0 and (not st or max(st) < d): q.append("plano: pct status final depois do destroy")
    return q

def _ciclo(c, p):
    q = []
    q += [f"ciclo: {k} ausente/vazio" for k in ("template", "rootfs", "inicio", "fim") if not (isinstance(c.get(k), str) and c[k].strip())]
    if not isinstance(c.get("ctid"), int) or isinstance(c.get("ctid"), bool): q.append("ciclo: ctid invalido")
    if c.get("destroy_ok") is not True: q.append("ciclo: destroy_ok deve ser true")
    for k in ("ctid", "template", "rootfs"):
        if k in p and c.get(k) != p.get(k): q.append(f"ciclo: {k} diverge do plano")
    h = c.get("sha256") if isinstance(c.get("sha256"), dict) else {}
    lo, ct = h.get("local") or h.get("mac") or c.get("sha256_local"), h.get("ct") or h.get("remoto") or c.get("sha256_ct")
    if not lo or not ct: q.append("ciclo: hash ausente (sha256.local/ct)")
    elif str(lo).lower() != str(ct).lower(): q.append("ciclo: hash divergente")
    elif not re.fullmatch(r"[0-9a-f]{64}", str(lo).lower()): q.append("ciclo: hash nao e sha256")
    sf = c.get("pct_status_final") or c.get("status_final")
    if not isinstance(sf, dict): q.append("ciclo: pct_status_final ausente")
    elif sf.get("existe") is True or (sf.get("existe") is not False and not (isinstance(sf.get("exit_code", sf.get("exit")), int) and sf.get("exit_code", sf.get("exit")) != 0)): q.append("ciclo: pct status final deve provar CT ausente")
    return q

def validar(ev):
    p, c, q = _ler(ev)
    q += _plano(p) if isinstance(p, dict) else ["plano ausente/nao e objeto"]
    q += _ciclo(c, p if isinstance(p, dict) else {}) if isinstance(c, dict) else ["lxc-ciclo ausente/nao e objeto"]
    return q

def _ev():
    t = "local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst"
    cmds = ["pct status 920 || qm status 920", f"pct create 920 {t} --hostname prova-kit-920 --cores 4 --memory 6144 --swap 1024 --rootfs vmdata:16 --unprivileged 1 --features nesting=1 --onboot 0", "pct start 920", "pct push 920 /tmp/kit.tgz /srv/prova/kit.tgz", "pct exec 920 -- bash -lc 'tar xzf kit.tgz'", "pct pull 920 /srv/prova/evidencias.tar.gz /tmp/evidencias-920.tar.gz", "sha256sum /tmp/evidencias-920.tar.gz", "pct stop 920 || true; pct destroy 920 --purge", "pct status 920"]
    p = {"dry_run": True, "ctid": 920, "template": t, "rootfs": "vmdata:16", "hostname": "prova-kit-920", "cores": 4, "memoria_mb": 6144, "swap_mb": 1024, "unprivileged": True, "nesting": True, "comandos": cmds}
    c = {"ctid": 920, "template": t, "rootfs": "vmdata:16", "inicio": "2026-11-11T22:00:00Z", "fim": "2026-11-11T22:35:00Z", "destroy_ok": True, "sha256": {"local": SHA, "ct": SHA}, "pct_status_final": {"exit_code": 1, "existe": False}}
    return {"plano": p, "ciclo": c}

def test_contrato_amostra_valida(tmp_path):
    ev = _ev()
    assert validar(ev) == []
    (tmp_path / "lxc-plano.json").write_text(json.dumps(ev["plano"]), encoding="utf-8")
    (tmp_path / "lxc-ciclo.json").write_text(json.dumps(ev["ciclo"]), encoding="utf-8")
    assert validar(tmp_path) == [] and validar(tmp_path / "lxc-ciclo.json") == [] and validar(tmp_path / "lxc-plano.json") == []

def test_contrato_arquivo_ausente(tmp_path):
    assert any("ausente" in x for x in validar(tmp_path / "sumiu"))

def test_contrato_destroy_ok_false():
    ev = _ev(); ev["ciclo"]["destroy_ok"] = False
    assert any("destroy_ok" in x for x in validar(ev))

@pytest.mark.parametrize("conteudo", ["", '{"ctid": 920'])
def test_contrato_json_truncado_ou_vazio(tmp_path, conteudo):
    ev = _ev()
    (tmp_path / "lxc-plano.json").write_text(json.dumps(ev["plano"]), encoding="utf-8")
    (tmp_path / "lxc-ciclo.json").write_text(conteudo, encoding="utf-8")
    assert any("JSON" in x for x in validar(tmp_path / "lxc-ciclo.json"))

def test_contrato_hash_ausente():
    ev = _ev(); ev["ciclo"]["sha256"] = {"local": SHA}
    assert any("hash ausente" in x for x in validar(ev))

def test_contrato_sequencia_e_status_final():
    ev = _ev()
    assert validar(ev) == []
    ev["plano"]["comandos"] = list(reversed(ev["plano"]["comandos"]))
    assert any("ordem" in x for x in validar(ev))
    ev = _ev(); ev["ciclo"]["pct_status_final"] = {"exit_code": 0, "existe": True}
    assert any("status final" in x for x in validar(ev))
    ev = _ev(); ev["plano"].update(ctid=219, hostname="prova-kit-219")
    assert any("219" in x for x in validar(ev))

def test_evidencia_real():
    if os.environ.get("FORJA_PROVA_KIT") != "1":
        pytest.skip("FORJA_PROVA_KIT=1 nao definido")
    base = Path(__file__).resolve().parents[2] / ".work" / "prova-kit" / "evidencias"
    assert validar(base) == [], f"evidencia invalida em {base}: {validar(base)}"
