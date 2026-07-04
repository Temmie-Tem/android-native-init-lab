#!/bin/sh
# D-public packet-filter helper.
#
# This helper is staged for bounded live prototypes.  It is never invoked by
# firstboot automatically.  The apply path saves the current filter tables before
# loading a loopback-only default-drop policy; restore uses those saved tables.

set -u
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

HELPER_VERSION=1
IPT4="${A90_DPUBLIC_IPTABLES4:-/usr/sbin/iptables-legacy}"
IPT6="${A90_DPUBLIC_IPTABLES6:-/usr/sbin/ip6tables-legacy}"
SAVE4="${A90_DPUBLIC_IPTABLES_SAVE4:-/usr/sbin/iptables-legacy-save}"
SAVE6="${A90_DPUBLIC_IPTABLES_SAVE6:-/usr/sbin/ip6tables-legacy-save}"
RESTORE4="${A90_DPUBLIC_IPTABLES_RESTORE4:-/usr/sbin/iptables-legacy-restore}"
RESTORE6="${A90_DPUBLIC_IPTABLES_RESTORE6:-/usr/sbin/ip6tables-legacy-restore}"
RUN_DIR="${A90_DPUBLIC_PACKET_FILTER_RUN_DIR:-/run/a90-dpublic/packet-filter}"
MARKER="${A90_DPUBLIC_PACKET_FILTER_MARKER:-/run/a90-dpublic/packet-filter.marker}"
BEFORE4="$RUN_DIR/before.v4"
BEFORE6="$RUN_DIR/before.v6"

mkdir -p "$RUN_DIR" "$(dirname "$MARKER")" 2>/dev/null || true

emit() {
    line=$1
    printf '%s\n' "$line"
    printf '%s\n' "$line" >> "$MARKER" 2>/dev/null || true
}

emit_common() {
    op=$1
    emit "packet_filter_helper_version=$HELPER_VERSION"
    emit "packet_filter_backend=legacy-iptables"
    emit "packet_filter_requested_op=$op"
    emit "packet_filter_policy_class=loopback-default-drop"
    emit "packet_filter_secret_values_logged=0"
}

fail() {
    rc=$1
    decision=$2
    op=$3
    emit_common "$op"
    emit "packet_filter_decision=$decision"
    exit "$rc"
}

require_tools() {
    for tool in "$IPT4" "$IPT6" "$SAVE4" "$SAVE6" "$RESTORE4" "$RESTORE6"; do
        [ -x "$tool" ] || return 1
    done
    return 0
}

save_current_rules() {
    umask 077
    "$SAVE4" > "$BEFORE4" || return 1
    "$SAVE6" > "$BEFORE6" || return 1
    chmod 600 "$BEFORE4" "$BEFORE6" 2>/dev/null || true
    return 0
}

apply_v4() {
    "$RESTORE4" <<'EOF'
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -i lo -j ACCEPT
-A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
COMMIT
EOF
}

apply_v6() {
    "$RESTORE6" <<'EOF'
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]
-A INPUT -i lo -j ACCEPT
-A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
COMMIT
EOF
}

restore_saved_rules() {
    [ -s "$BEFORE4" ] || return 1
    [ -s "$BEFORE6" ] || return 1
    "$RESTORE4" < "$BEFORE4" || return 1
    "$RESTORE6" < "$BEFORE6" || return 1
    return 0
}

op="${1:-preflight}"
case "$op" in
    preflight)
        require_tools || fail 70 "packet-filter-tools-missing" "$op"
        emit_common "$op"
        emit "packet_filter_apply_autostart=0"
        emit "packet_filter_restore_available=$([ -s "$BEFORE4" ] && [ -s "$BEFORE6" ] && echo 1 || echo 0)"
        emit "packet_filter_decision=packet-filter-preflight-pass"
        exit 0
        ;;
    apply-loopback-default-drop)
        require_tools || fail 70 "packet-filter-tools-missing" "$op"
        emit_common "$op"
        save_current_rules || fail 71 "packet-filter-save-before-failed" "$op"
        if apply_v4 && apply_v6; then
            emit "packet_filter_saved_before=1"
            emit "packet_filter_loopback_accept=1"
            emit "packet_filter_input_default=DROP"
            emit "packet_filter_forward_default=DROP"
            emit "packet_filter_output_default=ACCEPT"
            emit "packet_filter_decision=packet-filter-loopback-default-drop-applied"
            exit 0
        fi
        restore_saved_rules >/dev/null 2>&1 || true
        fail 72 "packet-filter-apply-failed-restored" "$op"
        ;;
    restore)
        require_tools || fail 70 "packet-filter-tools-missing" "$op"
        emit_common "$op"
        restore_saved_rules || fail 78 "packet-filter-restore-missing-or-failed" "$op"
        emit "packet_filter_decision=packet-filter-restored"
        exit 0
        ;;
    status)
        require_tools || fail 70 "packet-filter-tools-missing" "$op"
        emit_common "$op"
        emit "packet_filter_ipv4_rules_begin"
        "$IPT4" -S 2>/dev/null || true
        emit "packet_filter_ipv4_rules_end"
        emit "packet_filter_ipv6_rules_begin"
        "$IPT6" -S 2>/dev/null || true
        emit "packet_filter_ipv6_rules_end"
        emit "packet_filter_decision=packet-filter-status-observed"
        exit 0
        ;;
    *)
        fail 64 "packet-filter-unknown-op" "$op"
        ;;
esac
