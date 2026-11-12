#!/usr/bin/env python3
"""Wrapper fino: design-tokens.json -> `brand` do Remotion (plano:1449,2606).

Uso: python3 scripts/od/tokens_to_remotion.py --tokens design-tokens.json
Saida: objeto `brand` em JSON; exit 2 para uso/entrada invalida.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from forja.brand_tokens import load_brand  # noqa: E402
from forja.errors import ForjaError  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tokens do design system -> brand do Remotion")
    parser.add_argument("--tokens", required=True,
                        help="design-tokens.json relativo ao CWD")
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        brand = load_brand(args.tokens, None)
    except ForjaError as exc:
        print(exc.msg, file=sys.stderr)
        return exc.exit_code
    json.dump(brand, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
