#!/bin/sh
set -eu

PATH=/usr/sbin:/usr/bin:/sbin:/bin
RETURN_SUPERVISOR=/usr/local/sbin/a90-d3-return-supervisor-v3405
RETURN_PID_FILE=/run/a90-d3-return-supervisor.pid
MARKER=/run/a90-d3-marker
MARKER_TMP=/run/a90-d3-marker.tmp

umask 077
rm -f "$MARKER_TMP"

if ! RETURN_SUPERVISOR_PID=$("$RETURN_SUPERVISOR" --arm 120 20); then
  exit 71
fi
case "$RETURN_SUPERVISOR_PID" in
  ''|*[!0-9]*) exit 72 ;;
esac

PID1_EXE=$(readlink /proc/1/exe 2>/dev/null || true)
if [ "$PID1_EXE" != /usr/sbin/init ]; then
  exit 73
fi

mkdir -p /run /tmp
printf '%s\n' "$RETURN_SUPERVISOR_PID" > "$RETURN_PID_FILE"

{
  echo A90D3_MARKER
  echo schema=a90-phase3-network-ssh-v1-return-arm
  echo stage=D3-phase3-network-ssh-v1
  echo debian_version=$(cat /etc/debian_version 2>/dev/null)
  echo pid1_comm=$(cat /proc/1/comm 2>/dev/null)
  echo proc1_exe="$PID1_EXE"
  echo return_supervisor_pid="$RETURN_SUPERVISOR_PID"
  echo return_delay_sec=120
  echo sync_grace_sec=20
  echo recovery_action=sysrq-b-only
  echo service_bootstrap=/usr/local/sbin/a90-debian-network-ssh-v1
  test -f /etc/a90-server-distro-stage && cat /etc/a90-server-distro-stage
} > "$MARKER_TMP"
mv "$MARKER_TMP" "$MARKER"

exit 0
