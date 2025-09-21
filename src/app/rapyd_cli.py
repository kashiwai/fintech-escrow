import argparse
import json
import sys

from .rapyd_client import rapyd_request


def cmd_verify():
    # Safe public data endpoint to verify credentials/signature.
    status, data = rapyd_request("GET", "/v1/data/countries")
    print(status)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_request(method: str, path: str, body_json: str | None):
    body = json.loads(body_json) if body_json else None
    status, data = rapyd_request(method, path, body)
    print(status)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description="Rapyd API signed request CLI")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("verify")
    pr = sub.add_parser("request")
    pr.add_argument("--method", required=True)
    pr.add_argument("--path", required=True)
    pr.add_argument("--body", help="JSON string", default=None)
    args = p.parse_args()
    if args.cmd == "verify":
        cmd_verify()
    elif args.cmd == "request":
        cmd_request(args.method, args.path, args.body)
    else:
        p.print_help()


if __name__ == "__main__":
    main()

