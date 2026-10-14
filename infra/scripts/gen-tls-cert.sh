#!/usr/bin/env bash
# Creates a self-signed TLS certificate for the Mac AI Gateway and prints the
# SHA-256 fingerprint to pin in the app. Output goes to infra/tls/ (git-ignored).
#   usage: infra/scripts/gen-tls-cert.sh [hostname] [ip]
set -euo pipefail
HOST="${1:-$(scutil --get LocalHostName 2>/dev/null || hostname -s).local}"
IP="${2:-}"
DIR="$(cd "$(dirname "$0")/../.." && pwd)/infra/tls"
mkdir -p "$DIR" && chmod 700 "$DIR"
SAN="DNS:${HOST},DNS:localhost,IP:127.0.0.1"
[[ -n "$IP" ]] && SAN="${SAN},IP:${IP}"
openssl req -x509 -newkey rsa:3072 -sha256 -days 825 -nodes \
  -keyout "$DIR/gateway.key" -out "$DIR/gateway.crt" \
  -subj "/CN=${HOST}" -addext "subjectAltName=${SAN}" >/dev/null 2>&1
chmod 600 "$DIR/gateway.key"
echo "Certificate: $DIR/gateway.crt"
echo "Key:         $DIR/gateway.key"
echo "SAN:         $SAN"
echo "SHA-256 fingerprint (paste into the app):"
openssl x509 -in "$DIR/gateway.crt" -noout -fingerprint -sha256 | cut -d= -f2
