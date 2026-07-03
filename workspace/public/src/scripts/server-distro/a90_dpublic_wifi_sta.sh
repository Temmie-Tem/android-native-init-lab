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
WPA_PID=$RUN_DIR/wifi-sta-wpa.pid
WPA_LOG=$RUN_DIR/wifi-sta-wpa.log
DHCP_PID=$RUN_DIR/wifi-sta-dhclient.pid
DHCP_LEASES=$RUN_DIR/wifi-sta-dhclient.leases
DHCP_LOG=$RUN_DIR/wifi-sta-dhclient.log
L3_HOST=cloudflare.com
L3_PORT=443

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
    nc -z -w 5 "$L3_HOST" "$L3_PORT" >/dev/null 2>&1
    tcp_probe_rc=$?
  fi

  append_marker "wifi_sta_l3_attempted=1"
  append_marker "wifi_sta_l3_probe=cloudflare-443"
  append_marker "wifi_sta_gateway_ping_rc=$gateway_ping_rc"
  append_marker "wifi_sta_gateway_arp_state=$gateway_arp_state"
  append_marker "wifi_sta_gateway_arp_resolved=$gateway_arp_resolved"
  append_marker "wifi_sta_dns_probe_rc=$dns_probe_rc"
  append_marker "wifi_sta_tcp443_probe_rc=$tcp_probe_rc"
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
   ! command -v dhclient >/dev/null 2>&1 ||
   ! command -v ip >/dev/null 2>&1 ||
   ! command -v ping >/dev/null 2>&1 ||
   ! command -v getent >/dev/null 2>&1 ||
   ! command -v nc >/dev/null 2>&1; then
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

ip link set "$IFACE" up >/dev/null 2>&1 || true
wpa_supplicant -B -q -i "$IFACE" -D nl80211 -c "$CONFIG" \
  -P "$WPA_PID" -f "$WPA_LOG" >/dev/null 2>&1
wpa_rc=$?
append_marker "wifi_sta_wpa_supplicant_rc=$wpa_rc"
if [ "$wpa_rc" != "0" ]; then
  append_marker "wifi_sta_started=0"
  finish "wifi-sta-wpa-start-failed"
fi

append_marker "wifi_sta_started=1"
carrier=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
  if [ "$(cat /sys/class/net/$IFACE/carrier 2>/dev/null)" = "1" ]; then
    carrier=1
    break
  fi
  sleep 1
done
append_marker "wifi_sta_carrier_up=$carrier"

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
