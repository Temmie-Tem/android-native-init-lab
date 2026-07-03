#!/bin/sh
# Optional Debian-owned Wi-Fi STA bring-up for the D-public appliance.
#
# This helper intentionally consumes a wpa_supplicant config file without
# parsing or printing its contents. Public evidence should contain only booleans,
# return codes, interface names, and secret_values_logged=0.
set +e
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

IFACE=wlan0
RUN_DIR=/run/a90-dpublic
MARKER=/run/a90-d3-marker
ENABLE=/etc/a90-dpublic/wifi-sta-enable
CONFIG=/etc/a90-dpublic/wpa_supplicant-wlan0.conf
WPA_CTRL_DIR=/run/wpa_supplicant
WPA_PID=$RUN_DIR/wifi-sta-wpa.pid
WPA_LOG=$RUN_DIR/wifi-sta-wpa.log
DHCP_PID=$RUN_DIR/wifi-sta-dhclient.pid
DHCP_LEASES=$RUN_DIR/wifi-sta-dhclient.leases
DHCP_LOG=$RUN_DIR/wifi-sta-dhclient.log
L3_HOST=cloudflare.com
L3_PORT=443
NC_BIN=

append_marker() {
  [ -f "$MARKER" ] && echo "$1" >> "$MARKER"
}

kill_pidfile_if_matching() {
  pidfile=$1
  needle=$2
  [ -e "$pidfile" ] || return 0
  pid=$(cat "$pidfile" 2>/dev/null || true)
  case "$pid" in
    ''|*[!0-9]*) ;;
    *)
      if [ "$pid" != "1" ]; then
        cmd=$(tr '\000' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)
        case "$cmd" in
          *"$needle"*) kill "$pid" 2>/dev/null || true ;;
        esac
      fi
      ;;
  esac
  rm -f "$pidfile" 2>/dev/null || true
}

kill_matching_cmdline() {
  needle=$1
  for cmdline in /proc/[0-9]*/cmdline; do
    pid=${cmdline#/proc/}
    pid=${pid%/cmdline}
    [ "$pid" = "1" ] && continue
    cmd=$(tr '\000' ' ' < "$cmdline" 2>/dev/null || true)
    case "$cmd" in
      *"$needle"*) kill "$pid" 2>/dev/null || true ;;
    esac
  done
}

default_route_iface() {
  ip route show default 2>/dev/null |
    awk '/^default / { for (i = 1; i <= NF; i++) if ($i == "dev") { print $(i + 1); exit } }'
}

lease_default_router() {
  awk '
    /option routers/ {
      gsub(";", "", $3)
      print $3
      exit
    }
  ' "$DHCP_LEASES" 2>/dev/null
}

ncm_recovery_preserved() {
  ip route show 192.168.7.1 2>/dev/null | grep -q ' dev ncm0'
}

neigh_state_for_router() {
  ip neigh show "$1" dev "$IFACE" 2>/dev/null |
    awk '{ state = $NF } END { if (state != "") print state }'
}

arp_state_is_resolved() {
  case "$1" in
    REACHABLE|STALE|DELAY|PROBE|PERMANENT) return 0 ;;
    *) return 1 ;;
  esac
}

probe_l3_reachability() {
  router=$1
  gateway_ping_rc=99
  gateway_arp_state=none
  gateway_arp_resolved=0
  dns_probe_rc=99
  tcp_probe_rc=99

  if [ -n "$router" ]; then
    ping -I "$IFACE" -c 1 -W 2 "$router" >/dev/null 2>&1
    gateway_ping_rc=$?
    gateway_arp_state=$(neigh_state_for_router "$router")
    [ -n "$gateway_arp_state" ] || gateway_arp_state=none
    if arp_state_is_resolved "$gateway_arp_state"; then
      gateway_arp_resolved=1
    fi
  fi

  getent hosts "$L3_HOST" >/dev/null 2>&1
  dns_probe_rc=$?
  if [ "$dns_probe_rc" = "0" ]; then
    "$NC_BIN" -z -w 5 "$L3_HOST" "$L3_PORT" >/dev/null 2>&1
    tcp_probe_rc=$?
  fi

  append_marker "wifi_sta_l3_attempted=1"
  append_marker "wifi_sta_l3_probe=cloudflare-443"
  append_marker "wifi_sta_tcp_probe_tool=$(basename "$NC_BIN")"
  append_marker "wifi_sta_gateway_ping_rc=$gateway_ping_rc"
  append_marker "wifi_sta_gateway_arp_state=$gateway_arp_state"
  append_marker "wifi_sta_gateway_arp_resolved=$gateway_arp_resolved"
  append_marker "wifi_sta_dns_probe_rc=$dns_probe_rc"
  append_marker "wifi_sta_tcp443_probe_rc=$tcp_probe_rc"
}

wpa_cli_quiet() {
  wpa_cli -p "$WPA_CTRL_DIR" -i "$IFACE" "$@" >/dev/null 2>&1
  return $?
}

wpa_ctrl_wait() {
  ctrl_ready=0
  ctrl_wait_sec=0
  for sec in 1 2 3 4 5 6 7 8 9 10; do
    if wpa_cli -p "$WPA_CTRL_DIR" -i "$IFACE" PING 2>/dev/null | grep -q '^PONG'; then
      ctrl_ready=1
      break
    fi
    ctrl_wait_sec=$sec
    sleep 1
  done
  append_marker "wifi_sta_ctrl_ready=$ctrl_ready"
  append_marker "wifi_sta_ctrl_wait_sec=$ctrl_wait_sec"
  [ "$ctrl_ready" = "1" ]
}

append_wpa_status_markers() {
  status=$(wpa_cli -p "$WPA_CTRL_DIR" -i "$IFACE" STATUS 2>/dev/null)
  status_rc=$?
  append_marker "wifi_sta_ctrl_status_rc=$status_rc"
  wpa_state=$(printf '%s\n' "$status" | awk -F= '$1 == "wpa_state" { print $2; exit }')
  wpa_freq=$(printf '%s\n' "$status" | awk -F= '$1 == "freq" { print $2; exit }')
  wpa_key_mgmt=$(printf '%s\n' "$status" | awk -F= '$1 == "key_mgmt" { print $2; exit }')
  [ -n "$wpa_state" ] || wpa_state=-
  [ -n "$wpa_freq" ] || wpa_freq=-
  [ -n "$wpa_key_mgmt" ] || wpa_key_mgmt=-
  append_marker "wifi_sta_ctrl_status_wpa_state=$wpa_state"
  append_marker "wifi_sta_ctrl_status_freq=$wpa_freq"
  append_marker "wifi_sta_ctrl_status_key_mgmt=$wpa_key_mgmt"
  case "$wpa_state" in
    COMPLETED) append_marker "wifi_sta_ctrl_status_completed=1" ;;
    *) append_marker "wifi_sta_ctrl_status_completed=0" ;;
  esac
}

wait_wpa_completed() {
  wpa_completed=0
  wpa_completed_wait_sec=0
  for sec in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    state=$(wpa_cli -p "$WPA_CTRL_DIR" -i "$IFACE" STATUS 2>/dev/null |
      awk -F= '$1 == "wpa_state" { print $2; exit }')
    if [ "$state" = "COMPLETED" ]; then
      wpa_completed=1
      break
    fi
    wpa_completed_wait_sec=$sec
    sleep 1
  done
  append_marker "wifi_sta_wpa_completed=$wpa_completed"
  append_marker "wifi_sta_wpa_completed_wait_sec=$wpa_completed_wait_sec"
  [ "$wpa_completed" = "1" ]
}

finish() {
  decision=$1
  append_marker "wifi_sta_decision=$decision"
  append_marker "wifi_sta_secret_values_logged=0"
  exit 0
}

mkdir -p "$RUN_DIR"
append_marker "wifi_sta_requested=1"
append_marker "wifi_sta_iface=$IFACE"
append_marker "wifi_sta_config_path=$CONFIG"

if [ ! -s "$ENABLE" ]; then
  append_marker "wifi_sta_started=0"
  finish "wifi-sta-manual"
fi

if [ ! -s "$CONFIG" ]; then
  append_marker "wifi_sta_config_present=0"
  append_marker "wifi_sta_started=0"
  finish "wifi-sta-config-missing"
fi
append_marker "wifi_sta_config_present=1"

if ! command -v wpa_supplicant >/dev/null 2>&1 ||
   ! command -v wpa_cli >/dev/null 2>&1 ||
   ! command -v dhclient >/dev/null 2>&1 ||
   ! command -v ip >/dev/null 2>&1 ||
   ! command -v ping >/dev/null 2>&1 ||
   ! command -v getent >/dev/null 2>&1; then
  append_marker "wifi_sta_started=0"
  finish "wifi-sta-missing-tools"
fi
NC_BIN=$(command -v nc 2>/dev/null || command -v nc.openbsd 2>/dev/null || true)
if [ -z "$NC_BIN" ]; then
  append_marker "wifi_sta_started=0"
  finish "wifi-sta-missing-tools"
fi

ip link show "$IFACE" >/dev/null 2>&1
if [ "$?" != "0" ]; then
  append_marker "wifi_sta_wlan0_present=0"
  append_marker "wifi_sta_started=0"
  finish "wifi-sta-wlan0-missing"
fi
append_marker "wifi_sta_wlan0_present=1"

ip route replace 192.168.7.1 dev ncm0 >/dev/null 2>&1 || true
if ncm_recovery_preserved; then
  append_marker "ncm_recovery_preserved=1"
else
  append_marker "ncm_recovery_preserved=0"
fi

kill_pidfile_if_matching "$DHCP_PID" "dhclient"
kill_pidfile_if_matching "$WPA_PID" "wpa_supplicant"
kill_matching_cmdline "$CONFIG"
rm -f "$WPA_LOG" "$DHCP_LOG" "$DHCP_LEASES" 2>/dev/null || true
mkdir -p "$WPA_CTRL_DIR"

ip link set "$IFACE" up >/dev/null 2>&1
link_set_up_rc=$?
append_marker "wifi_sta_link_set_up_rc=$link_set_up_rc"
if [ "$link_set_up_rc" != "0" ]; then
  append_marker "wifi_sta_started=0"
  finish "wifi-sta-link-up-failed"
fi
wpa_supplicant -B -q -i "$IFACE" -D nl80211 -c "$CONFIG" \
  -P "$WPA_PID" -f "$WPA_LOG" >/dev/null 2>&1
wpa_rc=$?
append_marker "wifi_sta_wpa_supplicant_rc=$wpa_rc"
if [ "$wpa_rc" != "0" ]; then
  append_marker "wifi_sta_started=0"
  finish "wifi-sta-wpa-start-failed"
fi

append_marker "wifi_sta_started=1"
if wpa_ctrl_wait; then
  wpa_cli_quiet DRIVER COUNTRY KR
  append_marker "wifi_sta_ctrl_driver_country_rc=$?"
  wpa_cli_quiet SCAN
  append_marker "wifi_sta_ctrl_scan_rc=$?"
  wpa_cli_quiet ENABLE_NETWORK 0
  append_marker "wifi_sta_ctrl_enable_network_rc=$?"
  wpa_cli_quiet SELECT_NETWORK 0
  append_marker "wifi_sta_ctrl_select_network_rc=$?"
  wpa_cli_quiet REASSOCIATE
  append_marker "wifi_sta_ctrl_reassociate_rc=$?"
  append_wpa_status_markers
  if ! wait_wpa_completed; then
    append_wpa_status_markers
    append_marker "wifi_sta_carrier_up=0"
    finish "wifi-sta-assoc-failed"
  fi
else
  append_marker "wifi_sta_ctrl_driver_country_rc=99"
  append_marker "wifi_sta_ctrl_scan_rc=99"
  append_marker "wifi_sta_ctrl_enable_network_rc=99"
  append_marker "wifi_sta_ctrl_select_network_rc=99"
  append_marker "wifi_sta_ctrl_reassociate_rc=99"
  append_marker "wifi_sta_wpa_completed=0"
  append_marker "wifi_sta_wpa_completed_wait_sec=0"
  append_marker "wifi_sta_carrier_up=0"
  finish "wifi-sta-ctrl-unavailable"
fi
carrier=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
  if [ "$(cat /sys/class/net/$IFACE/carrier 2>/dev/null)" = "1" ]; then
    carrier=1
    break
  fi
  sleep 1
done
append_marker "wifi_sta_carrier_up=$carrier"
if [ "$ctrl_ready" = "1" ]; then
  append_wpa_status_markers
fi

dhclient -1 -q -4 -pf "$DHCP_PID" -lf "$DHCP_LEASES" "$IFACE" > "$DHCP_LOG" 2>&1
dhcp_rc=$?
append_marker "wifi_sta_dhcp_attempted=1"
append_marker "wifi_sta_dhcp_rc=$dhcp_rc"
if [ "$dhcp_rc" = "0" ]; then
  router=$(lease_default_router)
  if [ -n "$router" ]; then
    append_marker "wifi_sta_default_route_router_present=1"
    ip route replace default via "$router" dev "$IFACE" >/dev/null 2>&1
    append_marker "wifi_sta_default_route_set_rc=$?"
  else
    append_marker "wifi_sta_default_route_router_present=0"
    append_marker "wifi_sta_default_route_set_rc=99"
  fi
fi
route_iface=$(default_route_iface)
[ -n "$route_iface" ] || route_iface=none
append_marker "wifi_sta_default_route_iface=$route_iface"

if ncm_recovery_preserved; then
  append_marker "ncm_recovery_preserved_after_dhcp=1"
else
  append_marker "ncm_recovery_preserved_after_dhcp=0"
fi

if [ "$dhcp_rc" = "0" ] && [ "$route_iface" = "$IFACE" ]; then
  probe_l3_reachability "$router"
  if [ "$gateway_arp_resolved" != "1" ]; then
    finish "wifi-sta-l3-gateway-unreachable"
  fi
  if [ "$dns_probe_rc" != "0" ]; then
    finish "wifi-sta-l3-dns-failed"
  fi
  if [ "$tcp_probe_rc" != "0" ]; then
    finish "wifi-sta-l3-tcp-failed"
  fi
  finish "wifi-sta-pass"
fi
if [ "$dhcp_rc" = "0" ]; then
  finish "wifi-sta-dhcp-no-wlan0-default"
fi
finish "wifi-sta-dhcp-failed"
