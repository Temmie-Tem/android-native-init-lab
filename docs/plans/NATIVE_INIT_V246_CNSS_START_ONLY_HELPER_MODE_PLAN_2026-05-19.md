# Native Init v246 CNSS Start-Only Helper Mode Plan

## Summary

- target: v246 helper-side `cnss-start-only` mode implementation plan
- baseline: v245 safe runner `preflight-ready`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- host wrapper: `scripts/revalidation/wifi_cnss_start_only_runner.py`
- live daemon start in this planning step: not executed

v246 is the implementation plan for the helper mode that v245 dry-run already
models. It should add a bounded start/observe/stop path to the helper, but the
host wrapper must keep live execution fail-closed until explicit operator
approval is given.

## Why v246 Is Needed

v245 can prove prerequisites, read-only preflight, and exact dry-run argv, but
there is no helper mode that can safely perform the actual start-only envelope.
The old v229 `runandroid` path is obsolete because it does not provide the v244
private namespace, bind-backed `/apex` farm, uid/gid/groups, or `CAP_NET_ADMIN`
contract.

## Helper Contract

Add a new mode:

```text
--mode cnss-start-only
```

Required extra guard flag for helper execution:

```text
--allow-cnss-start-only
```

The helper must reject `cnss-start-only` unless that flag is present. This keeps
accidental invocation safe even if the host wrapper has a bug.

The mode must use v244 setup:

- private mount namespace
- private `/dev/null`
- real linkerconfig copy
- private bind-backed `/apex` farm plus `com.android.vndk.v30` alias
- private read-only vendor mount
- uid/gid `system=1000`
- supplemental groups `inet=3003`, `net_admin=3005`, `wifi=1010`
- ambient/effective/permitted `CAP_NET_ADMIN`
- `chroot` into private root before exec

Daemon argv is fixed:

```text
/vendor/bin/cnss-daemon -n -l
```

No free-form target path or arguments are allowed for this mode.

## Runtime Envelope

Inside the helper:

1. prepare namespace and print the same context inventory as v244
2. fork a supervisor child/session for `cnss-daemon`
3. apply identity/capability contract in the child
4. exec `/vendor/bin/cnss-daemon -n -l`
5. parent observes for `--timeout-sec` seconds or child exit
6. capture child pid, exit/signal, timeout state, and selected `/proc/<pid>` data
7. terminate process group with SIGTERM, then SIGKILL if needed
8. reap all tracked children
9. print machine-readable key/value summary
10. cleanup private mounts and temp paths

## Output Contract

Use stable key/value output so the host wrapper can parse without scraping prose:

```text
cnss_start.begin=1
cnss_start.allowed=1
cnss_start.pid=<pid>
cnss_start.exec_attempted=1
cnss_start.observable=0|1
cnss_start.exited=0|1
cnss_start.exit_code=<n>
cnss_start.signal=<n>
cnss_start.timed_out=0|1
cnss_start.term_sent=0|1
cnss_start.kill_sent=0|1
cnss_start.reaped=0|1
cnss_start.postflight_safe=0|1
cnss_start.result=start-only-pass|start-only-runtime-gap|start-only-reboot-required|start-only-blocked
```

If exec fails immediately because Android runtime primitives are missing, the
helper should still return a parseable `start-only-runtime-gap` result after
cleanup, not crash or hang.

## Host Wrapper Changes

Update `scripts/revalidation/wifi_cnss_start_only_runner.py`:

- keep `plan`, `preflight`, and `dry-run` unchanged
- update dry-run argv to include `--allow-cnss-start-only` only in explicitly
  approved `run` mode
- live `run` requires:
  - `--allow-daemon-start`
  - `--assume-yes`
  - `--i-understand-reboot-only-recovery`
- parse helper `cnss_start.*` keys
- classify results as:
  - `start-only-pass`
  - `start-only-runtime-gap`
  - `start-only-reboot-required`
  - `start-only-blocked`
  - `manual-review-required`

## Guardrails

Still denied:

- `cnss_diag`
- Wi-Fi scan/connect/link-up/credential/DHCP/routing
- `rfkill unblock`
- `ip link set wlan* up`
- `iw scan/connect`
- supplicant/HAL/wificond/hostapd
- ICNSS generic bind/unbind
- firmware path mutation
- persistent Android partition writes
- automatic reboot

## Validation Plan

Static:

```bash
scripts/revalidation/build_android_execns_probe_helper.sh
python3 -m py_compile scripts/revalidation/wifi_cnss_start_only_runner.py
git diff --check
strings stage3/linux_init/helpers/a90_android_execns_probe | rg 'cnss-start-only|allow-cnss-start-only'
```

Safe live validation, no daemon start:

```bash
python3 scripts/revalidation/wifi_cnss_start_only_runner.py plan \
  --out-dir tmp/wifi/v246-cnss-start-only-helper-plan
python3 scripts/revalidation/wifi_cnss_start_only_runner.py preflight \
  --out-dir tmp/wifi/v246-cnss-start-only-helper-preflight
python3 scripts/revalidation/wifi_cnss_start_only_runner.py dry-run \
  --out-dir tmp/wifi/v246-cnss-start-only-helper-dryrun
python3 scripts/revalidation/wifi_cnss_start_only_runner.py run \
  --out-dir tmp/wifi/v246-cnss-start-only-helper-run-blocked
```

Expected safe validation:

- plan/preflight/dry-run PASS
- run without dangerous flags returns `start-only-blocked`
- `daemon_start_executed=false`

Live daemon validation is not automatic. It requires separate operator approval
after reviewing v246 dry-run evidence.

## Acceptance For v246 Implementation

- helper supports `--mode cnss-start-only` but rejects it without
  `--allow-cnss-start-only`
- host runner remains fail-closed by default
- safe validation proves no daemon execution occurred
- report documents helper SHA-256 and all safe-mode decisions
- live daemon start remains blocked until explicit approval
