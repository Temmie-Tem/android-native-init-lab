#!/bin/sh
set -u

PATH=/usr/sbin:/usr/bin:/sbin:/bin
RUN_DIR=/run/a90-wifi
READY=$RUN_DIR/ready
READY_TMP=$RUN_DIR/ready.tmp
FAILURE=$RUN_DIR/failure
FAILURE_TMP=$RUN_DIR/failure.tmp
BRIDGE=/run/a90-native-wifi
STATUS=$BRIDGE/status
RESOLV=$BRIDGE/resolv.conf
COMPANION=$BRIDGE/companion
IFACE=wlan0
MAX_POLLS=90
IP=/usr/bin/ip
STAT=/usr/bin/stat
GREP=/usr/bin/grep
AWK=/usr/bin/awk
MOUNT=/bin/mount
FINDMNT=/usr/bin/findmnt

umask 077
mkdir -p "$RUN_DIR" || exit 80
rm -f "$READY" "$READY_TMP" "$FAILURE" "$FAILURE_TMP"

fail() {
  code=$1
  reason=$2
  {
    echo schema=a90-debian-wifi-handoff-v1-failure
    echo owner=debian-observer-native-control-plane
    echo reason="$reason"
    echo code="$code"
    echo ncm_ssh_affected=0
  } > "$FAILURE_TMP"
  mv "$FAILURE_TMP" "$FAILURE"
  exit "$code"
}

health_value() {
  key=$1
  "$AWK" -F= -v key="$key" '
    $1 == key {
      count += 1
      value = $2
    }
    END {
      if (count != 1 || value !~ /^[A-Za-z0-9._-]+$/) {
        exit 1
      }
      print value
    }
  ' "$COMPANION"
}

poll=0
while [ "$poll" -lt "$MAX_POLLS" ]; do
  if [ -d "/sys/class/net/$IFACE" ] &&
     [ ! -L "$STATUS" ] && [ -f "$STATUS" ] &&
     "$GREP" -qx 'schema=a90-native-wifi-handoff-v1' "$STATUS" &&
     "$GREP" -qx 'decision=wifi-autoconnect-pass' "$STATUS" &&
     "$GREP" -qx 'final_rc=0' "$STATUS" &&
     "$GREP" -qx 'carrier_up=1' "$STATUS" &&
     "$GREP" -qx 'default_route_present=1' "$STATUS" &&
     "$GREP" -qx 'resolv_conf_present=1' "$STATUS" &&
     [ ! -L "$COMPANION" ] && [ -f "$COMPANION" ] &&
     "$GREP" -qx 'schema=a90-wifi-companion-health-v1' "$COMPANION" &&
     "$GREP" -qx 'state=healthy' "$COMPANION" &&
     "$GREP" -qx 'required_children=alive' "$COMPANION" &&
     "$GREP" -qx 'modem_holder=alive' "$COMPANION" &&
     "$GREP" -qx 'wlan0=present' "$COMPANION" &&
     [ "$(cat "/sys/class/net/$IFACE/carrier" 2>/dev/null || true)" = 1 ] &&
     "$IP" route show default dev "$IFACE" 2>/dev/null | "$GREP" -q '^default ' &&
     [ ! -L "$RESOLV" ] && [ -s "$RESOLV" ]; then
    break
  fi
  poll=$((poll + 1))
  sleep 1
done
[ "$poll" -lt "$MAX_POLLS" ] || fail 81 wifi-handoff-timeout

RESOLV_META=$("$STAT" -c '%u:%g:%a' "$RESOLV" 2>/dev/null || true)
[ "$RESOLV_META" = 0:0:600 ] || fail 82 resolver-metadata-mismatch
COMPANION_META=$("$STAT" -c '%u:%g:%a' "$COMPANION" 2>/dev/null || true)
[ "$COMPANION_META" = 0:0:600 ] || fail 86 companion-metadata-mismatch
COMPANION_PID_1=$(health_value pid 2>/dev/null || true)
COMPANION_SEQ_1=$(health_value sequence 2>/dev/null || true)
case "$COMPANION_PID_1:$COMPANION_SEQ_1" in
  *[!0-9:]*|:|*:) fail 87 companion-health-invalid ;;
esac
[ "$COMPANION_PID_1" -gt 1 ] || fail 87 companion-pid-invalid
kill -0 "$COMPANION_PID_1" 2>/dev/null || fail 87 companion-not-alive
sleep 3
"$GREP" -qx 'schema=a90-wifi-companion-health-v1' "$COMPANION" ||
  fail 88 companion-health-schema-changed
"$GREP" -qx 'state=healthy' "$COMPANION" ||
  fail 88 companion-health-state-changed
"$GREP" -qx 'required_children=alive' "$COMPANION" ||
  fail 88 companion-children-not-alive
"$GREP" -qx 'modem_holder=alive' "$COMPANION" ||
  fail 88 companion-modem-holder-not-alive
"$GREP" -qx 'wlan0=present' "$COMPANION" ||
  fail 88 companion-wlan0-not-present
COMPANION_PID_2=$(health_value pid 2>/dev/null || true)
COMPANION_SEQ_2=$(health_value sequence 2>/dev/null || true)
case "$COMPANION_PID_2:$COMPANION_SEQ_2" in
  *[!0-9:]*|:|*:) fail 88 companion-health-invalid-after-wait ;;
esac
[ "$COMPANION_PID_2" = "$COMPANION_PID_1" ] ||
  fail 88 companion-pid-changed
[ "$COMPANION_SEQ_2" -gt "$COMPANION_SEQ_1" ] ||
  fail 88 companion-health-not-advancing
kill -0 "$COMPANION_PID_2" 2>/dev/null ||
  fail 88 companion-not-alive-after-wait
[ "$(cat "/sys/class/net/$IFACE/carrier" 2>/dev/null || true)" = 1 ] ||
  fail 88 carrier-lost-during-health-check
"$IP" route show default dev "$IFACE" 2>/dev/null | "$GREP" -q '^default ' ||
  fail 88 default-route-lost-during-health-check
NAMESERVER_COUNT=$("$AWK" '$1 == "nameserver" && NF == 2 { count += 1 } END { print count + 0 }' "$RESOLV")
[ "$NAMESERVER_COUNT" -gt 0 ] || fail 82 resolver-empty
[ ! -L /etc/resolv.conf ] && [ -f /etc/resolv.conf ] || fail 83 resolver-target-not-regular
"$MOUNT" --bind "$RESOLV" /etc/resolv.conf || fail 84 resolver-bind-failed
if ! "$MOUNT" -o remount,bind,ro,nosuid,nodev,noexec /etc/resolv.conf; then
  "$MOUNT" -o remount,bind,ro /etc/resolv.conf >/dev/null 2>&1 || true
  fail 84 resolver-harden-failed
fi
MOUNT_STATE=$("$FINDMNT" -n -o OPTIONS --target /etc/resolv.conf 2>/dev/null || true)
case ",$MOUNT_STATE," in
  *,ro,*) ;;
  *) fail 85 resolver-not-read-only ;;
esac

{
  echo schema=a90-debian-wifi-handoff-v1-ready
  echo owner=debian-observer-native-control-plane
  echo control_plane=native-private-mount-namespace
  echo network_namespace=shared
  echo wlan_ifname="$IFACE"
  echo carrier_up=1
  echo default_route_present=1
  echo resolver_source=native-redacted-handoff
  echo resolver_read_only=1
  echo nameserver_count="$NAMESERVER_COUNT"
  echo companion_health=1
  echo companion_sequence_advanced=1
  echo poll_count="$poll"
  echo ncm_ssh_affected=0
} > "$READY_TMP"
mv "$READY_TMP" "$READY"
rm -f "$FAILURE" "$FAILURE_TMP"
exit 0
