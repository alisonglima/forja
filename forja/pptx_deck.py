"""Operacoes deterministicas em decks pptx sinteticos.

O modulo trabalha sobre `python-pptx` e nao le argv, rede ou o OD: `clone`
duplica um slide com relacoes e notas, `put` troca texto sem perder estilo,
`set_pic` repointa a imagem, `slim` poda masters/layouts ociosos e `validate`
compara o arquivo com o catalogo e o sha256 do template.
"""

from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path

from pptx import Presentation
from pptx.exc import PythonPptxError
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn
from pptx.shapes.picture import Picture

from forja.errors import ForjaError

_R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_GROUP_TAGS = (qn("p:nvGrpSpPr"), qn("p:grpSpPr"))
_R_ATTR = "{%s}" % _R_NS


def _error(msg: str) -> dict:
    return {"level": "error", "code": "DECK_SCHEMA", "msg": msg}


def clone(prs, src_slide):
    """Copia o slide para o fim do deck, remapeando relacoes e notas."""
    out = prs.slides.add_slide(src_slide.slide_layout)
    dst_tree = out.shapes._spTree
    for child in list(dst_tree):
        if child.tag not in _GROUP_TAGS:
            dst_tree.remove(child)
    for child in src_slide.shapes._spTree:
        if child.tag in _GROUP_TAGS:
            continue
        copied = deepcopy(child)
        _remap_rels(copied, src_slide.part, out.part)
        dst_tree.append(copied)
    if src_slide.part.has_notes_slide:
        _copy_notes(src_slide.notes_slide, out.notes_slide)
    return out


def _remap_rels(element, src_part, dst_part) -> None:
    """Aponta todo atributo `r:` do elemento para uma relacao do slide novo."""
    for node in element.iter():
        for attr, value in list(node.attrib.items()):
            if not attr.startswith(_R_ATTR) or not value:
                continue
            try:
                rel = src_part.rels[value]
            except KeyError:
                continue
            if rel.is_external:
                new_id = dst_part.relate_to(rel.target_ref, rel.reltype, is_external=True)
            else:
                new_id = dst_part.relate_to(rel.target_part, rel.reltype)
            node.set(attr, new_id)


def _copy_notes(src_notes, dst_notes) -> None:
    """Copia os paragrafos das notas preservando a formatacao."""
    src_body = src_notes.notes_text_frame._txBody
    dst_body = dst_notes.notes_text_frame._txBody
    for paragraph in list(dst_body.findall(qn("a:p"))):
        dst_body.remove(paragraph)
    for paragraph in src_body.findall(qn("a:p")):
        dst_body.append(deepcopy(paragraph))


def _text_shape(slide, name: str, contains: str | None):
    """Devolve a unica forma de texto com `name` (e `contains`), ou falha."""
    matches = [shape for shape in slide.shapes if shape.name == name]
    if contains is not None:
        matches = [
            shape
            for shape in matches
            if getattr(shape, "has_text_frame", False) and contains in shape.text_frame.text
        ]
    if len(matches) != 1 or not getattr(matches[0], "has_text_frame", False):
        raise ForjaError(
            "DECK_SHAPE_MISSING",
            f"slide sem forma de texto unica {name!r}",
            details={"name": name, "contains": contains},
        )
    return matches[0]


def put(slide, name: str, text: str, contains: str | None = None) -> None:
    """Troca o texto da forma, mantendo o `rPr` do primeiro run."""
    text_frame = _text_shape(slide, name, contains).text_frame
    first = text_frame.paragraphs[0]
    runs = list(first.runs)
    if runs:
        runs[0].text = text
        for run in runs[1:]:
            run._r.getparent().remove(run._r)
    else:
        first.add_run().text = text
    for paragraph in list(text_frame._txBody.findall(qn("a:p")))[1:]:
        text_frame._txBody.remove(paragraph)


def _cover_crop(img_w: int, img_h: int, frame_w: float, frame_h: float, focal) -> tuple:
    """Fracoes (esq, dir, topo, base) para a imagem cobrir o quadro sem esticar; `focal` em 0..1."""
    img_ratio, frame_ratio = img_w / img_h, frame_w / frame_h
    fx, fy = (min(max(float(v), 0.0), 1.0) for v in focal)
    if img_ratio > frame_ratio:  # imagem mais larga: recorta os lados
        cut = 1 - frame_ratio / img_ratio
        return cut * fx, cut * (1 - fx), 0.0, 0.0
    cut = 1 - img_ratio / frame_ratio  # imagem mais alta: recorta cima e baixo
    return 0.0, 0.0, cut * fy, cut * (1 - fy)


def set_pic(slide, name: str, path, focal=(0.5, 0.5)) -> None:
    """Repointa o `r:embed` da imagem e enquadra a foto no quadro do template (recorte `cover`, sem esticar)."""
    matches = [shape for shape in slide.shapes if shape.name == name]
    if len(matches) != 1 or not isinstance(matches[0], Picture):
        raise ForjaError(
            "DECK_SHAPE_MISSING",
            f"slide sem imagem unica {name!r}",
            details={"name": name},
        )
    image_part, rel_id = slide.part.get_or_add_image_part(str(path))
    pic = matches[0]
    pic._element.blipFill.blip.set(qn("r:embed"), rel_id)
    img_w, img_h = image_part.image.size
    left, right, top, bottom = _cover_crop(img_w, img_h, pic.width, pic.height, focal)
    pic.crop_left, pic.crop_right, pic.crop_top, pic.crop_bottom = left, right, top, bottom


def slim(prs, keep_layouts) -> None:
    """Remove masters/layouts sem uso e o que so eles carregavam no pacote."""
    keep = {str(name) for name in keep_layouts}
    used = {slide.slide_layout.part for slide in prs.slides}
    for master in list(prs.slide_masters):
        layouts = list(master.slide_layouts)
        kept = {layout.part for layout in layouts if layout.part in used or layout.name in keep}
        if not kept:
            _drop_master(prs, master)
            continue
        _drop_layouts(master, kept)


def _drop_layouts(master, kept) -> None:
    layout_ids = master._element.sldLayoutIdLst
    if layout_ids is None:
        return
    for layout_id in list(layout_ids):
        rel_id = layout_id.get(qn("r:id"))
        rel = master.part.rels.get(rel_id)
        if rel is not None and rel.target_part in kept:
            continue
        layout_ids.remove(layout_id)
        if rel_id in master.part.rels:
            master.part.rels.pop(rel_id)


def _drop_master(prs, master) -> None:
    presentation = prs.part
    rel_id = None
    for key, rel in list(presentation.rels.items()):
        if rel.reltype == RT.SLIDE_MASTER and rel.target_part is master.part:
            rel_id = key
            break
    if rel_id is None:
        return
    presentation.rels.pop(rel_id)
    master_ids = presentation._element.sldMasterIdLst
    if master_ids is None:
        return
    for master_id in list(master_ids):
        if master_id.get(qn("r:id")) == rel_id:
            master_ids.remove(master_id)


def validate(path, catalog, template_sha256) -> list:
    """Reabre o deck e devolve issues de contrato; nunca imprime."""
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        return [_error(f"nao foi possivel ler o deck: {exc}")]
    issues = []
    if hashlib.sha256(data).hexdigest() != template_sha256:
        issues.append(_error("sha256 do template nao confere"))
    try:
        prs = Presentation(str(path))
    except (OSError, PythonPptxError, ValueError, KeyError) as exc:
        issues.append(_error(f"deck invalido: {exc}"))
        return issues

    expected_slides = catalog.get("slides")
    if isinstance(expected_slides, int) and len(prs.slides) != expected_slides:
        issues.append(_error(f"slides: esperado {expected_slides}, achado {len(prs.slides)}"))
    if len(prs.slide_masters) != 1:
        issues.append(_error(f"masters: esperado 1, achado {len(prs.slide_masters)}"))
    names = {layout.name for layout in prs.slide_layouts}
    for name in catalog.get("layouts") or []:
        if name not in names:
            issues.append(_error(f"layout ausente: {name!r}"))
    expected_notes = catalog.get("notes")
    if isinstance(expected_notes, list):
        actual_notes = [
            slide.notes_slide.notes_text_frame.text if slide.part.has_notes_slide else ""
            for slide in prs.slides
        ]
        if actual_notes != list(expected_notes):
            issues.append(_error("notas do deck nao conferem com o catalogo"))
    return issues


def drop_slides(prs, keep) -> None:
    """Mantem so os slides de `keep`, soltando a relacao do descartado."""
    indexes = {int(index) for index in keep}
    total = len(prs.slides)
    if not indexes:
        raise ValueError("keep vazio: o deck ficaria sem slides")
    for index in sorted(indexes):
        if index < 0 or index >= total:
            raise IndexError(f"slide fora do deck: {index} (total {total})")
    slide_ids = prs.slides._sldIdLst
    relations = prs.part.rels
    for position, slide_id in enumerate(list(slide_ids)):
        if position in indexes:
            continue
        rel_id = slide_id.get(qn("r:id"))
        slide_ids.remove(slide_id)
        if rel_id in relations:
            relations.pop(rel_id)
