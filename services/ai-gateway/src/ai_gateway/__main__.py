"""Run the gateway: ``uv run beetle-ai-gateway`` (reads .env / environment)."""

from __future__ import annotations

import logging
import sys

import uvicorn
from pydantic import ValidationError

from .config import Settings, is_loopback
from .main import create_app


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        settings = Settings()  # type: ignore[call-arg]
    except ValidationError as e:
        print(f"Invalid gateway configuration:\n{e}", file=sys.stderr)
        return 2
    if not settings.tls_enabled and not is_loopback(settings.gateway_host):
        print(
            "Refusing to listen on a non-loopback address without TLS. Set GATEWAY_TLS_CERT/GATEWAY_TLS_KEY "
            "(see `make gateway-cert`) or bind to 127.0.0.1.",
            file=sys.stderr,
        )
        return 2
    uvicorn.run(
        create_app(settings),
        host=settings.gateway_host,
        port=settings.gateway_port,
        ssl_certfile=settings.gateway_tls_cert,
        ssl_keyfile=settings.gateway_tls_key,
        proxy_headers=False,
        server_header=False,
        access_log=False,  # request bodies contain breeding data; never log them
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
