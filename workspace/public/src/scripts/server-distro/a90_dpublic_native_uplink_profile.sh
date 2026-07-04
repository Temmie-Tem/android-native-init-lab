#!/bin/sh
# D-public appliance profile for the native-owned Wi-Fi uplink path.
#
# This helper is intentionally a policy shim.  It never starts DHCP, routing,
# cloudflared, or any public listener itself.  It only records the appliance
# default state and, when explicitly enabled, delegates confirmed STA uplink to
# the native-owned uplink client.

set -u
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

PROFILE_VERSION=1
CLIENT="${A90_DPUBLIC_NATIVE_UPLINK_CLIENT:-/usr/local/bin/a90-native-wifi-uplink-client}"
SERVICE_DIR="${A90_NATIVE_WIFI_UPLINK_SERVICE_DIR:-/tmp/a90-native-wifi-uplink-service}"
ENABLE_FILE="${A90_DPUBLIC_NATIVE_UPLINK_ENABLE:-/etc/a90-dpublic/native-uplink-enable}"
QUICK_TUNNEL_ENABLE="${A90_DPUBLIC_QUICK_TUNNEL_ENABLE:-/etc/a90-dpublic/cloudflared-quick-enable}"
MARKER="${A90_DPUBLIC_NATIVE_UPLINK_PROFILE_MARKER:-/run/a90-dpublic/native-uplink-profile.marker}"
CONFIRM_VALUE="A90_NATIVE_UPLINK_AUTOCONNECT_V1"

marker_dir=$(dirname "$MARKER")
mkdir -p "$marker_dir" 2>/dev/null || true

emit() {
    line=$1
    printf '%s\n' "$line"
    if [ -d "$marker_dir" ]; then
        printf '%s\n' "$line" >> "$MARKER" 2>/dev/null || true
    fi
}

emit_common() {
    op=$1
    emit "native_uplink_profile_version=$PROFILE_VERSION"
    emit "native_uplink_profile_owner=debian-appliance"
    emit "native_uplink_profile_native_owner=native-init"
    emit "native_uplink_profile_requested_op=$op"
    emit "native_uplink_profile_client_present=$([ -x "$CLIENT" ] && echo 1 || echo 0)"
    emit "native_uplink_profile_enable_present=$([ -s "$ENABLE_FILE" ] && echo 1 || echo 0)"
    emit "native_uplink_profile_public_default=off"
    emit "native_uplink_profile_quick_tunnel_enable_present=$([ -s "$QUICK_TUNNEL_ENABLE" ] && echo 1 || echo 0)"
    emit "native_uplink_profile_wsta43_sequence_required=1"
    emit "native_uplink_profile_secret_values_logged=0"
}

fail() {
    rc=$1
    decision=$2
    op=$3
    emit_common "$op"
    emit "native_uplink_profile_decision=$decision"
    exit "$rc"
}

op="${1:-profile}"
case "$op" in
    profile|preflight)
        emit_common "$op"
        emit "native_uplink_profile_decision=native-uplink-profile-ready"
        exit 0
        ;;
    native-status)
        [ -x "$CLIENT" ] || fail 70 "native-uplink-profile-client-missing" "$op"
        emit_common "$op"
        "$CLIENT" status "$SERVICE_DIR"
        rc=$?
        emit "native_uplink_profile_client_rc=$rc"
        if [ "$rc" = "0" ]; then
            emit "native_uplink_profile_decision=native-uplink-profile-native-status-pass"
        else
            emit "native_uplink_profile_decision=native-uplink-profile-native-status-failed"
        fi
        exit "$rc"
        ;;
    autoconnect-confirmed)
        [ -x "$CLIENT" ] || fail 70 "native-uplink-profile-client-missing" "$op"
        [ -s "$ENABLE_FILE" ] || fail 77 "native-uplink-profile-enable-missing" "$op"
        if [ "${A90_NATIVE_WIFI_UPLINK_ALLOW_CONFIRMED:-0}" != "1" ]; then
            fail 77 "native-uplink-profile-confirmed-disabled" "$op"
        fi
        if [ "${A90_NATIVE_WIFI_UPLINK_CONFIRM_TOKEN:-}" != "$CONFIRM_VALUE" ]; then
            fail 77 "native-uplink-profile-confirm-token-missing" "$op"
        fi
        emit_common "$op"
        "$CLIENT" autoconnect-confirmed "$SERVICE_DIR"
        rc=$?
        emit "native_uplink_profile_client_rc=$rc"
        if [ "$rc" = "0" ]; then
            emit "native_uplink_profile_decision=native-uplink-profile-autoconnect-pass"
        else
            emit "native_uplink_profile_decision=native-uplink-profile-autoconnect-failed"
        fi
        exit "$rc"
        ;;
    quick-tunnel|public-tunnel)
        emit_common "$op"
        if [ ! -s "$QUICK_TUNNEL_ENABLE" ]; then
            emit "native_uplink_profile_decision=native-uplink-profile-public-tunnel-disabled"
            exit 77
        fi
        emit "native_uplink_profile_decision=native-uplink-profile-public-tunnel-host-orchestrated-required"
        emit "native_uplink_profile_public_runner=wsta43"
        exit 77
        ;;
    *)
        fail 64 "native-uplink-profile-unknown-op" "$op"
        ;;
esac
