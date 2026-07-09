#!/system/bin/sh

DAEMON="$1"
STOCK_SERVICE="DR-daemon"
STOCK_PROCESS="ddexe"
MARKER="/dev/.s22plus_o1_control_once"
STATUS="/dev/.s22plus_o1_status"
MAX_REQUESTS=128
IDLE_TIMEOUT_MS=180000
RESTORE_REQUIRED=0
FINALIZED=0

stock_has_tty_owner() {
    for pid in $(pidof "$STOCK_PROCESS" 2>/dev/null); do
        for fd in /proc/$pid/fd/*; do
            target=$(readlink "$fd" 2>/dev/null || true)
            if [ "$target" = "/dev/ttyGS0" ]; then
                return 0
            fi
        done
    done
    return 1
}

wait_stock_state() {
    expected="$1"
    count=0
    while [ "$count" -lt 100 ]; do
        state=$(getprop "init.svc.$STOCK_SERVICE")
        if [ "$expected" = "running" ]; then
            if [ "$state" = "running" ] && stock_has_tty_owner; then
                return 0
            fi
        else
            if [ "$state" = "stopped" ] && ! pidof "$STOCK_PROCESS" >/dev/null 2>&1; then
                return 0
            fi
        fi
        sleep 0.1
        count=$((count + 1))
    done
    return 1
}

restore_stock_service() {
    if [ "$RESTORE_REQUIRED" -ne 1 ]; then
        return 0
    fi
    setprop ctl.start "$STOCK_SERVICE" || return 1
    wait_stock_state running
}

on_exit() {
    shell_rc=$?
    restore_stock_service
    restore_rc=$?
    if [ "$FINALIZED" -ne 1 ]; then
        printf 'result=aborted\nshell_rc=%s\nrestore_rc=%s\n' "$shell_rc" "$restore_rc" >"$STATUS"
    fi
    trap - EXIT
    exit "$shell_rc"
}

trap on_exit EXIT
trap 'exit 128' HUP INT TERM

if [ -e "$MARKER" ]; then
    FINALIZED=1
    exit 0
fi
printf 'phase=started\n' >"$STATUS" || exit 19

if [ ! -x "$DAEMON" ] || [ ! -c /dev/ttyGS0 ]; then
    exit 21
fi
if ! wait_stock_state running; then
    exit 22
fi
: >"$MARKER" || exit 20
printf 'phase=handoff\n' >"$STATUS" || exit 19

RESTORE_REQUIRED=1
setprop ctl.stop "$STOCK_SERVICE" || exit 23
if ! wait_stock_state stopped; then
    exit 24
fi

printf 'phase=daemon-running\n' >"$STATUS" || exit 19
"$DAEMON" \
    --device /dev/ttyGS0 \
    --max-requests "$MAX_REQUESTS" \
    --idle-timeout-ms "$IDLE_TIMEOUT_MS"
daemon_rc=$?

restore_stock_service
restore_rc=$?
RESTORE_REQUIRED=0
FINALIZED=1
if [ "$daemon_rc" -eq 0 ] && [ "$restore_rc" -eq 0 ]; then
    printf 'result=pass\ndaemon_rc=0\nrestore_rc=0\n' >"$STATUS"
else
    printf 'result=fail\ndaemon_rc=%s\nrestore_rc=%s\n' "$daemon_rc" "$restore_rc" >"$STATUS"
fi
trap - EXIT HUP INT TERM

if [ "$restore_rc" -ne 0 ]; then
    exit 25
fi
exit "$daemon_rc"
