#!/bin/sh
# D-public Debian appliance firstboot profile.
#
# Runs after native-init switch_root into the userdata Debian root.  This is the
# visual/server demo profile: no proof-only autoreboot, USB/NCM admin path,
# loopback smoke service, optional tunnel service, and Debian-owned KMS HUD.
set +e
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

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

cleanup_cloudflared_runtime() {
  reason=$1
  kill_matching_cmdline "/usr/local/bin/cloudflared tunnel"
  for pidfile in /run/a90-dpublic/cloudflared-*.pid; do
    kill_pidfile_if_matching "$pidfile" "/usr/local/bin/cloudflared tunnel"
  done
  rm -f /run/a90-dpublic/cloudflared-*.log \
        /run/a90-dpublic/cloudflared-*.url \
        /run/a90-dpublic/cloudflared-*-url.txt \
        /run/a90-dpublic/public-url.txt 2>/dev/null || true
  [ -f /run/a90-d3-marker ] &&
    echo cloudflared_runtime_cleanup="$reason" >> /run/a90-d3-marker
}

wait_no_tcp_listen() {
  port_hex=$1
  for _ in 1 2 3 4 5; do
    grep -qi ":$port_hex .* 0A " /proc/net/tcp 2>/dev/null || return 0
    sleep 1
  done
  return 1
}

observe_cloudflared_start() {
  pidfile=/run/a90-dpublic/cloudflared-live.pid
  logfile=/run/a90-dpublic/cloudflared-live.log
  urlfile=/run/a90-dpublic/cloudflared-live.url
  pid=$(cat "$pidfile" 2>/dev/null || true)
  alive=0
  url_observed=0

  case "$pid" in
    ''|*[!0-9]*) pid= ;;
  esac

  for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      alive=1
    else
      alive=0
      break
    fi

    url=$(grep -Eo 'https://[^ ]+trycloudflare.com' "$logfile" 2>/dev/null | tail -1)
    if [ -n "$url" ]; then
      printf '%s\n' "$url" > "$urlfile"
      chmod 600 "$urlfile" 2>/dev/null || true
      url_observed=1
      break
    fi
    sleep 1
  done

  echo tunnel_process_alive=$alive >> /run/a90-d3-marker
  echo tunnel_url_observed=$url_observed >> /run/a90-d3-marker
  if [ "$url_observed" = "1" ]; then
    echo tunnel_decision=quick-url-ready >> /run/a90-d3-marker
  elif [ "$alive" = "1" ]; then
    echo tunnel_decision=quick-url-pending >> /run/a90-d3-marker
  else
    echo tunnel_decision=quick-process-exited >> /run/a90-d3-marker
  fi
}

mkdir -p /run /tmp /root/.ssh /etc/dropbear /run/a90-dpublic /etc/a90-dpublic
chmod 700 /root/.ssh 2>/dev/null || true

IP=/usr/sbin/ip
[ -x "$IP" ] || IP=/usr/bin/ip

"$IP" link set lo up >/dev/null 2>&1 || true
"$IP" link set ncm0 up >/dev/null 2>&1 || true
"$IP" addr replace 192.168.7.2/24 dev ncm0 >/dev/null 2>&1 || true
"$IP" route replace 192.168.7.1 dev ncm0 >/dev/null 2>&1 || true
"$IP" route replace default via 192.168.7.1 dev ncm0 >/dev/null 2>&1 || true

cat > /etc/hosts <<'EOF'
127.0.0.1 localhost
::1 localhost ip6-localhost ip6-loopback
192.168.7.2 a90-dpublic
EOF
printf 'nameserver 1.1.1.1\n' > /etc/resolv.conf

{
  echo A90DPUBLIC_MARKER
  echo stage=D-public-live-gate
  echo debian_version=$(cat /etc/debian_version 2>/dev/null)
  echo pid1_comm=$(cat /proc/1/comm 2>/dev/null)
  echo proc1_exe=$(readlink /proc/1/exe 2>/dev/null)
  echo ncm_ip=192.168.7.2
  echo autoreboot_sec=disabled
  if [ -f /etc/a90-server-distro-stage ]; then
    while IFS= read -r line; do
      case "$line" in
        stage=*|autoreboot_sec=*) echo base_"$line" ;;
        *) echo "$line" ;;
      esac
    done < /etc/a90-server-distro-stage
  fi
  test -f /etc/a90-appliance-stage && echo appliance_marker=$(cat /etc/a90-appliance-stage)
} > /run/a90-d3-marker

if [ ! -s /etc/dropbear/dropbear_ed25519_host_key ]; then
  /usr/bin/dropbearkey -t ed25519 -f /etc/dropbear/dropbear_ed25519_host_key \
    >/run/a90-d3-dropbearkey.log 2>&1
fi

if [ -s /root/.ssh/authorized_keys ]; then
  /usr/sbin/dropbear -E -r /etc/dropbear/dropbear_ed25519_host_key \
    -p 192.168.7.2:2222 -P /run/a90-d3-dropbear.pid -s -j -k \
    >>/run/a90-d3-dropbear.log 2>&1
  echo dropbear_started=1 >> /run/a90-d3-marker
else
  echo dropbear_started=0 >> /run/a90-d3-marker
fi

if [ -x /usr/local/bin/a90-dpublic-smoke-httpd ]; then
  if [ -s /run/a90-dpublic/smoke.pid ]; then
    kill "$(cat /run/a90-dpublic/smoke.pid)" 2>/dev/null || true
  fi
  kill_matching_cmdline "/usr/local/bin/a90-dpublic-smoke-httpd"
  wait_no_tcp_listen 1F90 || true
  /usr/local/bin/a90-dpublic-smoke-httpd 127.0.0.1 8080 \
    >/run/a90-dpublic/smoke.log 2>&1 &
  echo $! > /run/a90-dpublic/smoke.pid
  sleep 1
  if kill -0 "$(cat /run/a90-dpublic/smoke.pid)" 2>/dev/null; then
    echo smoke_started=1 >> /run/a90-d3-marker
  else
    echo smoke_started=0 >> /run/a90-d3-marker
  fi
else
  echo smoke_started=0 >> /run/a90-d3-marker
fi

# If native-init left a non-PID1 /init child holding DRM master, release it so
# Debian can own KMS.  PID1 is Debian sysvinit at this point and is never killed.
for status in /proc/[0-9]*/status; do
  pid=${status#/proc/}
  pid=${pid%/status}
  [ "$pid" = "1" ] && continue
  exe=$(readlink "/proc/$pid/exe" 2>/dev/null || true)
  [ "$exe" = "/init" ] || continue
  for fd in "/proc/$pid"/fd/*; do
    target=$(readlink "$fd" 2>/dev/null || true)
    case "$target" in
      *dri*|*card0*|*drm*)
        kill "$pid" 2>/dev/null || true
        ;;
    esac
  done
done

if [ -x /usr/local/bin/a90-dpublic-hud ]; then
  if [ -s /run/a90-dpublic/hud.pid ]; then
    kill "$(cat /run/a90-dpublic/hud.pid)" 2>/dev/null || true
  fi
  kill_matching_cmdline "/usr/local/bin/a90-dpublic-hud"
  for _ in 1 2 3 4 5; do
    drm_busy=0
    for fd in /proc/[0-9]*/fd/*; do
      target=$(readlink "$fd" 2>/dev/null || true)
      case "$target" in
        *dri*|*card0*|*drm*) drm_busy=1 ;;
      esac
    done
    [ "$drm_busy" = "0" ] && break
    sleep 1
  done
  /usr/local/bin/a90-dpublic-hud 2 >/run/a90-dpublic/hud.log 2>&1 &
  echo $! > /run/a90-dpublic/hud.pid
  sleep 1
  if kill -0 "$(cat /run/a90-dpublic/hud.pid)" 2>/dev/null; then
    echo hud_started=1 >> /run/a90-d3-marker
  else
    echo hud_started=0 >> /run/a90-d3-marker
  fi
else
  echo hud_started=0 >> /run/a90-d3-marker
fi

if [ -s /etc/a90-dpublic/wifi-sta-enable ]; then
  if [ -x /usr/local/bin/a90-dpublic-wifi-sta ]; then
    /usr/local/bin/a90-dpublic-wifi-sta >/run/a90-dpublic/wifi-sta-firstboot.log 2>&1
  else
    echo wifi_sta_requested=1 >> /run/a90-d3-marker
    echo wifi_sta_started=0 >> /run/a90-d3-marker
    echo wifi_sta_decision=wifi-sta-helper-missing >> /run/a90-d3-marker
    echo wifi_sta_secret_values_logged=0 >> /run/a90-d3-marker
  fi
else
  echo wifi_sta_requested=0 >> /run/a90-d3-marker
  echo wifi_sta_started=0 >> /run/a90-d3-marker
  echo wifi_sta_decision=wifi-sta-manual >> /run/a90-d3-marker
  echo wifi_sta_secret_values_logged=0 >> /run/a90-d3-marker
fi

if [ -s /etc/a90-dpublic/cloudflared-quick-enable ] &&
   [ -x /usr/local/bin/cloudflared ]; then
  cleanup_cloudflared_runtime enabled-prestart
  /usr/local/bin/cloudflared tunnel --no-autoupdate \
    --url http://127.0.0.1:8080 --metrics 127.0.0.1:0 --loglevel info \
    >/run/a90-dpublic/cloudflared-live.log 2>&1 &
  echo $! > /run/a90-dpublic/cloudflared-live.pid
  echo tunnel_started=1 >> /run/a90-d3-marker
  observe_cloudflared_start
else
  cleanup_cloudflared_runtime manual
  echo tunnel_started=manual >> /run/a90-d3-marker
  echo tunnel_process_alive=0 >> /run/a90-d3-marker
  echo tunnel_url_observed=0 >> /run/a90-d3-marker
  echo tunnel_decision=manual >> /run/a90-d3-marker
fi

exit 0
