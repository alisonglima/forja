"""Contrato do comando `forja frames` (quadros reduzidos, tempo no nome, folha de contato)."""
import io
import json
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="precisa de ffmpeg/ffprobe",
)


def _project(tmp_path):
    from forja import project

    root = tmp_path / "p"
    project.scaffold(root, "demo", workflow="dub")
    video = root / "input" / "source.mp4"
    video.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30:duration=7",
         "-pix_fmt", "yuv420p", str(video)],
        check=True,
    )
    return root


def _frames(root, *extra):
    from forja import cli

    out, err = io.StringIO(), io.StringIO()
    code = cli.main(["--json", "--project", str(root), "frames", *extra], env={"PATH": shutil.which("ffmpeg").rsplit("/", 1)[0]}, out=out, err=err)
    return code, json.loads(out.getvalue())


def test_frames_names_each_file_with_its_time(tmp_path):
    root = _project(tmp_path)
    code, doc = _frames(root, "--every", "2")
    names = sorted(p.name for p in (root / "work" / "frames").glob("t*s.jpg"))
    assert code == 0 and names == ["t0000.0s.jpg", "t0002.0s.jpg", "t0004.0s.jpg", "t0006.0s.jpg"]


def test_frames_reports_time_for_each_frame_in_json(tmp_path):
    root = _project(tmp_path)
    _, doc = _frames(root, "--every", "2")
    assert [f["t"] for f in doc["data"]["frames"]] == [0.0, 2.0, 4.0, 6.0]


def test_frames_are_downscaled_to_640_px_wide(tmp_path):
    root = _project(tmp_path)
    _frames(root, "--every", "2")
    shot = root / "work" / "frames" / "t0002.0s.jpg"
    width = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=width", "-of", "csv=p=0", str(shot)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert width == "640"


def test_frames_writes_a_contact_sheet(tmp_path):
    root = _project(tmp_path)
    _, doc = _frames(root, "--every", "2")
    sheet = root / "work" / "frames" / "contact.jpg"
    assert sheet.is_file() and doc["data"]["contact_sheet"] == str(sheet)


def test_frames_removes_stale_frames_from_a_previous_run(tmp_path):
    root = _project(tmp_path)
    _frames(root, "--every", "1")
    _frames(root, "--every", "3")
    names = {p.name for p in (root / "work" / "frames").glob("t*s.jpg")}
    assert "t0003.0s.jpg" in names and names <= {"t0000.0s.jpg", "t0003.0s.jpg", "t0006.0s.jpg"}


def test_frames_rejects_a_non_positive_interval(tmp_path):
    root = _project(tmp_path)
    code, doc = _frames(root, "--every", "0")
    assert code == 2 and doc["ok"] is False
