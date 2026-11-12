#!/usr/bin/env python3
"""Wrapper fino: promove/verifica o template aprovado do Open Design.

Uso: python3 scripts/od/promote_template.py --from post.html --brand leo-lions \
      --template post --approved-by NOME --approve-hash SHA256 [--json]
Somente le argv e delega a `forja.templates`; nao reimplementa copia/hash.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from forja.errors import ForjaError, error_payload  # noqa: E402
from forja.templates import promote_template, verify_template  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Promove o template aprovado do OD para brands/<id>/templates/")
    parser.add_argument("--from", dest="src", required=True,
                        help="arquivo do template aprovado no projeto OD")
    parser.add_argument("--brand", required=True, help="diretorio brands/<id>")
    parser.add_argument("--template", required=True, help="nome da peca (post, deck)")
    parser.add_argument("--approved-by", required=True, help="nome do aprovador humano")
    parser.add_argument("--approve-hash", required=True, help="sha256 do arquivo aprovado")
    parser.add_argument("--od-project", default=None)
    parser.add_argument("--od-artifact", default=None)
    parser.add_argument("--design-system", default=None)
    parser.add_argument("--preset", default=None)
    parser.add_argument("--approved-at", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def _emit(payload: dict) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.check or args.verify:
            result = verify_template(args.brand, args.template)
        else:
            result = promote_template(
                args.src, args.brand, args.template,
                approve_hash=args.approve_hash, approved_by=args.approved_by,
                od_project=args.od_project, od_artifact=args.od_artifact,
                design_system=args.design_system, preset=args.preset,
                now=args.approved_at or datetime.now(timezone.utc).isoformat(),
                force=args.force)
    except ForjaError as exc:
        if args.json:
            _emit(error_payload(exc))
        else:
            print("%s: %s" % (exc.code, exc.msg), file=sys.stderr)
        return exc.exit_code
    _emit({"ok": True, "result": result})
    return 0


if __name__ == "__main__":
    sys.exit(main())
