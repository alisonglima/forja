"""`forja init` sem video cria um projeto por cenas valido; dublagem exige --source."""
import io
import json

import yaml


def _run(argv):
    from forja import cli

    out, err = io.StringIO(), io.StringIO()
    code = cli.main(argv, env={}, out=out, err=err)
    return code, json.loads(out.getvalue())


def test_init_without_source_creates_a_storyboard_project(tmp_path):
    code, doc = _run(["--json", "init", str(tmp_path / "p")])
    assert code == 0 and doc["ok"] is True and (tmp_path / "p" / "storyboard.yaml").is_file()


def test_storyboard_project_has_assets_dir_and_no_cues_files(tmp_path):
    _run(["--json", "init", str(tmp_path / "p")])
    root = tmp_path / "p"
    assert (root / "assets").is_dir() and not (root / "cues.json").exists() and not (root / "lower_thirds.json").exists()


def test_starter_storyboard_passes_validation(tmp_path):
    from forja import storyboard

    _run(["--json", "init", str(tmp_path / "p")])
    sb = yaml.safe_load((tmp_path / "p" / "storyboard.yaml").read_text(encoding="utf-8"))
    errors = [i for i in storyboard.validate_storyboard(sb, tmp_path / "p") if i["level"] == "error"]
    assert errors == []


def test_status_of_a_fresh_storyboard_project_uses_the_storyboard_workflow(tmp_path):
    _run(["--json", "init", str(tmp_path / "p")])
    code, doc = _run(["--json", "--project", str(tmp_path / "p"), "status"])
    assert code == 0 and doc["ok"] is True
    assert doc["data"]["workflow"] == "storyboard" and doc["data"]["steps"][0]["name"] == "validate"


def test_init_dub_without_source_is_a_usage_error(tmp_path):
    code, doc = _run(["--json", "init", str(tmp_path / "p"), "--workflow", "dub"])
    assert code == 2 and doc["error"]["code"] == "USAGE" and "--source" in doc["error"]["msg"]


def test_init_with_source_still_creates_a_dub_project(tmp_path):
    source = tmp_path / "v.mp4"
    source.write_bytes(b"x")
    code, doc = _run(["--json", "init", str(tmp_path / "p"), "--source", str(source)])
    assert code == 0 and (tmp_path / "p" / "cues.json").is_file() and not (tmp_path / "p" / "storyboard.yaml").exists()


def test_agents_md_lists_storyboard_files_for_the_storyboard_workflow():
    from forja import project

    text = project.agents_md("storyboard")
    assert "storyboard.yaml" in text and "cues.json" not in text


def test_agents_md_for_dub_is_unchanged_in_its_file_list():
    from forja import project

    text = project.agents_md("dub")
    assert "cues.json" in text and "lower_thirds.json" in text and "storyboard.yaml" not in text


def test_init_next_action_quotes_the_project_path(tmp_path):
    """O comando sugerido nao pode virar injecao quando o caminho tem ';' ou espaco."""
    import shlex

    weird = tmp_path / "x; touch pwn"
    code, doc = _run(["--json", "init", str(weird)])
    assert code == 0
    command = doc["next_actions"][0]["command"]
    assert shlex.split(command)[:2] == ["forja", "--project"]
    assert shlex.split(command)[2] == str(weird)
    assert command.endswith(" status")
