#!/bin/sh
# Debian-side client for the native-owned Wi-Fi uplink service boundary.
#
# This helper requests redacted status, the no-confirm denial probe, and a
# future WSTA25 confirmed autoconnect path.  Confirmed autoconnect is fail-closed
# by default and requires both explicit environment gates before it writes a
# request file.  The helper never starts DHCP, ping, routing, or public tunnel
# work itself.

set -u

SERVICE_VERSION="a90-native-wifi-uplink-service-v1"
SERVICE_DIR="${A90_NATIVE_WIFI_UPLINK_SERVICE_DIR:-/tmp/a90-native-wifi-uplink-service}"
TIMEOUT_SEC="${A90_NATIVE_WIFI_UPLINK_SERVICE_TIMEOUT_SEC:-30}"
CONFIRM_VALUE="A90_NATIVE_UPLINK_AUTOCONNECT_V1"
ALLOW_CONFIRMED="${A90_NATIVE_WIFI_UPLINK_ALLOW_CONFIRMED:-0}"
CONFIRM_TOKEN="${A90_NATIVE_WIFI_UPLINK_CONFIRM_TOKEN:-}"

usage() {
    echo "usage: a90-native-wifi-uplink-client [status|autoconnect-no-confirm|autoconnect-confirmed] [service-dir]" >&2
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
confirmed_autoconnect=0
case "$requested_op" in
    status)
        service_op="status"
        expected_decision="wifi-uplink-service-status-pass"
        ;;
    autoconnect-no-confirm)
        service_op="autoconnect"
        expected_decision="wifi-uplink-service-confirm-required"
        ;;
    autoconnect-confirmed)
        service_op="autoconnect"
        expected_decision="wifi-uplink-service-autoconnect-pass"
        confirmed_autoconnect=1
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

if [ "$confirmed_autoconnect" = "1" ]; then
    if [ "$ALLOW_CONFIRMED" != "1" ]; then
        fail 77 "native-wifi-uplink-client-confirmed-disabled" "requested_op=$requested_op"
    fi
    if [ "$CONFIRM_TOKEN" != "$CONFIRM_VALUE" ]; then
        fail 77 "native-wifi-uplink-client-confirm-token-missing" "requested_op=$requested_op"
    fi
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
    if [ "$confirmed_autoconnect" = "1" ]; then
        printf 'confirm=%s\n' "$CONFIRM_VALUE"
    fi
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
        version|seq|op|owner|rc|credentials|connect|dhcp_routing|external_ping_execution|public_tunnel|raw_values_redacted|secret_values_logged|wlan0_present|default_route_present|nameserver_count|autoconnect_ready|autoconnect_enabled|config_profile_present|profile_valid|dhcp|scan_before_connect|retry_count|external_ping_blocked|autoconnect_config_decision|autoconnect_result_present|autoconnect_decision|autoconnect_profile_present|connect_rc|dhcp_rc|final_rc|carrier_up|scan_recovery_attempted|scan_recovery_first_scan_rc|scan_recovery_rc|scan_recovery_rescan_rc|scan_recovery_success|scan_recovery_decision|connect_diag_attempted|connect_diag_decision|connect_wlan0_wait_rc|connect_wlan0_wait_elapsed_ms|connect_link_up_rc|connect_link_up_errno|connect_prepare_rc|connect_runtime_prepare_rc|connect_supplicant_root_exec_rc|connect_supplicant_process_count_before|connect_supplicant_start_rc|connect_ctrl_wait_rc|connect_ctrl_wait_errno|connect_ctrl_wait_elapsed_ms|connect_ctrl_wait_category|connect_ctrl_driver_country_rc|connect_ctrl_scan_rc|connect_ctrl_enable_network_rc|connect_ctrl_select_network_rc|connect_ctrl_reassociate_rc|connect_carrier_wait_rc|connect_carrier_wait_elapsed_ms|connect_carrier_up_at_wait|connect_ctrl_status_rc|connect_ctrl_status_errno|connect_ctrl_status_wpa_state|connect_ctrl_status_completed|connect_ctrl_signal_rc|connect_ctrl_signal_errno|connect_supplicant_spawned|connect_supplicant_left_running|connect_cleanup_status|decision)
            printf '%s=%s\n' "$key" "$value"
            ;;
        requested_profile_present)
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
