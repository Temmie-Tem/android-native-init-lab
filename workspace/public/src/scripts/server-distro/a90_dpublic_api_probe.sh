#!/bin/sh
# D-public API/DNS probe for WSTA9.
#
# This intentionally does not start cloudflared or expose a local service.  It
# tests the quick-tunnel API path independently and records only booleans/return
# codes in the public marker.  Raw API responses may contain generated tunnel
# hostnames/secrets, so they stay in /run/a90-dpublic with mode 0600.
set +e
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

RUN_DIR=/run/a90-dpublic
MARKER=/run/a90-d3-marker
API_HOST=api.trycloudflare.com
API_URL=https://api.trycloudflare.com/tunnel
CONTROL_HOST=cloudflare.com
WGET_RESPONSE=$RUN_DIR/api-probe-wget-response.json
WGET_LOG=$RUN_DIR/api-probe-wget.log
OPENSSL_RESPONSE=$RUN_DIR/api-probe-openssl-response.txt
OPENSSL_LOG=$RUN_DIR/api-probe-openssl.log
OPENSSL_REQUEST=$RUN_DIR/api-probe-openssl-request.txt
NC_BIN=

append_marker() {
  [ -f "$MARKER" ] && echo "$1" >> "$MARKER"
}

default_route_iface() {
  ip route show default 2>/dev/null |
    awk '/^default / { for (i = 1; i <= NF; i++) if ($i == "dev") { print $(i + 1); exit } }'
}

nameserver_count() {
  awk '$1 == "nameserver" { n++ } END { print n + 0 }' /etc/resolv.conf 2>/dev/null
}

json_success_true() {
  grep -q '"success"[[:space:]]*:[[:space:]]*true' "$1" 2>/dev/null
}

json_hostname_present() {
  grep -q '"hostname"[[:space:]]*:' "$1" 2>/dev/null
}

probe_tcp() {
  host=$1
  if [ -z "$NC_BIN" ]; then
    return 99
  fi
  "$NC_BIN" -z -w 8 "$host" 443 >/dev/null 2>&1
  return $?
}

mkdir -p "$RUN_DIR"
rm -f "$WGET_RESPONSE" "$WGET_LOG" "$OPENSSL_RESPONSE" "$OPENSSL_LOG" "$OPENSSL_REQUEST" 2>/dev/null || true

append_marker "api_probe_started=1"
route_iface=$(default_route_iface)
[ -n "$route_iface" ] || route_iface=none
append_marker "api_probe_default_route_iface=$route_iface"
append_marker "api_probe_resolv_nameserver_count=$(nameserver_count)"

getent hosts "$CONTROL_HOST" >/dev/null 2>&1
control_dns_rc=$?
getent hosts "$API_HOST" >/dev/null 2>&1
api_dns_rc=$?
append_marker "api_probe_dns_control_rc=$control_dns_rc"
append_marker "api_probe_dns_api_rc=$api_dns_rc"

NC_BIN=$(command -v nc 2>/dev/null || command -v nc.openbsd 2>/dev/null || true)
if [ -n "$NC_BIN" ]; then
  append_marker "api_probe_tcp_tool=$(basename "$NC_BIN")"
else
  append_marker "api_probe_tcp_tool=none"
fi
probe_tcp "$CONTROL_HOST"
control_tcp_rc=$?
probe_tcp "$API_HOST"
api_tcp_rc=$?
append_marker "api_probe_tcp_control_rc=$control_tcp_rc"
append_marker "api_probe_tcp_api_rc=$api_tcp_rc"

wget_present=0
wget_post_attempted=0
wget_post_rc=99
wget_success_json=0
wget_hostname_present=0
if command -v wget >/dev/null 2>&1; then
  wget_present=1
  wget_post_attempted=1
  wget --timeout=25 --no-check-certificate --post-data='' \
    -O "$WGET_RESPONSE" "$API_URL" > "$WGET_LOG" 2>&1
  wget_post_rc=$?
  chmod 600 "$WGET_RESPONSE" "$WGET_LOG" 2>/dev/null || true
  if json_success_true "$WGET_RESPONSE"; then
    wget_success_json=1
  fi
  if json_hostname_present "$WGET_RESPONSE"; then
    wget_hostname_present=1
  fi
fi
append_marker "api_probe_wget_present=$wget_present"
append_marker "api_probe_wget_post_attempted=$wget_post_attempted"
append_marker "api_probe_wget_post_rc=$wget_post_rc"
append_marker "api_probe_wget_success_json=$wget_success_json"
append_marker "api_probe_wget_hostname_present=$wget_hostname_present"

openssl_present=0
openssl_post_attempted=0
openssl_post_rc=99
openssl_http200=0
openssl_success_json=0
openssl_hostname_present=0
if command -v openssl >/dev/null 2>&1; then
  openssl_present=1
  openssl_post_attempted=1
  {
    printf 'POST /tunnel HTTP/1.1\r\n'
    printf 'Host: %s\r\n' "$API_HOST"
    printf 'User-Agent: a90-dpublic-api-probe\r\n'
    printf 'Content-Type: application/json\r\n'
    printf 'Content-Length: 0\r\n'
    printf 'Connection: close\r\n'
    printf '\r\n'
  } > "$OPENSSL_REQUEST"
  timeout 25 openssl s_client -connect "$API_HOST:443" -servername "$API_HOST" \
    -quiet < "$OPENSSL_REQUEST" > "$OPENSSL_RESPONSE" 2> "$OPENSSL_LOG"
  openssl_post_rc=$?
  chmod 600 "$OPENSSL_REQUEST" "$OPENSSL_RESPONSE" "$OPENSSL_LOG" 2>/dev/null || true
  if grep -q '^HTTP/1\.[01] 200' "$OPENSSL_RESPONSE" 2>/dev/null; then
    openssl_http200=1
  fi
  if json_success_true "$OPENSSL_RESPONSE"; then
    openssl_success_json=1
  fi
  if json_hostname_present "$OPENSSL_RESPONSE"; then
    openssl_hostname_present=1
  fi
fi
append_marker "api_probe_openssl_present=$openssl_present"
append_marker "api_probe_openssl_post_attempted=$openssl_post_attempted"
append_marker "api_probe_openssl_post_rc=$openssl_post_rc"
append_marker "api_probe_openssl_http200=$openssl_http200"
append_marker "api_probe_openssl_success_json=$openssl_success_json"
append_marker "api_probe_openssl_hostname_present=$openssl_hostname_present"

if [ "$wget_success_json" = "1" ] || [ "$openssl_success_json" = "1" ]; then
  decision=api-post-pass
elif [ "$api_dns_rc" != "0" ]; then
  decision=api-dns-failed
elif [ "$api_tcp_rc" != "0" ]; then
  decision=api-tcp-failed
elif [ "$wget_post_attempted" = "1" ] || [ "$openssl_post_attempted" = "1" ]; then
  decision=api-post-failed
else
  decision=api-tools-missing
fi
append_marker "api_probe_decision=$decision"
append_marker "api_probe_secret_values_logged=0"

exit 0
