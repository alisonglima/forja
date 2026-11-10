"""Contrato do compose: pastas do kit montadas do host (funciona com qualquer UID)."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _compose():
    return yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))


def test_forja_mounts_projects_and_models_from_the_kit_folder():
    compose = _compose()
    volumes = compose["services"]["forja"]["volumes"]
    assert "./projects:/projects" in volumes
    assert "./models:/models" in volumes
    assert "models" not in (compose.get("volumes") or {})


def test_browser_ports_stay_on_loopback():
    compose = _compose()
    ports = compose["services"]["browser"]["ports"]
    assert all(str(port).startswith("127.0.0.1:") for port in ports)


def test_forja_does_not_import_every_secret_from_the_env_file():
    """A chave do TTS entra explicita; a senha do navegador nao vai para o forja."""
    service = _compose()["services"]["forja"]
    assert "env_file" not in service
    environment = service["environment"]
    assert "GEMINI_API_KEY" in environment
    assert "BROWSER_PASSWORD" not in environment
