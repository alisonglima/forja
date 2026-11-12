"""Contrato da prova (e), parte 1: os dois MP4 em p5-05-video/.
Congela de plano:2305-2322 o ffprobe de hf/remotion.mp4 (codec_name, width,
height, pix_fmt, r_frame_rate, nb_frames, duration) e os criterios 1080x1920,
30 fps, 150 quadros, 5,000 s +/- 1 quadro. plano:2345-2405 (K.3) fixa os
arquivos p5-05-video/. O .mjs/.sh so executa; nenhum assert fora daqui.
validar(ev) e puro; contrato usa tmp_path, sem rede/LXC/ffmpeg/poppler/Chrome.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from fractions import Fraction
from pathlib import Path

import pytest

ENGINES = ("hf", "remotion")
CAMPOS = ("codec_name", "width", "height", "pix_fmt", "r_frame_rate", "nb_frames", "duration")
TOLERANCIA_S = 1 / 30 + 1e-6

# DIVERGENCIA: shell de plano:2305-2322 usa p5-05/, K.3 fixa p5-05-video/.
# LACUNA: K.3 nao lista sha256sums.txt; adotado por analogia a p5-01.
# LACUNA: plano nao fixa codec_name/pix_fmt; so exige medicao.
def _sha256(caminho):
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()

def _ler_probe(caminho):
    texto = caminho.read_text(encoding="utf-8") if caminho.is_file() else ""
    if not texto.strip():
        return None, "ffprobe.json ausente/vazio"
    try:
        return json.loads(texto), None
    except json.JSONDecodeError:
        return None, "ffprobe.json truncado/invalido"

def _carregar(raiz):
    pasta = Path(raiz)
    pasta = pasta if pasta.name == "p5-05-video" else pasta / "p5-05-video"
    hashes = {}
    manifesto = pasta / "sha256sums.txt"
    if manifesto.is_file():
        for linha in manifesto.read_text(encoding="utf-8").splitlines():
            partes = linha.split()
            if len(partes) > 1:
                hashes[Path(partes[-1].lstrip("*")).name] = partes[0].lower()
    videos = {}
    for motor in ENGINES:
        mp4 = pasta / f"{motor}.mp4"
        dados, erro = _ler_probe(pasta / f"{motor}.ffprobe.json")
        videos[motor] = {"mp4": mp4, "probe": dados, "sha256": hashes.get(mp4.name), "erro": erro}
    return {"videos": videos}

def _criterios(motor, stream, probe, problemas):
    try:
        testes = {
            "dimensoes": (int(stream["width"]), int(stream["height"])) == (1080, 1920),
            "r_frame_rate": Fraction(str(stream["r_frame_rate"])) == 30,
            "nb_frames": int(stream["nb_frames"]) == 150,
            "duration": abs(float(stream.get("duration") or probe["format"]["duration"]) - 5.0) <= TOLERANCIA_S,
        }
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        testes = {"ffprobe": False}
    problemas.extend(f"{motor}: {campo} fora do criterio" for campo, ok in testes.items() if not ok)

def validar(ev):
    """Devolve a lista de problemas da evidencia ([] = contrato atendido)."""
    ev = ev if isinstance(ev, dict) else _carregar(ev)
    problemas = []
    for motor in ENGINES:
        item = (ev.get("videos") or {}).get(motor) or {}
        mp4 = item.get("mp4")
        if not mp4 or not Path(mp4).is_file():
            problemas.append(f"{motor}.mp4: arquivo ausente")
            continue
        caminho = Path(mp4)
        if caminho.stat().st_size == 0:
            problemas.append(f"{motor}.mp4: arquivo vazio")
        sha = str(item.get("sha256") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", sha):
            problemas.append(f"{motor}.mp4: hash ausente/invalido")
        elif _sha256(caminho) != sha:
            problemas.append(f"{motor}.mp4: hash nao confere")
        probe = item.get("probe")
        if item.get("erro") or not isinstance(probe, dict) or not probe:
            problemas.append(f"{motor}: {item.get('erro') or 'ffprobe vazio/invalido'}")
            continue
        stream = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), None)
        if stream is None:
            problemas.append(f"{motor}: sem stream de video")
            continue
        faltando = [campo for campo in CAMPOS if stream.get(campo) in (None, "")]
        if faltando:
            problemas.append(f"{motor}: campos ffprobe ausentes: {', '.join(faltando)}")
        _criterios(motor, stream, probe, problemas)
    return problemas

def _probe(**troca):
    stream = {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920,
              "pix_fmt": "yuv420p", "r_frame_rate": "30/1", "nb_frames": "150",
              "duration": "5.000000", **troca}
    return {"streams": [stream], "format": {"duration": stream["duration"]}}

def _amostra(tmp_path):
    pasta = tmp_path / "p5-05-video"
    pasta.mkdir()
    videos, linhas = {}, []
    for motor in ENGINES:
        mp4 = pasta / f"{motor}.mp4"
        mp4.write_bytes(f"mp4-{motor}".encode())
        sha = _sha256(mp4)
        linhas.append(f"{sha}  {mp4.name}")
        probe = _probe()
        (pasta / f"{motor}.ffprobe.json").write_text(json.dumps(probe), encoding="utf-8")
        videos[motor] = {"mp4": mp4, "probe": probe, "sha256": sha, "erro": None}
    (pasta / "sha256sums.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return pasta, {"videos": videos}

def test_contrato_amostra_valida(tmp_path):
    assert validar(_amostra(tmp_path)[1]) == []

def test_contrato_arquivo_ausente(tmp_path):
    _, ev = _amostra(tmp_path)
    ev["videos"]["hf"]["mp4"] = tmp_path / "nao-existe.mp4"
    assert any("hf.mp4: arquivo ausente" in p for p in validar(ev))

def test_contrato_valor_fora_do_criterio(tmp_path):
    _, ev = _amostra(tmp_path)
    ev["videos"]["remotion"]["probe"] = _probe(width=1920)
    assert any("remotion: dimensoes" in p for p in validar(ev))

@pytest.mark.parametrize("texto,rotulo", [("", "vazio"), ('{"streams": [', "truncado")])
def test_contrato_json_invalido(tmp_path, texto, rotulo):
    pasta, _ = _amostra(tmp_path)
    (pasta / "hf.ffprobe.json").write_text(texto, encoding="utf-8")
    assert any(rotulo in p for p in validar(pasta))

def test_contrato_hash_ausente(tmp_path):
    _, ev = _amostra(tmp_path)
    ev["videos"]["hf"]["sha256"] = None
    assert any("hf.mp4: hash ausente" in p for p in validar(ev))

def test_evidencia_real():
    if os.environ.get("FORJA_PROVA_KIT") != "1":
        pytest.skip("defina FORJA_PROVA_KIT=1 para ler a evidencia real")
    raiz = Path(__file__).resolve().parents[2] / ".work" / "prova-kit" / "evidencias"
    problemas = validar(raiz)
    assert problemas == [], f"{raiz / 'p5-05-video'}: {problemas}"
