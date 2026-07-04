#!/bin/sh
# Debian-side client for the native-owned Wi-Fi service boundary.
#
# This helper only requests native-owned status/scan observations.  It does not
# start association, DHCP, ping, routing, or public tunnel work.

set -u

SERVICE_VERSION="a90-native-wifi-service-v1"
SERVICE_DIR="${A90_NATIVE_WIFI_SERVICE_DIR:-/tmp/a90-native-wifi-service}"
TIMEOUT_SEC="${A90_NATIVE_WIFI_SERVICE_TIMEOUT_SEC:-30}"
SCAN_DELAY_MS="${A90_NATIVE_WIFI_SERVICE_SCAN_DELAY_MS:-5000}"

usage() {
    echo "usage: a90-native-wifi-service-client [status|scan] [service-dir]" >&2
}

fail() {
    rc="$1"
    decision="$2"
    shift 2
    echo "native_wifi_service_client_version=1"
    echo "native_wifi_service_client_decision=$decision"
    echo "native_wifi_service_client_secret_values_logged=0"
    for line in "$@"; do
        echo "$line"
    done
    exit "$rc"
}

op="${1:-}"
case "$op" in
    status|scan)
        ;;
    connect|associate|association|dhcp|ping|public-tunnel|tunnel)
        fail 64 "native-wifi-service-op-denied" "requested_op=$op"
        ;;
    ""|-h|--help|help)
        usage
        fail 64 "native-wifi-service-client-usage"
        ;;
    *)
        usage
        fail 64 "native-wifi-service-client-unknown-op" "requested_op=$op"
        ;;
esac

if [ "${2:-}" ]; then
    SERVICE_DIR="$2"
fi

case "$TIMEOUT_SEC" in
    ""|*[!0-9]*)
        fail 64 "native-wifi-service-client-bad-timeout"
        ;;
esac
case "$SCAN_DELAY_MS" in
    ""|*[!0-9]*)
        fail 64 "native-wifi-service-client-bad-scan-delay"
        ;;
esac

if ! mkdir -p "$SERVICE_DIR"; then
    fail 70 "native-wifi-service-client-service-dir-failed"
fi

seq_value="$(date +%s 2>/dev/null || echo 0)$$"
request_tmp="$SERVICE_DIR/request.tmp.$$"
request="$SERVICE_DIR/request"
response="$SERVICE_DIR/response"

rm -f "$response" "$SERVICE_DIR/response.tmp" "$request_tmp"
if ! {
    printf 'seq=%s\n' "$seq_value"
    printf 'op=%s\n' "$op"
    printf 'scan_delay_ms=%s\n' "$SCAN_DELAY_MS"
} > "$request_tmp"; then
    rm -f "$request_tmp"
    fail 70 "native-wifi-service-client-request-write-failed"
fi
if ! mv "$request_tmp" "$request"; then
    rm -f "$request_tmp"
    fail 70 "native-wifi-service-client-request-publish-failed"
fi

elapsed=0
while [ "$elapsed" -lt "$TIMEOUT_SEC" ]; do
    if [ -f "$response" ] && grep -q "^seq=$seq_value\$" "$response"; then
        break
    fi
    elapsed=$((elapsed + 1))
    sleep 1
done

if [ ! -f "$response" ] || ! grep -q "^seq=$seq_value\$" "$response"; then
    fail 75 "native-wifi-service-client-response-timeout" "seq=$seq_value" "op=$op"
fi

version=""
response_seq=""
response_op=""
owner=""
decision=""
native_rc=""

echo "native_wifi_service_client_version=1"
echo "native_wifi_service_client_response_ready=1"
while IFS= read -r line; do
    case "$line" in
        *=*)
            key="${line%%=*}"
            value="${line#*=}"
            ;;
        *)
            continue
            ;;
    esac
    case "$key" in
        version) version="$value" ;;
        seq) response_seq="$value" ;;
        op) response_op="$value" ;;
        owner) owner="$value" ;;
        rc) native_rc="$value" ;;
        decision) decision="$value" ;;
    esac
    case "$key" in
        version|seq|op|owner|rc|wlan0_present|wlan0_ifindex|wlan0_flags|supplicant_process_count|dhcp_routing|public_tunnel|credentials|connect|raw_results_redacted|scan_result_count|decision)
            printf '%s=%s\n' "$key" "$value"
            ;;
    esac
done < "$response"
echo "native_wifi_service_client_secret_values_logged=0"

if [ "$version" != "$SERVICE_VERSION" ]; then
    echo "native_wifi_service_client_decision=native-wifi-service-client-bad-version"
    exit 76
fi
if [ "$response_seq" != "$seq_value" ] || [ "$response_op" != "$op" ]; then
    echo "native_wifi_service_client_decision=native-wifi-service-client-response-mismatch"
    exit 76
fi
if [ "$owner" != "native-init" ]; then
    echo "native_wifi_service_client_decision=native-wifi-service-client-bad-owner"
    exit 76
fi

case "$op:$decision" in
    status:wifi-service-status-pass|scan:wifi-scan-pass)
        echo "native_wifi_service_client_decision=native-wifi-service-client-pass"
        exit 0
        ;;
esac

echo "native_wifi_service_client_native_rc=$native_rc"
echo "native_wifi_service_client_decision=native-wifi-service-client-native-failed"
exit 10
