"""O verificador de prompts reprova comando/flag/subcomando inexistente e aceita os reais."""
import importlib.util
from pathlib import Path


def _checker():
    path = Path(__file__).resolve().parents[1] / "scripts" / "check-prompts.py"
    spec = importlib.util.spec_from_file_location("check_prompts", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, module._command_table(module._describe())


def test_accepts_real_commands_and_flags():
    mod, table = _checker()
    text = "Rode `./kit.sh run --project /projects/x qa --strict` e depois `forja --json frames --every 2`."
    assert mod.check_text(text, table, "t") == []


def test_rejects_an_unknown_command():
    mod, table = _checker()
    assert any("inexistente" in p for p in mod.check_text("`forja dublar tudo`", table, "t"))


def test_rejects_an_unknown_flag_of_a_real_command():
    mod, table = _checker()
    assert any("--rapido" in p for p in mod.check_text("`forja qa --rapido`", table, "t"))


def test_rejects_an_unknown_kit_subcommand():
    mod, table = _checker()
    assert any("subcomando" in p for p in mod.check_text("`./kit.sh limpar`", table, "t"))


def test_ignores_placeholders_and_prose():
    mod, table = _checker()
    assert mod.check_text("Use o comando forja <comando> para ver a ajuda.", table, "t") == []


def test_all_shipped_prompts_pass():
    mod, table = _checker()
    problems = []
    for path in sorted((Path(__file__).resolve().parents[1] / "prompts").glob("*.md")):
        problems += mod.check_text(path.read_text(encoding="utf-8"), table, path.name)
    assert problems == []
