# Server-Distro D-public Boot Visual HUD

- Date: 2026-07-04 KST
- Unit: D-public Debian-owned visual handoff and status HUD.
- Private HUD run: `workspace/private/runs/server-distro/dpublic-hud-20260703T153322Z`
- Private live run: `workspace/private/runs/server-distro/dpublic-live-20260703T150145Z`
- Public URL: redacted from committed report; stored only in the private live run.

## Verdict

D-public boot visual handoff **passed** on the live Debian appliance.

After native-init switches into the userdata Debian root, the firstboot profile now disables the
proof-only autoreboot path, starts the loopback smoke service, recovers DRM ownership from any
non-PID1 native `/init` HUD child, and starts a Debian-side KMS HUD.  The display proof is a live
`DRM_IOCTL_MODE_SETCRTC` present from Debian userspace:

```text
a90-dpublic-hud display=1080x2400 connector=28 crtc=133 refresh=2s
```

## Live State

The device was left in Debian userspace:

```text
pid1_comm=init
proc1_exe=/usr/sbin/init
debian_version=12.14
root=/dev/block/a90-userdata ext4 /
autoreboot_sec=disabled
dropbear_started=1
smoke_started=1
hud_started=1
tunnel_started=manual
```

Live helper identities:

```text
firstboot_sha256=a5e5c17a167f225f56528fe5ed0964e970813136ad299da4a5e8dc2f79db3411
hud_sha256=89ecabd1fcdbd548df23d23d0735c4c4eee1b6c47677e5570d56e8afe3ccfc29
smoke_httpd_sha256=8492bf77de7293b1a42ac9b321262974045992cbc5149c8937b0a24f83fd8e56
http_get_sha256=e19705456003f4e2a29590c077c078d960a062ab9cb514c6004f415c649f3ab2
```

Live processes:

```text
a90-dpublic-hud /usr/local/bin/a90-dpublic-hud 2
a90-dpublic-smoke-httpd 127.0.0.1 8080
cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8080 ...
```

The local smoke probe returned:

```text
A90_DPUBLIC_SMOKE_OK
service=loopback-http
public_exposure=outbound-tunnel-only
```

The public Cloudflare quick Tunnel path was rechecked five times after the HUD/firstboot corrections;
each request returned `A90_DPUBLIC_SMOKE_OK`.  The actual quick Tunnel URL is intentionally not
committed.

## Corrections

- Added `workspace/public/src/scripts/server-distro/a90_dpublic_hud.c`, a static Debian-side DRM/KMS
  HUD helper that materializes `/dev/dri/card0` from `/sys/class/drm/card0/dev`, creates a dumb
  framebuffer, and renders the server status screen.
- Added `workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh`, the D-public firstboot
  profile.  It keeps autoreboot disabled, brings up loopback and USB/NCM admin networking, starts
  dropbear, starts the loopback smoke service, starts the Debian KMS HUD, and only auto-starts
  `cloudflared` when `/etc/a90-dpublic/cloudflared-quick-enable` exists.
- Fixed the live DRM takeover failure.  A non-PID1 native `/init` child was holding `/dev/dri/card0`
  after switch_root.  The firstboot profile now kills only non-PID1 `/init` processes that hold DRM
  fds before starting the Debian HUD.
- Fixed D-public smoke robustness.  The smoke server now ignores `SIGPIPE`; the firstboot profile also
  clears stale D-public smoke/HUD processes by command line and waits for port/DRM release before
  restart.
- Removed status ambiguity in the marker by prefixing inherited D3 proof-stage values as
  `base_stage` and `base_autoreboot_sec`.

## Validation

Host/static:

```text
aarch64-linux-gnu-gcc -O2 -Wall -Wextra -static ... a90_dpublic_hud.c a90_draw.c
aarch64-linux-gnu-gcc -O2 -Wall -Wextra -static ... a90_dpublic_smoke_httpd.c
aarch64-linux-gnu-gcc -O2 -Wall -Wextra -static ... a90_dpublic_http_get.c
sh -n workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_dpublic_smoke_helpers tests.test_prepare_dpublic_preflight
git diff --check
```

Result:

```text
Ran 10 tests in 0.006s
OK
```

Live:

```text
HUD KMS present: display=1080x2400 connector=28 crtc=133 refresh=2s
local loopback smoke: 3/3 A90_DPUBLIC_SMOKE_OK
public quick Tunnel smoke: 5/5 A90_DPUBLIC_SMOKE_OK
```

## Safety Boundary

- No boot image was flashed in this unit.
- No forbidden partition was touched.
- Public exposure remained limited to the loopback smoke service through an outbound quick Tunnel.
- No public URL, credential, raw device identifier, or private artifact was committed.
- The live D-public tunnel and Debian HUD were left running for operator inspection.

## Follow-Up

The robust long-term native-side cleanup is to stop the native auto-HUD service before the
server-distro switch_root handoff.  This unit kept the current live appliance stable by doing the
DRM-owner recovery inside Debian firstboot, without rebuilding or flashing native-init.
