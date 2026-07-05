# WSTA147 D-public HUD Presenter Restart Policy Live Pass

Date: 2026-07-05 10:38 KST

## Verdict

WSTA147 live-gated the V3402 D-public HUD presenter restart policy.  Result:
PASS.  Restart releases the old native presenter, starts a fresh presenter,
fresh intents are consumed after restart, stale pidfile cleanup works, and final
native health remains clean.

The device is intentionally left on the live-passed V3402 resident image.  No
rollback was needed.

## Flash Gate

Preconditions were checked before flash:

- Current device health before flash: resident V3401, `selftest fail=0`.
- v2321 rollback SHA matched.
- v2237 fallback SHA matched.
- v48 fallback image existed.
- TWRP recovery artifact existed.

Checked flash:

- Candidate: `A90 Linux init 0.11.158 (v3402-dpublic-hud-presenter-restart-policy)`
- Boot SHA256:
  `57821e94857cb58b397c737a73d5f85381329f5e9ec8a6b55dc7d5dbb6a7d3f1`
- Helper: `native_init_flash.py --from-native`
- Local Android boot magic: ok.
- Remote pushed image SHA256 matched.
- Boot partition prefix readback SHA256 matched.
- Post-boot cmdv1 `version/status` verification passed.
- Flash helper total time: `65.358s`.

## Restart Proof

Private run directory:

`workspace/private/runs/server-distro/wsta147-v3402-hud-restart-policy-live-20260705T1035KST/`

Service start:

- `A90WSTA146 restart_policy=restart-stop-start-stale-pid-cleanup`
- `A90WSTA144 shared_run_dir=mounted path=/run/a90-dpublic fstype=tmpfs mode=1770 owner=root:a90hud`
- `A90WSTA140 start.pid=661`
- `A90WSTA140 start.done=1`

Pre-restart intent:

- Fresh intent `sequence=14701` was written.
- Presenter printed
  `dpublic-hud-presenter-service: presented framebuffer 1080x2400 on crtc=133`.
- Status after intent:
  - `status.pid=661`
  - `status.drm_fd=1`
  - `status.debian_direct_kms=0`
  - `status.restart_policy=restart-stop-start-stale-pid-cleanup`
- Status file:
  - `last_sequence=14701`
  - `present_rc=0`
  - `process_model=forked-native-child-survives-switch-root`

Restart:

- Command: `dpublic-hud-presenter-service restart ... --release-drm`
- Stop phase:
  - `stop.pid=661 release_drm=1`
  - `handoff_display drm_owner_pid=661 action=term`
  - `stop.done=1`
  - `restart.stop_rc=0`
- Start phase:
  - `start.pid=669`
  - `start.done=1`
  - `restart.start_rc=0`
  - `restart.done=1 rc=0`

Post-restart intent:

- Fresh intent `sequence=14702` was written.
- Presenter printed
  `dpublic-hud-presenter-service: presented framebuffer 1080x2400 on crtc=133`.
- Status after intent:
  - `status.pid=669`
  - `status.drm_fd=1`
  - `status.debian_direct_kms=0`
- Status file:
  - `last_sequence=14702`
  - `present_rc=0`

Stop after restart:

- `stop.pid=669 release_drm=1`
- `handoff_display drm_owner_pid=669 action=term`
- `stop.done=1`

## Stale Pid Cleanup

A fake dead pidfile was safely synthesized with value `999999`.  The next start
proved the cleanup path:

- `A90WSTA146 start.stale_pid=999999 action=unlink`
- `A90WSTA140 start.pid=680`
- `A90WSTA140 start.done=1`

Final stop returned `stop.done=1`, and follow-up status returned
`status.state=stopped rc=-2`.

## Final Health

- Resident: `A90 Linux init 0.11.158 (v3402-dpublic-hud-presenter-restart-policy)`
- `selftest: pass=12 warn=1 fail=0`
- `boot: BOOT OK`
- `transport.serial=ready`
- `transport.ncm=ready`
- `transport.tcpctl=ready`
- `storage: sd present=yes mounted=yes expected=yes rw=yes`

## Safety

Only the boot partition was flashed, via the checked helper.  No forbidden
partition, PMIC/regulator/GDSC/GPIO/backlight, panel reinitialization, Wi-Fi
association, DHCP, public tunnel, packet-filter mutation, userdata population,
or Debian handoff action ran in WSTA147.

## Next

Fold the WSTA147 restart/stale-cleanup live proof into WSTA108 operator status,
then proceed to optional HUD syscall trace profiling or broader containment
hardening.
