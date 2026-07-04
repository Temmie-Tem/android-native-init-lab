#!/bin/sh
# Debian-side client for the native-owned Wi-Fi uplink service boundary.
#
# This helper only requests redacted status and the no-confirm denial probe. It
# never supplies the autoconnect confirm token and never starts association,
# DHCP, ping, routing, or public tunnel work.

set -u

SERVICE_VERSION="a90-native-wifi-uplink-service-v1"
SERVICE_DIR="${A90_NATIVE_WIFI_UPLINK_SERVICE_DIR:-/tmp/a90-native-wifi-uplink-service}"
TIMEOUT_SEC="${A90_NATIVE_WIFI_UPLINK_SERVICE_TIMEOUT_SEC:-30}"

usage() {
    echo "usage: a90-native-wifi-uplink-client [status|autoconnect-no-confirm] [service-dir]" >&2
}

fail() {
    rc="$1"
    decision="$2"
    shift 2
    echo "native_wifi_uplink_client_version=1"
    echo "native_wifi_uplink_client_decision=$decision"
    echo "native_wifi_uplink_client_secret_values_logged=0"
    for line in "$@"; do
        echo "$line"
    done
    exit "$rc"
}

requested_op="${1:-}"
case "$requested_op" in
    status)
        service_op="status"
        expected_decision="wifi-uplink-service-status-pass"
        ;;
    autoconnect-no-confirm)
        service_op="autoconnect"
        expected_decision="wifi-uplink-service-confirm-required"
        ;;
    autoconnect|connect|associate|association|dhcp|ping|public-tunnel|tunnel|confirmed-autoconnect)
        fail 64 "native-wifi-uplink-client-op-denied" "requested_op=$requested_op"
        ;;
    ""|-h|--help|help)
        usage
        fail 64 "native-wifi-uplink-client-usage"
        ;;
    *)
        usage
        fail 64 "native-wifi-uplink-client-unknown-op" "requested_op=$requested_op"
        ;;
esac

if [ "${2:-}" ]; then
    SERVICE_DIR="$2"
fi

case "$TIMEOUT_SEC" in
    ""|*[!0-9]*)
        fail 64 "native-wifi-uplink-client-bad-timeout"
        ;;
esac

if ! mkdir -p "$SERVICE_DIR"; then
    fail 70 "native-wifi-uplink-client-service-dir-failed"
fi

seq_value="$(date +%s 2>/dev/null || echo 0)$$"
request_tmp="$SERVICE_DIR/request.tmp.$$"
request="$SERVICE_DIR/request"
response="$SERVICE_DIR/response"

rm -f "$response" "$SERVICE_DIR/response.tmp" "$request_tmp"
if ! {
    printf 'seq=%s\n' "$seq_value"
    printf 'op=%s\n' "$service_op"
} > "$request_tmp"; then
    rm -f "$request_tmp"
    fail 70 "native-wifi-uplink-client-request-write-failed"
fi
if ! mv "$request_tmp" "$request"; then
    rm -f "$request_tmp"
    fail 70 "native-wifi-uplink-client-request-publish-failed"
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
    fail 75 "native-wifi-uplink-client-response-timeout" "seq=$seq_value" "op=$service_op"
fi

version=""
response_seq=""
response_op=""
owner=""
decision=""
native_rc=""

echo "native_wifi_uplink_client_version=1"
echo "native_wifi_uplink_client_response_ready=1"
echo "native_wifi_uplink_client_requested_op=$requested_op"
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
        version|seq|op|owner|rc|credentials|connect|dhcp_routing|external_ping_execution|public_tunnel|raw_values_redacted|secret_values_logged|wlan0_present|default_route_present|nameserver_count|autoconnect_ready|autoconnect_enabled|config_profile_present|profile_valid|dhcp|scan_before_connect|retry_count|external_ping_blocked|autoconnect_config_decision|autoconnect_result_present|autoconnect_decision|autoconnect_profile_present|connect_rc|dhcp_rc|final_rc|carrier_up|decision)
            printf '%s=%s\n' "$key" "$value"
            ;;
    esac
done < "$response"
echo "native_wifi_uplink_client_secret_values_logged=0"

if [ "$version" != "$SERVICE_VERSION" ]; then
    echo "native_wifi_uplink_client_decision=native-wifi-uplink-client-bad-version"
    exit 76
fi
if [ "$response_seq" != "$seq_value" ] || [ "$response_op" != "$service_op" ]; then
    echo "native_wifi_uplink_client_decision=native-wifi-uplink-client-response-mismatch"
    exit 76
fi
if [ "$owner" != "native-init" ]; then
    echo "native_wifi_uplink_client_decision=native-wifi-uplink-client-bad-owner"
    exit 76
fi
if [ "$decision" = "$expected_decision" ]; then
    echo "native_wifi_uplink_client_decision=native-wifi-uplink-client-pass"
    exit 0
fi

echo "native_wifi_uplink_client_native_rc=$native_rc"
echo "native_wifi_uplink_client_decision=native-wifi-uplink-client-native-failed"
exit 10
