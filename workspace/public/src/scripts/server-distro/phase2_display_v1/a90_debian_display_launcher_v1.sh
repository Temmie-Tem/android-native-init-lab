#!/bin/sh
set -eu

PATH=/usr/sbin:/usr/bin:/sbin:/bin
RUN_DIR=/run/a90-display
PRESENTER=/usr/local/sbin/a90-debian-display-v1
DISPLAY_UID=3904
DISPLAY_GID=3904
MAX_ATTEMPTS=3

umask 077
mkdir -p "$RUN_DIR"
chown "$DISPLAY_UID:$DISPLAY_GID" "$RUN_DIR"
chmod 0700 "$RUN_DIR"
rm -f "$RUN_DIR/ready" "$RUN_DIR/ready.tmp" "$RUN_DIR/failure"

attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
  echo "$$" > "$RUN_DIR/launcher.pid"
  if "$PRESENTER" </dev/null >>"$RUN_DIR/presenter.log" 2>&1; then
    exit 0
  else
    rc=$?
  fi
  {
    echo schema=a90-debian-display-v1-failure
    echo attempt="$attempt"
    echo rc="$rc"
  } > "$RUN_DIR/failure"
  attempt=$((attempt + 1))
  if [ "$attempt" -le "$MAX_ATTEMPTS" ]; then
    sleep 1
  fi
done

exit 1
