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
IMMEDIATE_SNAPSHOT_ONLY=/etc/a90-dpublic/wifi-sta-immediate-snapshot-only
CONFIG=/etc/a90-dpublic/wpa_supplicant-wlan0.conf
WPA_CTRL_DIR=/run/wpa_supplicant
WPA_PID=$RUN_DIR/wifi-sta-wpa.pid
WPA_LOG=$RUN_DIR/wifi-sta-wpa.log
DHCP_PID=$RUN_DIR/wifi-sta-dhclient.pid
DHCP_LEASES=$RUN_DIR/wifi-sta-dhclient.leases
DHCP_LOG=$RUN_DIR/wifi-sta-dhclient.log
L3_HOST=cloudflare.com
L3_PORT=443
DWELL_SAMPLES=6
DWELL_INTERVAL_SEC=5
WPA_COMPLETE_ATTEMPTS=3
WPA_COMPLETE_WAIT_SEC=20
SCAN_VIS_SAMPLES=6
SCAN_VIS_INTERVAL_SEC=2
LINK_REASSERT_SETTLE_SEC=2
NC_BIN=
RUN_ID=
PHASE_SEQ=0

append_marker() {
  [ -f "$MARKER" ] && echo "$1" >> "$MARKER"
}

uptime_ms() {
  awk '{ split($1, a, "."); ms = a[1] * 1000; if (a[2] != "") { ms += substr(a[2] "000", 1, 3) } print ms }' /proc/uptime 2>/dev/null
}

mark_phase() {
  phase=$1
  PHASE_SEQ=$((PHASE_SEQ + 1))
  now_ms=$(uptime_ms)
  [ -n "$now_ms" ] || now_ms=0
  append_marker "wifi_sta_event=$RUN_ID:$PHASE_SEQ:$phase:$now_ms"
}

link_snapshot() {
  snapshot_label=$1
  link_operstate=$(cat /sys/class/net/$IFACE/operstate 2>/dev/null)
  [ -n "$link_operstate" ] || link_operstate=-
  link_carrier=$(cat /sys/class/net/$IFACE/carrier 2>/dev/null)
  [ -n "$link_carrier" ] || link_carrier=0
  link_flags_hex=$(cat /sys/class/net/$IFACE/flags 2>/dev/null)
  [ -n "$link_flags_hex" ] || link_flags_hex=0x0
  case "$link_flags_hex" in
    0x*|0X*|[0-9]*) link_flags_num=$((link_flags_hex + 0)) ;;
    *) link_flags_num=0 ;;
  esac
  link_flags_up=0
  link_flags_running=0
  link_flags_lower_up=0
  link_flags_dormant=0
  [ $((link_flags_num & 1)) -ne 0 ] && link_flags_up=1
  [ $((link_flags_num & 64)) -ne 0 ] && link_flags_running=1
  [ $((link_flags_num & 65536)) -ne 0 ] && link_flags_lower_up=1
  [ $((link_flags_num & 131072)) -ne 0 ] && link_flags_dormant=1
  link_addr_assign_type=$(cat /sys/class/net/$IFACE/addr_assign_type 2>/dev/null)
  [ -n "$link_addr_assign_type" ] || link_addr_assign_type=-
  link_tx_queue_len=$(cat /sys/class/net/$IFACE/tx_queue_len 2>/dev/null)
  [ -n "$link_tx_queue_len" ] || link_tx_queue_len=-
  link_line=$(ip -o link show dev "$IFACE" 2>/dev/null)
  link_qdisc=$(printf '%s\n' "$link_line" | awk '{ for (i = 1; i <= NF; i++) if ($i == "qdisc") { print $(i + 1); exit } }')
  [ -n "$link_qdisc" ] || link_qdisc=-
  link_wireless_present=0
  if [ -d /sys/class/net/$IFACE/wireless ] || awk -v iface="$IFACE" -F: '$1 ~ iface { found = 1 } END { exit found ? 0 : 1 }' /proc/net/wireless 2>/dev/null; then
    link_wireless_present=1
  fi

  append_marker "wifi_sta_link_${snapshot_label}_operstate=$link_operstate"
  append_marker "wifi_sta_link_${snapshot_label}_carrier=$link_carrier"
  append_marker "wifi_sta_link_${snapshot_label}_flags_hex=$link_flags_hex"
  append_marker "wifi_sta_link_${snapshot_label}_flags_up=$link_flags_up"
  append_marker "wifi_sta_link_${snapshot_label}_flags_running=$link_flags_running"
  append_marker "wifi_sta_link_${snapshot_label}_flags_lower_up=$link_flags_lower_up"
  append_marker "wifi_sta_link_${snapshot_label}_flags_dormant=$link_flags_dormant"
  append_marker "wifi_sta_link_${snapshot_label}_addr_assign_type=$link_addr_assign_type"
  append_marker "wifi_sta_link_${snapshot_label}_qdisc=$link_qdisc"
  append_marker "wifi_sta_link_${snapshot_label}_tx_queue_len=$link_tx_queue_len"
  append_marker "wifi_sta_link_${snapshot_label}_wireless_present=$link_wireless_present"
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

default_route_gateway() {
  ip route show default 2>/dev/null |
    awk '/^default / { for (i = 1; i <= NF; i++) if ($i == "via") { print $(i + 1); exit } }'
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

sample_gateway_ping() {
  router=$1
  gateway_ping_attempts=3
  gateway_ping_successes=0
  gateway_ping_first_success_ms=-
  gateway_ping_total_ms=-
  gateway_ping_rc=1

  ping_start_ms=$(uptime_ms)
  attempt=1
  while [ "$attempt" -le "$gateway_ping_attempts" ]; do
    attempt_start_ms=$(uptime_ms)
    ping -I "$IFACE" -c 1 -W 1 "$router" >/dev/null 2>&1
    ping_rc=$?
    attempt_end_ms=$(uptime_ms)
    if [ "$ping_rc" = "0" ]; then
      gateway_ping_successes=$((gateway_ping_successes + 1))
      if [ "$gateway_ping_first_success_ms" = "-" ]; then
        gateway_ping_first_success_ms=$((attempt_end_ms - attempt_start_ms))
      fi
    fi
    attempt=$((attempt + 1))
  done
  ping_end_ms=$(uptime_ms)
  gateway_ping_total_ms=$((ping_end_ms - ping_start_ms))
  if [ "$gateway_ping_successes" -gt 0 ]; then
    gateway_ping_rc=0
  fi
}

sample_l3_reachability() {
  router=$1
  gateway_ping_rc=99
  gateway_ping_attempts=0
  gateway_ping_successes=0
  gateway_ping_first_success_ms=-
  gateway_ping_total_ms=-
  gateway_neigh_state_before=none
  gateway_neigh_get_rc=99
  gateway_neigh_state_after_get=none
  gateway_arp_state=none
  gateway_arp_resolved=0
  lease_router_present=0
  lease_router_matches_initial=0
  default_route_gateway_present=0
  default_route_gateway_matches_initial=0
  default_route_gateway_matches_lease=0
  dns_probe_rc=99
  tcp_probe_rc=99

  lease_router=$(lease_default_router)
  if [ -n "$lease_router" ]; then
    lease_router_present=1
  fi
  route_gateway=$(default_route_gateway)
  if [ -n "$route_gateway" ]; then
    default_route_gateway_present=1
  fi

  if [ -n "$router" ]; then
    if [ "$lease_router" = "$router" ]; then
      lease_router_matches_initial=1
    fi
    if [ "$route_gateway" = "$router" ]; then
      default_route_gateway_matches_initial=1
    fi
    if [ -n "$lease_router" ] && [ "$route_gateway" = "$lease_router" ]; then
      default_route_gateway_matches_lease=1
    fi

    gateway_neigh_state_before=$(neigh_state_for_router "$router")
    [ -n "$gateway_neigh_state_before" ] || gateway_neigh_state_before=none
    ip neigh get "$router" dev "$IFACE" >/dev/null 2>&1
    gateway_neigh_get_rc=$?
    gateway_neigh_state_after_get=$(neigh_state_for_router "$router")
    [ -n "$gateway_neigh_state_after_get" ] || gateway_neigh_state_after_get=none
    sample_gateway_ping "$router"
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
}

probe_l3_reachability() {
  sample_l3_reachability "$1"
  append_marker "wifi_sta_l3_attempted=1"
  append_marker "wifi_sta_l3_probe=cloudflare-443"
  append_marker "wifi_sta_tcp_probe_tool=$(basename "$NC_BIN")"
  append_marker "wifi_sta_gateway_ping_rc=$gateway_ping_rc"
  append_marker "wifi_sta_gateway_ping_attempts=$gateway_ping_attempts"
  append_marker "wifi_sta_gateway_ping_successes=$gateway_ping_successes"
  append_marker "wifi_sta_gateway_ping_first_success_ms=$gateway_ping_first_success_ms"
  append_marker "wifi_sta_gateway_ping_total_ms=$gateway_ping_total_ms"
  append_marker "wifi_sta_gateway_neigh_state_before=$gateway_neigh_state_before"
  append_marker "wifi_sta_gateway_neigh_get_rc=$gateway_neigh_get_rc"
  append_marker "wifi_sta_gateway_neigh_state_after_get=$gateway_neigh_state_after_get"
  append_marker "wifi_sta_gateway_arp_state=$gateway_arp_state"
  append_marker "wifi_sta_gateway_arp_resolved=$gateway_arp_resolved"
  append_marker "wifi_sta_lease_router_present=$lease_router_present"
  append_marker "wifi_sta_lease_router_matches_initial=$lease_router_matches_initial"
  append_marker "wifi_sta_default_route_gateway_present=$default_route_gateway_present"
  append_marker "wifi_sta_default_route_gateway_matches_initial=$default_route_gateway_matches_initial"
  append_marker "wifi_sta_default_route_gateway_matches_lease=$default_route_gateway_matches_lease"
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

wpa_state_value() {
  wpa_cli -p "$WPA_CTRL_DIR" -i "$IFACE" STATUS 2>/dev/null |
    awk -F= '$1 == "wpa_state" { print $2; exit }'
}

wpa_scan_results_count() {
  wpa_cli -p "$WPA_CTRL_DIR" -i "$IFACE" SCAN_RESULTS 2>/dev/null |
    awk 'NR > 2 { count++ } END { print count + 0 }'
}

sample_regulatory_state() {
  reg_label=$1
  country=$(wpa_cli -p "$WPA_CTRL_DIR" -i "$IFACE" GET country 2>/dev/null)
  country_get_rc=$?
  country_present=0
  country_is_kr=0
  case "$country" in
    ""|FAIL*) ;;
    *)
      country_present=1
      [ "$country" = "KR" ] && country_is_kr=1
      ;;
  esac

  iw_present=0
  iw_reg_get_rc=127
  iw_reg_country_present=0
  iw_dev_info_rc=127
  iw_phy_present=0
  iw_type_managed=0
  iw_link_rc=127
  iw_link_connected=0
  iw_scan_rc=127
  iw_scan_bss_count=0
  if command -v iw >/dev/null 2>&1; then
    iw_present=1
    iw_reg=$(iw reg get 2>/dev/null)
    iw_reg_get_rc=$?
    if printf '%s\n' "$iw_reg" | grep -q '^country '; then
      iw_reg_country_present=1
    fi
    iw_dev_info=$(iw dev "$IFACE" info 2>/dev/null)
    iw_dev_info_rc=$?
    if printf '%s\n' "$iw_dev_info" | grep -q '^[[:space:]]*wiphy '; then
      iw_phy_present=1
    fi
    if printf '%s\n' "$iw_dev_info" | grep -q '^[[:space:]]*type managed'; then
      iw_type_managed=1
    fi
    iw_link=$(iw dev "$IFACE" link 2>/dev/null)
    iw_link_rc=$?
    if printf '%s\n' "$iw_link" | grep -q '^Connected to '; then
      iw_link_connected=1
    fi
    if command -v timeout >/dev/null 2>&1; then
      iw_scan=$(timeout 10s iw dev "$IFACE" scan 2>/dev/null)
      iw_scan_rc=$?
    else
      iw_scan=$(iw dev "$IFACE" scan 2>/dev/null)
      iw_scan_rc=$?
    fi
    iw_scan_bss_count=$(printf '%s\n' "$iw_scan" | grep -c '^BSS ')
  fi

  append_marker "wifi_sta_reg_${reg_label}_country_get_rc=$country_get_rc"
  append_marker "wifi_sta_reg_${reg_label}_country_present=$country_present"
  append_marker "wifi_sta_reg_${reg_label}_country_kr=$country_is_kr"
  append_marker "wifi_sta_reg_${reg_label}_iw_present=$iw_present"
  append_marker "wifi_sta_reg_${reg_label}_iw_reg_get_rc=$iw_reg_get_rc"
  append_marker "wifi_sta_reg_${reg_label}_iw_reg_country_present=$iw_reg_country_present"
  append_marker "wifi_sta_reg_${reg_label}_iw_dev_info_rc=$iw_dev_info_rc"
  append_marker "wifi_sta_reg_${reg_label}_iw_phy_present=$iw_phy_present"
  append_marker "wifi_sta_reg_${reg_label}_iw_type_managed=$iw_type_managed"
  append_marker "wifi_sta_reg_${reg_label}_iw_link_rc=$iw_link_rc"
  append_marker "wifi_sta_reg_${reg_label}_iw_link_connected=$iw_link_connected"
  append_marker "wifi_sta_reg_${reg_label}_iw_scan_rc=$iw_scan_rc"
  append_marker "wifi_sta_reg_${reg_label}_iw_scan_bss_count=$iw_scan_bss_count"
}

scan_visibility_probe() {
  label=$1
  scan_visibility_found=0
  scan_visibility_final_count=0
  scan_visibility_trigger_start_ms=$(uptime_ms)
  wpa_cli_quiet SCAN
  scan_visibility_trigger_rc=$?
  append_marker "wifi_sta_scan_${label}_trigger_rc=$scan_visibility_trigger_rc"
  append_marker "wifi_sta_scan_${label}_samples=$SCAN_VIS_SAMPLES"
  append_marker "wifi_sta_scan_${label}_interval_sec=$SCAN_VIS_INTERVAL_SEC"
  mark_phase "scan-$label-trigger"

  sample=1
  while [ "$sample" -le "$SCAN_VIS_SAMPLES" ]; do
    sleep "$SCAN_VIS_INTERVAL_SEC"
    scan_count=$(wpa_scan_results_count)
    scan_visibility_final_count=$scan_count
    if [ "$scan_count" -gt 0 ]; then
      scan_visibility_found=1
    fi
    state=$(wpa_state_value)
    [ -n "$state" ] || state=-
    operstate=$(cat /sys/class/net/$IFACE/operstate 2>/dev/null)
    [ -n "$operstate" ] || operstate=-
    carrier_now=$(cat /sys/class/net/$IFACE/carrier 2>/dev/null)
    [ -n "$carrier_now" ] || carrier_now=0
    append_marker "wifi_sta_scan_${label}_sample_${sample}_results_count=$scan_count"
    append_marker "wifi_sta_scan_${label}_sample_${sample}_wpa_state=$state"
    append_marker "wifi_sta_scan_${label}_sample_${sample}_operstate=$operstate"
    append_marker "wifi_sta_scan_${label}_sample_${sample}_carrier=$carrier_now"
    link_snapshot "scan_${label}_sample_${sample}"
    sample=$((sample + 1))
  done
  scan_visibility_end_ms=$(uptime_ms)
  scan_visibility_total_ms=$((scan_visibility_end_ms - scan_visibility_trigger_start_ms))
  append_marker "wifi_sta_scan_${label}_found=$scan_visibility_found"
  append_marker "wifi_sta_scan_${label}_final_results_count=$scan_visibility_final_count"
  append_marker "wifi_sta_scan_${label}_total_ms=$scan_visibility_total_ms"
  mark_phase "scan-$label-done"
}

sample_wpa_signal() {
  wpa_cli -p "$WPA_CTRL_DIR" -i "$IFACE" PING 2>/dev/null | grep -q '^PONG'
  wpa_ping_rc=$?
  signal=$(wpa_cli -p "$WPA_CTRL_DIR" -i "$IFACE" SIGNAL_POLL 2>/dev/null)
  signal_poll_rc=$?
  signal_rssi_dbm=$(printf '%s\n' "$signal" | awk -F= '$1 == "RSSI" { print $2; exit }')
  signal_linkspeed_mbps=$(printf '%s\n' "$signal" | awk -F= '$1 == "LINKSPEED" { print $2; exit }')
  signal_frequency_mhz=$(printf '%s\n' "$signal" | awk -F= '$1 == "FREQUENCY" { print $2; exit }')
  [ -n "$signal_rssi_dbm" ] || signal_rssi_dbm=-
  [ -n "$signal_linkspeed_mbps" ] || signal_linkspeed_mbps=-
  [ -n "$signal_frequency_mhz" ] || signal_frequency_mhz=-
}

wait_wpa_completed() {
  wpa_completed=0
  wpa_completed_wait_sec=0
  wpa_completed_attempts=0
  append_marker "wifi_sta_assoc_attempts_max=$WPA_COMPLETE_ATTEMPTS"
  append_marker "wifi_sta_assoc_attempt_wait_sec=$WPA_COMPLETE_WAIT_SEC"

  attempt=1
  while [ "$attempt" -le "$WPA_COMPLETE_ATTEMPTS" ]; do
    wpa_completed_attempts=$attempt
    append_marker "wifi_sta_assoc_attempt_${attempt}_started=1"
    sec=1
    while [ "$sec" -le "$WPA_COMPLETE_WAIT_SEC" ]; do
      state=$(wpa_state_value)
      if [ "$state" = "COMPLETED" ]; then
        wpa_completed=1
        break
      fi
      wpa_completed_wait_sec=$((wpa_completed_wait_sec + 1))
      sleep 1
      sec=$((sec + 1))
    done
    state=$(wpa_state_value)
    [ -n "$state" ] || state=-
    scan_count=$(wpa_scan_results_count)
    append_marker "wifi_sta_assoc_attempt_${attempt}_wpa_state=$state"
    append_marker "wifi_sta_assoc_attempt_${attempt}_scan_results_count=$scan_count"
    if [ "$wpa_completed" = "1" ]; then
      append_marker "wifi_sta_assoc_attempt_${attempt}_completed=1"
      break
    fi
    append_marker "wifi_sta_assoc_attempt_${attempt}_completed=0"
    if [ "$attempt" -lt "$WPA_COMPLETE_ATTEMPTS" ]; then
      scan_visibility_probe "retry_${attempt}"
      append_marker "wifi_sta_assoc_attempt_${attempt}_retry_scan_rc=$scan_visibility_trigger_rc"
      append_marker "wifi_sta_assoc_attempt_${attempt}_retry_scan_found=$scan_visibility_found"
      link_snapshot "assoc_retry_${attempt}_before_relink"
      ip link set "$IFACE" up >/dev/null 2>&1
      retry_link_up_rc=$?
      append_marker "wifi_sta_assoc_attempt_${attempt}_retry_link_up_rc=$retry_link_up_rc"
      sleep "$LINK_REASSERT_SETTLE_SEC"
      link_snapshot "assoc_retry_${attempt}_after_relink"
      wpa_cli_quiet ENABLE_NETWORK 0
      append_marker "wifi_sta_assoc_attempt_${attempt}_retry_enable_network_rc=$?"
      wpa_cli_quiet SELECT_NETWORK 0
      append_marker "wifi_sta_assoc_attempt_${attempt}_retry_select_network_rc=$?"
      wpa_cli_quiet REASSOCIATE
      append_marker "wifi_sta_assoc_attempt_${attempt}_retry_reassociate_rc=$?"
      mark_phase "assoc-retry-$attempt"
      sleep 2
    fi
    attempt=$((attempt + 1))
  done
  append_marker "wifi_sta_wpa_completed=$wpa_completed"
  append_marker "wifi_sta_wpa_completed_wait_sec=$wpa_completed_wait_sec"
  append_marker "wifi_sta_wpa_completed_attempts=$wpa_completed_attempts"
  [ "$wpa_completed" = "1" ]
}

finish() {
  decision=$1
  mark_phase "finish-$decision"
  append_marker "wifi_sta_decision_run_id=$RUN_ID"
  append_marker "wifi_sta_decision=$decision"
  append_marker "wifi_sta_secret_values_logged=0"
  exit 0
}

dwell_stability_probe() {
  router=$1
  dwell_pass=1
  first_fail_sample=0
  first_fail_reason=none
  append_marker "wifi_sta_dwell_started=1"
  append_marker "wifi_sta_dwell_samples=$DWELL_SAMPLES"
  append_marker "wifi_sta_dwell_interval_sec=$DWELL_INTERVAL_SEC"
  mark_phase "dwell-start"

  sample=1
  while [ "$sample" -le "$DWELL_SAMPLES" ]; do
    if [ "$sample" != "1" ]; then
      sleep "$DWELL_INTERVAL_SEC"
    fi
    wpa_state=$(wpa_state_value)
    [ -n "$wpa_state" ] || wpa_state=-
    sample_wpa_signal
    carrier_now=$(cat /sys/class/net/$IFACE/carrier 2>/dev/null)
    [ -n "$carrier_now" ] || carrier_now=0
    route_iface=$(default_route_iface)
    [ -n "$route_iface" ] || route_iface=none
    sample_l3_reachability "$router"

    sample_ok=1
    sample_failure=none
    if [ "$wpa_ping_rc" != "0" ]; then
      sample_ok=0
      sample_failure=wpa-ping
    elif [ "$wpa_state" != "COMPLETED" ]; then
      sample_ok=0
      sample_failure=wpa-state
    elif [ "$carrier_now" != "1" ]; then
      sample_ok=0
      sample_failure=carrier
    elif [ "$route_iface" != "$IFACE" ]; then
      sample_ok=0
      sample_failure=default-route
    elif [ "$gateway_arp_resolved" != "1" ]; then
      sample_ok=0
      sample_failure=gateway-arp
    elif [ "$gateway_ping_rc" != "0" ]; then
      sample_ok=0
      sample_failure=gateway-ping
    elif [ "$dns_probe_rc" != "0" ]; then
      sample_ok=0
      sample_failure=dns
    elif [ "$tcp_probe_rc" != "0" ]; then
      sample_ok=0
      sample_failure=tcp443
    fi

    append_marker "wifi_sta_dwell_sample_${sample}_wpa_state=$wpa_state"
    append_marker "wifi_sta_dwell_sample_${sample}_wpa_ping_rc=$wpa_ping_rc"
    append_marker "wifi_sta_dwell_sample_${sample}_signal_poll_rc=$signal_poll_rc"
    append_marker "wifi_sta_dwell_sample_${sample}_signal_rssi_dbm=$signal_rssi_dbm"
    append_marker "wifi_sta_dwell_sample_${sample}_signal_linkspeed_mbps=$signal_linkspeed_mbps"
    append_marker "wifi_sta_dwell_sample_${sample}_signal_frequency_mhz=$signal_frequency_mhz"
    append_marker "wifi_sta_dwell_sample_${sample}_carrier=$carrier_now"
    append_marker "wifi_sta_dwell_sample_${sample}_default_route_iface=$route_iface"
    append_marker "wifi_sta_dwell_sample_${sample}_gateway_ping_rc=$gateway_ping_rc"
    append_marker "wifi_sta_dwell_sample_${sample}_gateway_ping_attempts=$gateway_ping_attempts"
    append_marker "wifi_sta_dwell_sample_${sample}_gateway_ping_successes=$gateway_ping_successes"
    append_marker "wifi_sta_dwell_sample_${sample}_gateway_ping_first_success_ms=$gateway_ping_first_success_ms"
    append_marker "wifi_sta_dwell_sample_${sample}_gateway_ping_total_ms=$gateway_ping_total_ms"
    append_marker "wifi_sta_dwell_sample_${sample}_gateway_neigh_state_before=$gateway_neigh_state_before"
    append_marker "wifi_sta_dwell_sample_${sample}_gateway_neigh_get_rc=$gateway_neigh_get_rc"
    append_marker "wifi_sta_dwell_sample_${sample}_gateway_neigh_state_after_get=$gateway_neigh_state_after_get"
    append_marker "wifi_sta_dwell_sample_${sample}_gateway_arp_state=$gateway_arp_state"
    append_marker "wifi_sta_dwell_sample_${sample}_gateway_arp_resolved=$gateway_arp_resolved"
    append_marker "wifi_sta_dwell_sample_${sample}_lease_router_present=$lease_router_present"
    append_marker "wifi_sta_dwell_sample_${sample}_lease_router_matches_initial=$lease_router_matches_initial"
    append_marker "wifi_sta_dwell_sample_${sample}_default_route_gateway_present=$default_route_gateway_present"
    append_marker "wifi_sta_dwell_sample_${sample}_default_route_gateway_matches_initial=$default_route_gateway_matches_initial"
    append_marker "wifi_sta_dwell_sample_${sample}_default_route_gateway_matches_lease=$default_route_gateway_matches_lease"
    append_marker "wifi_sta_dwell_sample_${sample}_dns_rc=$dns_probe_rc"
    append_marker "wifi_sta_dwell_sample_${sample}_tcp443_rc=$tcp_probe_rc"
    append_marker "wifi_sta_dwell_sample_${sample}_failure=$sample_failure"
    append_marker "wifi_sta_dwell_sample_${sample}_ok=$sample_ok"
    mark_phase "dwell-sample-$sample"

    if [ "$sample_ok" != "1" ]; then
      dwell_pass=0
      if [ "$first_fail_sample" = "0" ]; then
        first_fail_sample=$sample
        first_fail_reason=$sample_failure
      fi
    fi
    sample=$((sample + 1))
  done

  append_marker "wifi_sta_dwell_pass=$dwell_pass"
  append_marker "wifi_sta_dwell_first_fail_sample=$first_fail_sample"
  append_marker "wifi_sta_dwell_first_fail_reason=$first_fail_reason"
  if [ "$dwell_pass" = "1" ]; then
    mark_phase "dwell-pass"
    return 0
  fi
  mark_phase "dwell-fail"
  return 1
}

mkdir -p "$RUN_DIR"
RUN_ID="$(uptime_ms)-$$"
[ -n "$RUN_ID" ] || RUN_ID="0-$$"
append_marker "wifi_sta_run_id=$RUN_ID"
append_marker "wifi_sta_run_start_uptime_ms=$(uptime_ms)"
mark_phase "start"
append_marker "wifi_sta_requested=1"
append_marker "wifi_sta_iface=$IFACE"
append_marker "wifi_sta_config_path=$CONFIG"
immediate_snapshot_only=0
if [ -s "$IMMEDIATE_SNAPSHOT_ONLY" ]; then
  immediate_snapshot_only=1
fi
append_marker "wifi_sta_immediate_snapshot_only=$immediate_snapshot_only"

if [ ! -s "$ENABLE" ]; then
  mark_phase "manual-disabled"
  append_marker "wifi_sta_started=0"
  finish "wifi-sta-manual"
fi

if [ "$immediate_snapshot_only" = "1" ]; then
  append_marker "wifi_sta_config_required=0"
  append_marker "wifi_sta_config_present=0"
  if ! command -v ip >/dev/null 2>&1 ||
     ! command -v iw >/dev/null 2>&1; then
    mark_phase "immediate-missing-tools"
    append_marker "wifi_sta_started=0"
    finish "wifi-sta-immediate-snapshot-missing-tools"
  fi
else
  append_marker "wifi_sta_config_required=1"
  if [ ! -s "$CONFIG" ]; then
    mark_phase "config-missing"
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
    mark_phase "missing-tools"
    append_marker "wifi_sta_started=0"
    finish "wifi-sta-missing-tools"
  fi
  NC_BIN=$(command -v nc 2>/dev/null || command -v nc.openbsd 2>/dev/null || true)
  if [ -z "$NC_BIN" ]; then
    mark_phase "missing-nc"
    append_marker "wifi_sta_started=0"
    finish "wifi-sta-missing-tools"
  fi
fi
mark_phase "tools-ok"

ip link show "$IFACE" >/dev/null 2>&1
if [ "$?" != "0" ]; then
  mark_phase "wlan0-missing"
  append_marker "wifi_sta_wlan0_present=0"
  append_marker "wifi_sta_started=0"
  finish "wifi-sta-wlan0-missing"
fi
append_marker "wifi_sta_wlan0_present=1"
link_snapshot "before_link_up"

ip route replace 192.168.7.1 dev ncm0 >/dev/null 2>&1 || true
if ncm_recovery_preserved; then
  append_marker "ncm_recovery_preserved=1"
else
  append_marker "ncm_recovery_preserved=0"
fi

if [ "$immediate_snapshot_only" = "1" ]; then
  mark_phase "immediate-snapshot-before-link"
  link_snapshot "immediate_before_link_up"
  sample_regulatory_state "immediate_before_link_up"
  ip link set "$IFACE" up >/dev/null 2>&1
  immediate_link_set_up_rc=$?
  append_marker "wifi_sta_immediate_link_set_up_rc=$immediate_link_set_up_rc"
  link_snapshot "immediate_after_link_up"
  sample_regulatory_state "immediate_after_link_up"
  append_marker "wifi_sta_immediate_iw_scan_rc=$iw_scan_rc"
  append_marker "wifi_sta_immediate_iw_scan_bss_count=$iw_scan_bss_count"
  append_marker "wifi_sta_started=0"
  if [ "$iw_scan_rc" = "0" ]; then
    finish "wifi-sta-immediate-snapshot-pass"
  fi
  finish "wifi-sta-immediate-snapshot-scan-failed"
fi

kill_pidfile_if_matching "$DHCP_PID" "dhclient"
kill_pidfile_if_matching "$WPA_PID" "wpa_supplicant"
kill_matching_cmdline "$CONFIG"
rm -f "$WPA_LOG" "$DHCP_LOG" "$DHCP_LEASES" 2>/dev/null || true
mkdir -p "$WPA_CTRL_DIR"

ip link set "$IFACE" up >/dev/null 2>&1
link_set_up_rc=$?
append_marker "wifi_sta_link_set_up_rc=$link_set_up_rc"
link_snapshot "after_link_up"
if [ "$link_set_up_rc" != "0" ]; then
  mark_phase "link-up-failed"
  append_marker "wifi_sta_started=0"
  finish "wifi-sta-link-up-failed"
fi
mark_phase "link-up"
wpa_supplicant -B -q -i "$IFACE" -D nl80211 -c "$CONFIG" \
  -P "$WPA_PID" -f "$WPA_LOG" >/dev/null 2>&1
wpa_rc=$?
append_marker "wifi_sta_wpa_supplicant_rc=$wpa_rc"
link_snapshot "after_wpa_start"
if [ "$wpa_rc" != "0" ]; then
  mark_phase "wpa-start-failed"
  append_marker "wifi_sta_started=0"
  finish "wifi-sta-wpa-start-failed"
fi

append_marker "wifi_sta_started=1"
mark_phase "wpa-started"
if wpa_ctrl_wait; then
  mark_phase "ctrl-ready"
  link_snapshot "ctrl_ready_before_country"
  wpa_cli_quiet DRIVER COUNTRY KR
  append_marker "wifi_sta_ctrl_driver_country_rc=$?"
  sample_regulatory_state "after_country"
  link_snapshot "after_country"
  scan_visibility_probe "initial"
  append_marker "wifi_sta_ctrl_scan_rc=$scan_visibility_trigger_rc"
  append_marker "wifi_sta_ctrl_scan_found=$scan_visibility_found"
  link_snapshot "after_initial_scan"
  wpa_cli_quiet ENABLE_NETWORK 0
  append_marker "wifi_sta_ctrl_enable_network_rc=$?"
  wpa_cli_quiet SELECT_NETWORK 0
  append_marker "wifi_sta_ctrl_select_network_rc=$?"
  wpa_cli_quiet REASSOCIATE
  append_marker "wifi_sta_ctrl_reassociate_rc=$?"
  link_snapshot "after_reassociate"
  append_wpa_status_markers
  if ! wait_wpa_completed; then
    mark_phase "assoc-failed"
    append_wpa_status_markers
    append_marker "wifi_sta_carrier_up=0"
    finish "wifi-sta-assoc-failed"
  fi
  mark_phase "assoc-completed"
else
  mark_phase "ctrl-unavailable"
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
mark_phase "carrier-checked"
if [ "$ctrl_ready" = "1" ]; then
  append_wpa_status_markers
fi

dhclient -1 -q -4 -pf "$DHCP_PID" -lf "$DHCP_LEASES" "$IFACE" > "$DHCP_LOG" 2>&1
dhcp_rc=$?
append_marker "wifi_sta_dhcp_attempted=1"
append_marker "wifi_sta_dhcp_rc=$dhcp_rc"
mark_phase "dhcp-done"
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
  mark_phase "l3-initial-pass"
  if ! dwell_stability_probe "$router"; then
    finish "wifi-sta-dwell-failed"
  fi
  finish "wifi-sta-pass"
fi
if [ "$dhcp_rc" = "0" ]; then
  finish "wifi-sta-dhcp-no-wlan0-default"
fi
finish "wifi-sta-dhcp-failed"
