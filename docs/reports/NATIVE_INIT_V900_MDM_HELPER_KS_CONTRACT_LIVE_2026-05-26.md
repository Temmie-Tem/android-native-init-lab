# V900 mdm_helper/ks Contract Live Report

## Result

| Unit | Evidence | Decision |
| --- | --- | --- |
| first run | `tmp/wifi/v900-mdm-helper-ks-contract-live/manifest.json` | `v900-step-failed` before repair |
| allowlist repair | `docs/reports/NATIVE_INIT_V901_HELPER_V145_ALLOWLIST_DEPLOY_2026-05-26.md` | `execns-helper-v145-deploy-pass` |
| repaired live run | `tmp/wifi/v900-mdm-helper-ks-contract-live/manifest.json` | `v900-reboot-required-cleaned` |

V900 completed the bounded live `mdm_helper`/`ks` contract proof after V901
repaired and deployed helper `v145`.

## Findings

- Remote helper `v145` sha/marker/mode matched the expected artifact.
- `/vendor/bin/mdm_helper` started and became observable.
- `/dev/subsys_esoc0` open was attempted only after the
  `mdm_helper_observable` gate opened.
- The trigger child entered the `/dev/subsys_esoc0` open path and did not exit
  before timeout.
- The parent sent TERM and KILL, but the trigger child was not reaped, so the
  helper correctly classified the run as `reboot-required`.
- `/vendor/bin/ks` was not observed:
  `ks_count.before=0`, `ks_count.window=0`, `ks_count.after=0`.
- MHI pipe command line was not observed:
  `mhi_pipe_cmdline_count.window=0`.
- MHI device path stayed absent:
  `/dev/mhi_0305_01.01.00_pipe_10` did not exist before, during, or after the
  window.
- Post-window state still showed `mdm3` as `OFFLINING` and GPIO 142 `mdm
  status` IRQ count `0`.
- Cleanup reboot restored native health; direct post-cleanup checks showed
  `selftest fail=0` and `bootstatus` OK.

## Interpretation

The V896 Android ordering was partially reproduced: `mdm_helper` can be started
before the subsystem open, and the helper enforces that order. However, native
still does not reach the Android positive-control behavior. Opening
`/dev/subsys_esoc0` remains a blocking lower-kernel transition, no `ks` process
appears, no MHI pipe appears, GPIO 142 does not fire, and `mdm3` remains
`OFFLINING`.

This closes simple "start `mdm_helper` before `/dev/subsys_esoc0`" as a
sufficient trigger. The next gate should capture the exact blocked wait
location of the subsystem-open child or classify the missing `mdm_helper` input
that Android provides before that open completes.

## Guardrails

- No controller-side `REG_REQ_ENG`, `REG_CMD_ENG`, `CMD_EXE`, explicit
  `PWR_ON`, `WAIT_FOR_REQ`, `ESOC_NOTIFY`, or `BOOT_DONE`.
- No service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, boot image write, partition write, firmware
  mutation, GPIO/sysfs/debugfs write, module load/unload, or Wi-Fi link-up.
- A cleanup reboot was intentionally executed because the trigger child was not
  proven stopped.

## Next

V902 should not repeat the same live open blindly. The useful next unit is a
reduced blocker-capture gate:

1. keep the `mdm_helper` before `/dev/subsys_esoc0` ordering;
2. capture `/proc/<trigger_pid>/wchan`, process state, and available stack
   evidence while the trigger child is blocked;
3. keep `ks`, MHI, GPIO 142, and `mdm3` observations read-only;
4. reboot-clean if the child again cannot be reaped.
