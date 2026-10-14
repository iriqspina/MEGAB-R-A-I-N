"""Prepare a private local deployment config; never call Cloudflare or deploy.

Public origin and VPC service id are metadata. Gateway secret is intentionally
not accepted here: send it to `wrangler secret put MB_GATEWAY_SECRET` via stdin.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

ROOT = Path(__file__).resolve().parent


def build_config(origin: str, service_id: str) -> dict:
    parsed = urlparse(origin)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or
            parsed.password or parsed.query or parsed.fragment or parsed.port or
            parsed.path not in ('', '/') or not parsed.hostname.endswith('.workers.dev')):
        raise ValueError('Use a origem HTTPS exata do Worker em workers.dev, sem caminho ou credenciais.')
    if UUID(service_id).int == 0:
        raise ValueError('O serviço VPC real ainda não foi criado.')
    source = '\n'.join(line for line in (ROOT / 'wrangler.jsonc').read_text(encoding='utf-8').splitlines()
                       if not line.lstrip().startswith('//'))
    config = json.loads(source)
    config['vars']['PUBLIC_ORIGIN'] = f'https://{parsed.hostname}'
    # Activation is a separate, reviewable step after secret and origin checks.
    config['vars']['MB_REMOTE_ENABLED'] = 'false'
    config['vpc_services'][0]['service_id'] = str(UUID(service_id))
    return config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-origin', required=True)
    parser.add_argument('--service-id', required=True)
    args = parser.parse_args()
    try:
        config = build_config(args.public_origin, args.service_id)
    except ValueError as exc:
        parser.error(str(exc))
    destination = ROOT / 'wrangler.private.jsonc'
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, destination)
    print(json.dumps({'config_prepared': True, 'remote_enabled': False, 'network_calls': 0}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
