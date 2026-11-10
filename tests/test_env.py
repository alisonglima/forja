"""Subprocessos nao herdam variaveis com cara de segredo."""
from forja import env as envmod


def test_sanitized_drops_secret_like_names():
    clean = envmod.sanitized(
        {
            "PATH": "/bin",
            "HOME": "/tmp",
            "GEMINI_API_KEY": "x",
            "BROWSER_PASSWORD": "y",
            "HF_TOKEN": "z",
            "MY_SECRET": "w",
        }
    )
    assert clean == {"PATH": "/bin", "HOME": "/tmp"}


def test_sanitized_keeps_unrelated_names():
    clean = envmod.sanitized({"TZ": "UTC", "NODE_OPTIONS": "--max-old-space-size=512"})
    assert clean == {"TZ": "UTC", "NODE_OPTIONS": "--max-old-space-size=512"}
