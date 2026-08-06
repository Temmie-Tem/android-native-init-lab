#!/bin/sh
set -u

PATH=/usr/sbin:/usr/bin:/sbin:/bin
RUN_DIR=/run/a90-services
READY=$RUN_DIR/ready
READY_TMP=$RUN_DIR/ready.tmp
FAILURE=$RUN_DIR/failure
FAILURE_TMP=$RUN_DIR/failure.tmp
IFACE=ncm0
NCM_ADDR=192.168.7.2/24
NCM_IP=192.168.7.2
NCM_PEER=192.168.7.1
SSH_PORT=2222
AUTHORIZED_KEYS=/root/.ssh/authorized_keys
HOST_KEY=/etc/dropbear/dropbear_ed25519_host_key
DROPBEAR_PIDFILE=/run/a90-d3-dropbear.pid
DROPBEAR_LOG=/run/a90-d3-dropbear.log
DROPBEARKEY_LOG=/run/a90-d3-dropbearkey.log
TIMEOUT=/usr/bin/timeout
IP=/usr/bin/ip
SS=/usr/bin/ss
STAT=/usr/bin/stat
MAX_PID_POLLS=10
MAX_CLEANUP_POLLS=5
STARTED_PID=
LAUNCHED_PID=
DROPBEAR_DISPATCHED=0
RESTORE_LINK_DOWN=0
REMOVE_ADDR=0
REMOVE_ROUTE=0
REMOVE_HOST_KEY=0
DROPBEAR_CLEANUP=not-needed
NETWORK_CLEANUP=not-needed
HOST_KEY_CLEANUP=not-needed

umask 077

process_is_started_dropbear() {
  case "$STARTED_PID" in
    ''|*[!0-9]*) return 1 ;;
  esac
  [ "$(readlink "/proc/$STARTED_PID/exe" 2>/dev/null || true)" = /usr/sbin/dropbear ]
}

listener_state_for_started_pid() {
  case "$STARTED_PID" in
    ''|*[!0-9]*) return 1 ;;
  esac
  listener_owner="\"dropbear\",pid=$STARTED_PID,"
  if ! listener_snapshot=$("$TIMEOUT" 5 "$SS" -H -ltnp "sport = :$SSH_PORT" 2>/dev/null); then
    return 2
  fi
  case "$listener_snapshot" in
    *"$listener_owner"*) return 0 ;;
    '') return 1 ;;
    *) return 3 ;;
  esac
}

wait_for_dropbear_exit() {
  cleanup_poll=0
  while [ "$cleanup_poll" -lt "$MAX_CLEANUP_POLLS" ]; do
    process_present=0
    process_is_started_dropbear && process_present=1
    listener_state_for_started_pid
    listener_state=$?
    if [ "$listener_state" -eq 2 ]; then
      return 2
    fi
    if [ "$process_present" -eq 0 ] && [ "$listener_state" -eq 1 ]; then
      return 0
    fi
    cleanup_poll=$((cleanup_poll + 1))
    sleep 1
  done
  return 1
}

cleanup_started_dropbear() {
  [ "$DROPBEAR_DISPATCHED" -eq 1 ] || return
  case "$STARTED_PID" in
    ''|*[!0-9]*)
      DROPBEAR_CLEANUP=not-addressable
      return
      ;;
  esac
  DROPBEAR_CLEANUP=complete
  if process_is_started_dropbear; then
    kill "$STARTED_PID" 2>/dev/null || true
  fi
  wait_for_dropbear_exit
  wait_rc=$?
  if [ "$wait_rc" -eq 0 ]; then
    rm -f "$DROPBEAR_PIDFILE"
    [ ! -e "$DROPBEAR_PIDFILE" ] && [ ! -L "$DROPBEAR_PIDFILE" ] || DROPBEAR_CLEANUP=failed
    return
  fi
  if process_is_started_dropbear; then
    kill -KILL "$STARTED_PID" 2>/dev/null || true
  fi
  wait_for_dropbear_exit
  wait_rc=$?
  if [ "$wait_rc" -eq 0 ]; then
    rm -f "$DROPBEAR_PIDFILE"
    [ ! -e "$DROPBEAR_PIDFILE" ] && [ ! -L "$DROPBEAR_PIDFILE" ] || DROPBEAR_CLEANUP=failed
    return
  fi
  DROPBEAR_CLEANUP=failed
}

cleanup_network() {
  if [ "$REMOVE_ROUTE" -eq 0 ] && [ "$REMOVE_ADDR" -eq 0 ] && [ "$RESTORE_LINK_DOWN" -eq 0 ]; then
    return
  fi
  NETWORK_CLEANUP=complete
  if [ "$REMOVE_ROUTE" -eq 1 ]; then
    "$TIMEOUT" 10 "$IP" route del "$NCM_PEER" dev "$IFACE" >/dev/null 2>&1 || true
    if cleanup_route=$("$TIMEOUT" 10 "$IP" route show exact "$NCM_PEER" 2>/dev/null); then
      [ -z "$cleanup_route" ] || NETWORK_CLEANUP=failed
    else
      NETWORK_CLEANUP=failed
    fi
  fi
  if [ "$REMOVE_ADDR" -eq 1 ]; then
    "$TIMEOUT" 10 "$IP" addr del "$NCM_ADDR" dev "$IFACE" >/dev/null 2>&1 || true
    if cleanup_addr=$("$TIMEOUT" 10 "$IP" -o -4 addr show dev "$IFACE" scope global 2>/dev/null); then
      [ -z "$cleanup_addr" ] || NETWORK_CLEANUP=failed
    else
      NETWORK_CLEANUP=failed
    fi
  fi
  if [ "$RESTORE_LINK_DOWN" -eq 1 ]; then
    "$TIMEOUT" 10 "$IP" link set "$IFACE" down >/dev/null 2>&1 || true
    if cleanup_link=$("$TIMEOUT" 10 "$IP" -o link show dev "$IFACE" 2>/dev/null); then
      cleanup_flags=${cleanup_link#*<}
      if [ "$cleanup_flags" = "$cleanup_link" ]; then
        NETWORK_CLEANUP=failed
      else
        cleanup_flags=${cleanup_flags%%>*}
        case ",$cleanup_flags," in
          *,UP,*) NETWORK_CLEANUP=failed ;;
        esac
      fi
    else
      NETWORK_CLEANUP=failed
    fi
  fi
}

cleanup_host_key() {
  [ "$REMOVE_HOST_KEY" -eq 1 ] || return
  HOST_KEY_CLEANUP=complete
  rm -f "$HOST_KEY"
  [ ! -e "$HOST_KEY" ] && [ ! -L "$HOST_KEY" ] || HOST_KEY_CLEANUP=failed
}

fail() {
  code=$1
  failure_stage=$2
  cleanup_started_dropbear
  cleanup_network
  cleanup_host_key
  rm -f "$READY" "$READY_TMP" "$FAILURE_TMP"
  {
    echo schema=a90-debian-network-ssh-v1-failure
    echo owner=debian-sysvinit
    echo stage="$failure_stage"
    echo code="$code"
    echo dropbear_cleanup="$DROPBEAR_CLEANUP"
    echo network_cleanup="$NETWORK_CLEANUP"
    echo host_key_cleanup="$HOST_KEY_CLEANUP"
  } > "$FAILURE_TMP"
  mv "$FAILURE_TMP" "$FAILURE"
  exit "$code"
}

PID1_EXE=$(readlink /proc/1/exe 2>/dev/null || true)
if [ "$PID1_EXE" != /usr/sbin/init ]; then
  fail 80 pid1-not-debian-init
fi

# On-device same-ordinal evidence, unpacked to tmpfs and backgrounded.
# Generated from a90_ondevice_evidence_v1.service_block(); do not edit here.
# Never gating: every failure path leaves the boot alone, because the
# instrument must not become one more way for a defect to kill an ordinal.
cat > /run/a90-ondevice-evidence-v1 <<'A90_ONDEV_EOF' || true
#!/bin/sh
# a90-ondevice-evidence-v1 -- append one durable evidence line and exit.
# Generated from a90_ondevice_evidence_v1.writer_script(); do not edit in place.
set -u

RECORD=/mnt/sdext/a90/runtime/a90-ondevice-evidence-v1.log
RUN_FILE=/mnt/sdext/a90/runtime/a90-ondevice-evidence-run
PHASE=${1:-}
RUN=${2:-}

[ -n "$PHASE" ] || exit 2

# The rootfs hook only has to know the phase. native-init published the run
# identity beside the record before it dispatched this handoff.
if [ -z "$RUN" ] && [ -r "$RUN_FILE" ]; then
    RUN=$(tr -d '\r\n\t ' < "$RUN_FILE" 2>/dev/null)
fi
[ -n "$RUN" ] || exit 2

# /proc/uptime is centisecond CLOCK_BOOTTIME, the same axis native-init stamps
# its benchmark markers on. Leading zeros are stripped by hand because bash's
# 10# base prefix is not POSIX and silently yields an empty stamp under dash --
# which is what Debian's /bin/sh actually is.
uptime_ms() {
    read -r _up _idle < /proc/uptime 2>/dev/null || { echo na; return; }
    case "$_up" in
        *.*) _sec=${_up%%.*}; _cs=${_up#*.}; _cs=${_cs%%[!0-9]*} ;;
        *) _sec=$_up; _cs=0 ;;
    esac
    case "$_sec" in ''|*[!0-9]*) echo na; return ;; esac
    [ -n "$_cs" ] || _cs=0
    while [ ${#_cs} -gt 1 ]; do
        case "$_cs" in 0*) _cs=${_cs#0} ;; *) break ;; esac
    done
    echo $(( _sec * 1000 + _cs * 10 ))
}

# Values become key=value tokens, so any whitespace inside one would split the
# record. Strip it here rather than trusting every source path.
read_or_na() {
    _v=""
    if [ -r "$1" ]; then
        _v=$(tr -d '\r\n\t ' < "$1" 2>/dev/null)
    fi
    [ -n "$_v" ] || _v=na
    printf '%s\n' "$_v"
}

exists_flag() {
    if [ -e "$1" ]; then echo 1; else echo 0; fi
}

dropbear_listening() {
    for _f in /proc/net/tcp /proc/net/tcp6; do
        [ -r "$_f" ] || continue
        # local_address is field 2 as ADDR:PORT, state 0A is LISTEN.
        if awk -v p=":08AE" '$2 ~ p"$" && $4 == "0A" { found = 1 }
                 END { exit !found }' "$_f" 2>/dev/null; then
            echo 1
            return
        fi
    done
    echo 0
}

drm_card0() {
    if [ -c /dev/dri/card0 ]; then echo char; else echo absent; fi
}

PID1_COMM=$(read_or_na /proc/1/comm)
PROC1_EXE=$(readlink /proc/1/exe 2>/dev/null | tr -d '\r\n\t ')
[ -n "$PROC1_EXE" ] || PROC1_EXE=na

LINE="A90OBSREC schema=a90-ondevice-evidence-v1"
LINE="$LINE phase=$PHASE"
LINE="$LINE uptime_ms=$(uptime_ms)"
LINE="$LINE run=$RUN"
LINE="$LINE pid1_comm=$PID1_COMM"
LINE="$LINE proc1_exe=$PROC1_EXE"
LINE="$LINE drm_card0=$(drm_card0)"
LINE="$LINE drm_master=$(exists_flag /run/a90-display/ready)"
LINE="$LINE dropbear=$(dropbear_listening)"
LINE="$LINE display_ready=$(exists_flag /run/a90-display/ready)"
LINE="$LINE display_failure=$(exists_flag /run/a90-display/failure)"

mkdir -p "$(dirname "$RECORD")" 2>/dev/null || true
# One append, one line, then sync. A truncated tail from power loss is a
# discarded line on the read side, never a rejected record.
printf '%s\n' "$LINE" >> "$RECORD" 2>/dev/null || exit 1
sync 2>/dev/null || true
exit 0
A90_ONDEV_EOF
chmod 0755 /run/a90-ondevice-evidence-v1 2>/dev/null || true
cat > /run/a90-debian-ondevice-evidence-hook-v1 <<'A90_ONDEV_EOF' || true
#!/bin/sh
# a90-debian-ondevice-evidence-hook-v1 -- record same-ordinal Debian facts.
# Generated from a90_ondevice_evidence_v1.hook_script(); do not edit in place.
set -u
PATH=/usr/sbin:/usr/bin:/sbin:/bin

COLLECT=/run/a90-ondevice-evidence-v1
[ -x "$COLLECT" ] || exit 0

record() { "$COLLECT" "$1" >/dev/null 2>&1 || true; }

wait_for_any() {
    _limit=$1
    shift
    _waited=0
    while [ "$_waited" -lt "$_limit" ]; do
        for _p in "$@"; do
            [ -e "$_p" ] && return 0
        done
        _waited=$(( _waited + 1 ))
        sleep 1
    done
    return 1
}

# PID 1 is Debian by the time sysinit runs this, so the first stamp needs no
# wait.
record debian_pid1

# Each phase is stamped when its own signal arrives, in the order inittab
# actually produces them: the network/SSH service is a blocking entry and the
# display launcher runs after it. Waiting for the later signal first would
# stamp the earlier phase at the wrong time and report a boot slower than it
# was. Either outcome ends a wait -- a recorded failure is evidence, not a
# reason to keep polling. The collector independently reads /proc/net/tcp for
# the listener, so it and this signal do not share a failure mode.
wait_for_any 90 /run/a90-services/ready /run/a90-services/failure || true
record debian_sshd

wait_for_any 90 /run/a90-display/ready /run/a90-display/failure || true
record debian_drm_master

exit 0
A90_ONDEV_EOF
chmod 0755 /run/a90-debian-ondevice-evidence-hook-v1 2>/dev/null || true
if [ -x /run/a90-debian-ondevice-evidence-hook-v1 ]; then
  /run/a90-debian-ondevice-evidence-hook-v1 >/dev/null 2>&1 &
fi

mkdir -p "$RUN_DIR" /root/.ssh /etc/dropbear || fail 81 runtime-directory
chmod 0700 "$RUN_DIR" /root/.ssh || fail 81 runtime-directory-mode
rm -f "$READY" "$READY_TMP" "$FAILURE" "$FAILURE_TMP"

for tool in "$TIMEOUT" "$IP" "$SS" "$STAT" /usr/bin/dropbearkey /usr/sbin/dropbear; do
  [ -x "$tool" ] || fail 82 missing-tool
done
[ -e "/sys/class/net/$IFACE" ] || fail 83 ncm-interface-absent

[ ! -L "$AUTHORIZED_KEYS" ] || fail 89 authorized-keys-symlink
[ -s "$AUTHORIZED_KEYS" ] || fail 89 authorized-keys-absent
AUTH_META=$("$STAT" -c '%u:%g:%a' "$AUTHORIZED_KEYS" 2>/dev/null) || fail 89 authorized-keys-stat
if [ "$AUTH_META" != 0:0:600 ]; then
  fail 89 authorized-keys-metadata
fi

LINK_STATE=$("$TIMEOUT" 10 "$IP" -o link show dev "$IFACE" 2>/dev/null) || fail 83 ncm-link-read
LINK_FLAGS=${LINK_STATE#*<}
if [ "$LINK_FLAGS" = "$LINK_STATE" ]; then
  fail 83 ncm-link-flags-malformed
fi
LINK_FLAGS=${LINK_FLAGS%%>*}
case ",$LINK_FLAGS," in
  *,UP,*) ;;
  *) RESTORE_LINK_DOWN=1 ;;
esac

PRE_ADDR_STATE=$("$TIMEOUT" 10 "$IP" -o -4 addr show dev "$IFACE" scope global 2>/dev/null) || fail 83 ncm-pre-address-read
PRE_ADDR_LINES=$(printf '%s\n' "$PRE_ADDR_STATE" | awk 'NF { count += 1 } END { print count + 0 }')
if [ "$PRE_ADDR_LINES" -eq 0 ]; then
  REMOVE_ADDR=1
elif [ "$PRE_ADDR_LINES" -eq 1 ]; then
  case "$PRE_ADDR_STATE" in
    *" inet $NCM_ADDR "*) ;;
    *) fail 83 ncm-pre-address-conflict ;;
  esac
else
  fail 83 ncm-pre-address-conflict
fi

PRE_ROUTE_STATE=$("$TIMEOUT" 10 "$IP" route show exact "$NCM_PEER" 2>/dev/null) || fail 83 ncm-pre-route-read
PRE_ROUTE_LINES=$(printf '%s\n' "$PRE_ROUTE_STATE" | awk 'NF { count += 1 } END { print count + 0 }')
if [ "$PRE_ROUTE_LINES" -eq 0 ]; then
  REMOVE_ROUTE=1
elif [ "$PRE_ROUTE_LINES" -eq 1 ]; then
  case "$PRE_ROUTE_STATE" in
    "$NCM_PEER dev $IFACE"*) ;;
    *) fail 83 ncm-pre-route-conflict ;;
  esac
else
  fail 83 ncm-pre-route-conflict
fi

[ ! -L "$HOST_KEY" ] || fail 90 host-key-symlink
if [ ! -s "$HOST_KEY" ]; then
  REMOVE_HOST_KEY=1
  "$TIMEOUT" 20 /usr/bin/dropbearkey -t ed25519 -f "$HOST_KEY" >"$DROPBEARKEY_LOG" 2>&1 || fail 90 host-key-generate
fi
HOST_META=$("$STAT" -c '%u:%g:%a' "$HOST_KEY" 2>/dev/null) || fail 90 host-key-stat
if [ "$HOST_META" != 0:0:600 ]; then
  fail 90 host-key-metadata
fi

if [ "$RESTORE_LINK_DOWN" -eq 1 ]; then
  "$TIMEOUT" 10 "$IP" link set "$IFACE" up >/dev/null 2>&1 || fail 84 ncm-link-up
fi
if [ "$REMOVE_ADDR" -eq 1 ]; then
  "$TIMEOUT" 10 "$IP" addr replace "$NCM_ADDR" dev "$IFACE" >/dev/null 2>&1 || fail 85 ncm-address-set
fi
ADDR_STATE=$("$TIMEOUT" 10 "$IP" -o -4 addr show dev "$IFACE" scope global 2>/dev/null) || fail 86 ncm-address-read
ADDR_LINES=$(printf '%s\n' "$ADDR_STATE" | awk 'NF { count += 1 } END { print count + 0 }')
if [ "$ADDR_LINES" -ne 1 ]; then
  fail 86 ncm-address-not-exact
fi
case "$ADDR_STATE" in
  *" inet $NCM_ADDR "*) ;;
  *) fail 86 ncm-address-mismatch ;;
esac

if [ "$REMOVE_ROUTE" -eq 1 ]; then
  "$TIMEOUT" 10 "$IP" route replace "$NCM_PEER" dev "$IFACE" >/dev/null 2>&1 || fail 87 ncm-route-set
fi
ROUTE_STATE=$("$TIMEOUT" 10 "$IP" route show exact "$NCM_PEER" 2>/dev/null) || fail 88 ncm-route-read
ROUTE_LINES=$(printf '%s\n' "$ROUTE_STATE" | awk 'NF { count += 1 } END { print count + 0 }')
if [ "$ROUTE_LINES" -ne 1 ]; then
  fail 88 ncm-route-not-exact
fi
case "$ROUTE_STATE" in
  "$NCM_PEER dev $IFACE"*) ;;
  *) fail 88 ncm-route-mismatch ;;
esac

rm -f "$DROPBEAR_PIDFILE"
/usr/sbin/dropbear -F -E -r "$HOST_KEY" \
  -p "$NCM_IP:$SSH_PORT" -P "$DROPBEAR_PIDFILE" -s -j -k \
  >>"$DROPBEAR_LOG" 2>&1 &
LAUNCHED_PID=$!
STARTED_PID=$LAUNCHED_PID
DROPBEAR_DISPATCHED=1

poll=0
while [ "$poll" -lt "$MAX_PID_POLLS" ]; do
  if [ -s "$DROPBEAR_PIDFILE" ] && process_is_started_dropbear && listener_state_for_started_pid; then
    break
  fi
  poll=$((poll + 1))
  sleep 1
done
[ -s "$DROPBEAR_PIDFILE" ] || fail 92 dropbear-pid-timeout
PIDFILE_PID=$(cat "$DROPBEAR_PIDFILE" 2>/dev/null || true)
case "$PIDFILE_PID" in
  ''|*[!0-9]*) fail 92 dropbear-pid-malformed ;;
esac
if [ "$PIDFILE_PID" -ne "$LAUNCHED_PID" ]; then
  fail 92 dropbear-pid-not-child
fi
STARTED_PID=$PIDFILE_PID
kill -0 "$STARTED_PID" 2>/dev/null || fail 93 dropbear-not-live
if [ "$(readlink "/proc/$STARTED_PID/exe" 2>/dev/null || true)" != /usr/sbin/dropbear ]; then
  fail 93 dropbear-exe-mismatch
fi

LISTEN_STATE=$("$TIMEOUT" 10 "$SS" -H -ltnp "sport = :$SSH_PORT" 2>/dev/null) || fail 94 dropbear-listener-read
LISTEN_LINES=$(printf '%s\n' "$LISTEN_STATE" | awk 'NF { count += 1 } END { print count + 0 }')
if [ "$LISTEN_LINES" -ne 1 ]; then
  fail 94 dropbear-listener-not-exact
fi
case "$LISTEN_STATE" in
  *"$NCM_IP:$SSH_PORT"*) ;;
  *) fail 94 dropbear-listener-mismatch ;;
esac
LISTENER_OWNER="\"dropbear\",pid=$STARTED_PID,"
case "$LISTEN_STATE" in
  *"$LISTENER_OWNER"*) ;;
  *) fail 94 dropbear-listener-owner-mismatch ;;
esac

{
  echo schema=a90-debian-network-ssh-v1-ready
  echo owner=debian-sysvinit
  echo pid1_exe="$PID1_EXE"
  echo ncm_ifname="$IFACE"
  echo ncm_address="$NCM_ADDR"
  echo ncm_peer="$NCM_PEER"
  echo dropbear_pid="$STARTED_PID"
  echo dropbear_listen="$NCM_IP:$SSH_PORT"
  echo dropbear_auth=public-key-only
  echo dropbear_forwarding=disabled
} > "$READY_TMP"
mv "$READY_TMP" "$READY"
rm -f "$FAILURE" "$FAILURE_TMP"

exit 0
