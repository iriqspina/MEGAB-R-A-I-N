#!/usr/bin/env python3
"""Evidence-only report gate. See relatorios-glm/references/contrato-cli.md."""
import argparse
import json
import sys

import mb_relatorios_glm as ledger


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--manifest", required=True, help="JSON dentro de evidence/ do projeto")
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("init", "refresh"):
        command = sub.add_parser(name)
        command.add_argument("--production", required=True, help="result.json real do cliente")
        command.add_argument("--credit-exception")
        command.add_argument("--deadline", help="Prazo ISO com fuso, somente para excecao")
        command.add_argument("--fragment", help="Saida GLM literal congelada, incorporada uma vez na montagem POP")
        if name == "init":
            command.add_argument("--report", required=True)
            command.add_argument("--asset", action="append", default=[])
    sub.add_parser("revise").add_argument("--review", required=True)
    sub.add_parser("verify").add_argument("--inspection", required=True)
    sub.add_parser("deliver")
    sub.add_parser("status")
    sub.add_parser("begin-task").add_argument('--request',required=True,help='Pedido humano novo congelado: human_followup apos entrega ou human_reframe apos revogacao')
    sub.add_parser("promote").add_argument("--slug", required=True)
    revoke = sub.add_parser("revoke")
    revoke.add_argument("--reason", required=True)
    revoke.add_argument("--evidence", action="append", required=True)
    revoke.add_argument("--artifact-sha256", help="Hash de candidato anterior deste manifesto; padrao e o ciclo atual")
    args = parser.parse_args(argv)
    try:
        common = (args.project, args.manifest)
        if args.action == 'begin-task':
            data=ledger.begin_task(*common,args.request)
        elif args.action == "init":
            data = ledger.init(*common, args.report, args.production, args.asset, args.credit_exception, args.deadline, args.fragment)
        elif args.action == "refresh":
            data = ledger.refresh(*common, args.production, args.credit_exception, args.deadline, args.fragment)
        elif args.action == "revise":
            data = ledger.revise(*common, args.review)
        elif args.action == "verify":
            data = ledger.verify(*common, args.inspection)
        elif args.action == "promote":
            data = ledger.promote(*common, args.slug)
        elif args.action == "revoke":
            data = ledger.revoke(*common, args.reason, args.evidence, artifact_sha256=args.artifact_sha256)
        elif args.action == "deliver":
            data = ledger.deliver(*common)
        else:
            data = ledger.status(*common)
        if args.action != "status":
            data = ledger.status(*common)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 2 if args.action == "status" and data["state"] == "blocked" else 0
    except (ledger.GateError, ledger.mb_trava.TravaOcupada, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"state": "blocked", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
