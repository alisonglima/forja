"""Contrato da prova (f): rede estática em `.work/prova-kit/evidencias/p5-06-rede/`.
Congela `fora-loopback.txt` vazio e `dns.txt` sem consultas na fase estática,
`destinos.txt` sem destino proibido, `ss-antes.txt`/`ss-depois.txt` sem
listener em 0.0.0.0/::, `env.txt` sem token e `rede-static.json` com
fase/tx/rx; árvore em `p5-06-rede/` (plano:2323-2344,2358). O `.mjs`/`.sh`
só executa e grava, sem assert de aceitação (plano:2347-2350); o teste lê
JSON e pcap, TLS não prova conteúdo (plano:2343).
# LACUNA: nomes/schema/volume/formato não fixados (adoto 2328-2333); hash
# não está na árvore e é exigido. DIVERGENCIA: árvore `rede-*`/`ss-*` (2358) x nomes exatos (2328-2333): uso os exatos; env.txt cobre a omissão de 2358.
"""

from __future__ import annotations

import hashlib, json, os, re
from pathlib import Path
import pytest

RAIZ = Path(__file__).resolve().parents[2]
EVID = RAIZ / ".work/prova-kit/evidencias/p5-06-rede"
OBRIG = ("rede-static.pcap", "rede-static.json", "fora-loopback.txt", "destinos.txt", "dns.txt",
         "ss-antes.txt", "ss-depois.txt", "env.txt")
HEX = re.compile(r"^[0-9a-f]{64}$")
TOKEN = re.compile(r"(?:^|_)(?:TOKEN|SECRET|SECRETS|PASSWORD|PASSWD|APIKEY|API_KEY|ACCESS_KEY|PRIVATE_KEY|CREDENTIAL|CREDENTIALS|AUTH)$")
PROIBIDOS = ("open-design.feimacode.com", "auth.feimacode.com", "buffer.com", "metricool.com", "x.com",
             "twitter.com", "shopify.com", "slack.com", "figma.com", "canva.com", "fonts.googleapis.com", "fonts.gstatic.com")
PCAP = (b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4", b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d")


def _b(v): return v.encode("utf-8") if isinstance(v, str) else v
def _sha(v): return hashlib.sha256(_b(v)).hexdigest()
def _txt(v): return _b(v).decode("utf-8", "replace")


def _ler(ev):
    if isinstance(ev, dict): return {k: v for k, v in ev.items() if k != "sha256"}, ev.get("sha256"), []
    if not isinstance(ev, (str, Path)): return {}, None, ["evidência deve ser dict ou caminho de diretório"]
    base = Path(ev)
    if not base.is_dir(): return {}, None, [f"diretório de evidência ausente: {base}"]
    arqs = {p.name: p.read_bytes() for p in base.iterdir() if p.is_file()}
    return arqs, {n: _sha(v) for n, v in arqs.items()}, []


def _listener(linha):
    c = linha.split()
    if "LISTEN" not in {x.upper() for x in c[:3]}: return None
    i = 4 if c and c[0].lower() in {"tcp", "udp", "u_str", "u_dgr"} else 3
    if len(c) <= i: return None
    return c[i] if re.match(r"^(?:0\.0\.0\.0|\[::\]|\*):(?:\d+|\*)$", c[i]) else None


def validar(ev):
    """Lista os problemas da evidência; [] significa contrato cumprido."""
    arqs, sha, p = _ler(ev)
    if p: return p
    for n in OBRIG:
        if n not in arqs: p.append(f"arquivo ausente: {n}")
    pcap = arqs.get("rede-static.pcap")
    if pcap is not None and not _b(pcap).startswith(PCAP):
        p.append("rede-static.pcap: cabeçalho pcap ausente ou truncado")
    bruto = _txt(arqs["rede-static.json"]) if "rede-static.json" in arqs else None
    if bruto is not None:
        try: dados = json.loads(bruto)
        except (TypeError, ValueError): p.append("rede-static.json: JSON truncado ou vazio")
        else:
            if not isinstance(dados, dict): p.append("rede-static.json: raiz não é objeto")
            else:
                if dados.get("fase") != "static":
                    p.append(f"rede-static.json: fase {dados.get('fase')!r}, esperada 'static'")
                for campo in ("tx", "rx"):
                    valor = dados.get(campo)
                    if isinstance(valor, bool) or not isinstance(valor, int) or valor < 0:
                        p.append(f"rede-static.json: {campo} ausente ou fora do critério")
    for n in ("fora-loopback.txt", "dns.txt"):
        bruto = _txt(arqs[n]) if n in arqs else None
        if bruto is not None and bruto.strip():
            p.append(f"{n}: tráfego na fase estática: {bruto.strip().splitlines()[0][:80]}")
    baixo = _txt(arqs.get("destinos.txt", "")).lower()
    for destino in PROIBIDOS:
        if re.search(rf"(?<![a-z0-9-]){re.escape(destino)}(?![a-z0-9-])", baixo):
            p.append(f"destinos.txt: destino proibido: {destino}")
    for n in ("ss-antes.txt", "ss-depois.txt"):
        bruto = _txt(arqs[n]) if n in arqs else None
        if bruto is None: continue
        if not bruto.strip(): p.append(f"{n}: snapshot vazio"); continue
        for linha in bruto.splitlines():
            local = _listener(linha)
            if local: p.append(f"{n}: listener em 0.0.0.0/::: {local}"); break
    bruto = _txt(arqs["env.txt"]) if "env.txt" in arqs else None
    if bruto is not None:
        for linha in bruto.splitlines():
            achado = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=", linha)
            if achado and TOKEN.search(achado.group(1).upper()):
                p.append(f"env.txt: variável sensível presente: {achado.group(1)}")
    sha = sha or {}
    for n in OBRIG:
        hash_ = sha.get(n)
        if not hash_: p.append(f"hash ausente: {n}")
        elif not HEX.match(str(hash_).lower()): p.append(f"hash inválido: {n}")
        elif n in arqs and _sha(arqs[n]) != str(hash_).lower(): p.append(f"hash não confere: {n}")
    return p


def _amostra():
    ev = {"rede-static.pcap": b"\xd4\xc3\xb2\xa1" + b"\x00" * 20,
          "rede-static.json": '{"fase":"static","tx":0,"rx":0}\n',
          "fora-loopback.txt": "", "destinos.txt": "", "dns.txt": "",
          "ss-antes.txt": "Netid State Recv-Q Send-Q Local Address:Port Peer Address:Port Process\n",
          "ss-depois.txt": "Netid State Recv-Q Send-Q Local Address:Port Peer Address:Port Process\n",
          "env.txt": "PATH=/usr/bin\nHOME=/root\n"}
    ev["sha256"] = {n: _sha(v) for n, v in ev.items()}
    return ev


def test_contrato_evidencia_valida(tmp_path):
    ev = _amostra(); assert validar(ev) == []
    base = tmp_path / "p5-06-rede"; base.mkdir()
    for n, v in ev.items():
        if n != "sha256": (base / n).write_bytes(_b(v))
    assert validar(base) == []


@pytest.mark.parametrize("mutar,trecho", [
    (lambda e: e.pop("destinos.txt"), "arquivo ausente: destinos.txt"),
    (lambda e: e.update({"dns.txt": "12:00 IP 10.0.0.2.5353 > 8.8.8.8.53: 1+ A?\n"}), "dns.txt"),
    (lambda e: e.update({"fora-loopback.txt": "12:00 IP 10.0.0.2.9 > 1.1.1.1.443\n"}), "fora-loopback.txt"),
    (lambda e: e.update({"rede-static.json": '{"fase":"video","tx":0,"rx":0}'}), "fase 'video'"),
    (lambda e: e.update({"ss-antes.txt": "tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:*\n"}), "listener"),
    (lambda e: e.update({"env.txt": "OPEN_DESIGN_FIGMA_TOKEN=segredo\n"}), "OPEN_DESIGN_FIGMA_TOKEN"),
    (lambda e: e.update({"destinos.txt": "open-design.feimacode.com\n"}), "destino proibido"),
    (lambda e: e["sha256"].pop("rede-static.pcap"), "hash ausente: rede-static.pcap"),
])
def test_contrato_defeitos(mutar, trecho):
    ev = _amostra(); mutar(ev)
    assert any(trecho in p for p in validar(ev))


@pytest.mark.parametrize("bruto", ["{", "", "[]"])
def test_contrato_json_truncado_ou_vazio(bruto):
    ev = _amostra(); ev["rede-static.json"] = bruto
    assert any("JSON" in p or "objeto" in p for p in validar(ev))


def test_evidencia_real():
    if os.environ.get("FORJA_PROVA_KIT") != "1":
        pytest.skip("defina FORJA_PROVA_KIT=1 com .work/prova-kit/evidencias/p5-06-rede/")
    problemas = validar(EVID)
    assert problemas == [], f"p5-06-rede: {'; '.join(problemas)}"
