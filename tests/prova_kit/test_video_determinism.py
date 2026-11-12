"""Contrato da prova (e), parte 2: determinismo e comparação em `p5-05-video/`.
Cada motor (`hf`, `remotion`) roda `ffmpeg -f framemd5` duas vezes
(plano:2321); `<motor>.1.framemd5` e `<motor>.2.framemd5` precisam ter os
mesmos 150 hashes de quadro (plano:2321). `ssim.txt` traz o `All:` numérico
entre os motores (plano:2321), e `hf.time`/`remotion.time` registram tempo de
parede e pico de RSS com exit 0 (plano:2311-2317,2321). O `.mjs`/`.sh` só
executa e grava; nenhum assert de aceitação fora deste teste (plano:2345-2350).
"""
# LACUNA: plano:2357 não fixa os nomes dos framemd5; adotados
# `<motor>.1.framemd5` e `<motor>.2.framemd5`; SSIM mínimo não fixado
# (valida-se (0,1]); esta parte não tem JSON (vazio/truncado em framemd5,
# ssim.txt e .time).
# DIVERGENCIA: comandos usam `evidencias/p5-05/` (plano:2311-2317); árvore
# usa `p5-05-video/` (plano:2357); adotada a árvore.
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

MOTORES = ("hf", "remotion")
QUADROS = 150
NOMES = {f"{m}.{r}.framemd5" for m in MOTORES for r in (1, 2)} | {"ssim.txt"} | {f"{m}.time" for m in MOTORES}
HASH = re.compile(r"^[0-9a-f]{32}$")
SSIM = re.compile(r"All:\s*(-?\d+(?:\.\d+)?)")
ELAPSED = re.compile(r"Elapsed \(wall clock\) time[^)]*\):\s*([0-9:.]+)")
RSS = re.compile(r"Maximum resident set size \(kbytes\):\s*(\d+)")
EXIT = re.compile(r"Exit status:\s*(\d+)")

def _segundos(texto):
    total = 0.0
    for parte in texto.split(":"):
        total = total * 60 + float(parte)
    return total
def validar(ev):
    """Lista problemas; ev = dict nome->conteúdo ou caminho da pasta."""
    if not isinstance(ev, dict):
        raiz = Path(ev)
        if not raiz.is_dir():
            return [f"diretório ausente: {raiz}"]
        ev = {n: (raiz / n).read_bytes() for n in NOMES if (raiz / n).is_file()}
    ev = {n: (v.decode("utf-8", "replace") if isinstance(v, bytes) else str(v)) for n, v in ev.items()}
    p, seq = [f"arquivo ausente: {n}" for n in sorted(NOMES) if n not in ev], {}
    for motor in MOTORES:
        for rodada in (1, 2):
            nome = f"{motor}.{rodada}.framemd5"
            if nome in ev:
                linhas = [x.split(",") for x in ev[nome].splitlines() if x.strip() and not x.startswith("#")]
                hs = [x[-1].strip() for x in linhas if len(x) > 5 and HASH.match(x[-1].strip())]
                if len(hs) != len(linhas):
                    p.append(f"{nome}: hash de quadro ausente/inválido")
                seq[(motor, rodada)] = hs
        if (motor, 1) not in seq or (motor, 2) not in seq: continue
        if len(seq[(motor, 1)]) != QUADROS:
            p.append(f"{motor}: {len(seq[(motor, 1)])} quadros, esperado {QUADROS}")
        if seq[(motor, 1)] != seq[(motor, 2)]:
            p.append(f"{motor}: framemd5 repetido diverge")
    if "ssim.txt" in ev:
        achado = SSIM.search(ev["ssim.txt"])
        if achado is None:
            p.append("ssim.txt: All: ausente")
        elif not 0 < float(achado.group(1)) <= 1:
            p.append(f"ssim.txt: All fora de (0,1]: {achado.group(1)}")
    for motor in MOTORES:
        nome = f"{motor}.time"
        if nome not in ev: continue
        for regex, rotulo, converte, ok in ((ELAPSED, "tempo", _segundos, lambda x: x > 0), (RSS, "RSS", int, lambda x: x > 0), (EXIT, "exit", int, lambda x: x == 0)):
            achado = regex.search(ev[nome])
            if achado is None:
                p.append(f"{nome}: {rotulo} ausente")
            elif not ok(converte(achado.group(1))):
                p.append(f"{nome}: {rotulo} inválido ({achado.group(1)})")
    return p
def _amostra():
    ev = {}
    for motor in MOTORES:
        texto = "#format: framemd5\n" + "".join(f"0, {q}, {q}, 1, 129600, {q + (motor == 'remotion') * 1000:032x}\n" for q in range(QUADROS))
        ev[f"{motor}.1.framemd5"] = ev[f"{motor}.2.framemd5"] = texto
        ev[f"{motor}.time"] = (f'\tCommand being timed: "{motor}"\n\tElapsed (wall clock) time (h:mm:ss or m:ss): 0:05.00\n'
                               "\tMaximum resident set size (kbytes): 123456\n\tExit status: 0\n")
    ev["ssim.txt"] = "SSIM Y:0.99 All:0.987654 (19.09dB)\n"
    return ev
def test_contrato_amostra_valida():
    assert validar(_amostra()) == []
def test_contrato_arquivo_ausente():
    ev = _amostra()
    del ev["remotion.2.framemd5"]
    assert "arquivo ausente: remotion.2.framemd5" in validar(ev)
def test_contrato_hash_ausente():
    ev = _amostra(); ultimo = ev["hf.1.framemd5"].splitlines()[-1]
    ev["hf.1.framemd5"] = ev["hf.1.framemd5"].replace(ultimo[-32:], "")
    assert any("hash de quadro ausente" in x for x in validar(ev))
def test_contrato_vazio_ou_truncado():
    ev = _amostra(); ev["remotion.1.framemd5"] = ""; ev["ssim.txt"] = "SSIM Y:0.99"
    ev["hf.time"] = "Elapsed (wall clock) time (h:mm:ss or m:ss): "
    problemas = validar(ev)
    assert "remotion: 0 quadros, esperado 150" in problemas
    assert "ssim.txt: All: ausente" in problemas
    assert "hf.time: tempo ausente" in problemas
def test_contrato_valor_fora_do_criterio():
    ev = _amostra()
    for rodada in (1, 2): ev[f"hf.{rodada}.framemd5"] = "\n".join(ev[f"hf.{rodada}.framemd5"].splitlines()[:-1]) + "\n"
    linhas = ev["hf.2.framemd5"].splitlines()
    ev["hf.2.framemd5"] = "\n".join(linhas[:-1] + [linhas[-1][:-32] + "0" * 32]) + "\n"
    ev["ssim.txt"] = "SSIM All:1.2 (20dB)\n"
    ev["remotion.time"] = ev["remotion.time"].replace("123456", "0").replace("Exit status: 0", "Exit status: 1")
    problemas = validar(ev)
    assert "hf: 149 quadros, esperado 150" in problemas and "hf: framemd5 repetido diverge" in problemas
    assert "ssim.txt: All fora de (0,1]: 1.2" in problemas
    assert "remotion.time: RSS inválido (0)" in problemas and "remotion.time: exit inválido (1)" in problemas
def test_evidencia_real():
    if os.environ.get("FORJA_PROVA_KIT") != "1":
        pytest.skip("defina FORJA_PROVA_KIT=1 para ler .work/prova-kit/evidencias/")
    raiz = Path(__file__).resolve().parents[2] / ".work/prova-kit/evidencias/p5-05-video"
    if not raiz.is_dir():
        pytest.fail(f"evidência ausente: {raiz}")
    assert validar(raiz) == []
