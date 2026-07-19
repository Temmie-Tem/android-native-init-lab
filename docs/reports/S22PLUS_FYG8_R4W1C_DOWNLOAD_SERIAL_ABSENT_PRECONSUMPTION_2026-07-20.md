# S22+ FYG8 R4W1-C Download Serial-Absent Pre-Consumption Result

Date: 2026-07-20 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Verdict: `FAIL_R4W1C_PRECONSUMPTION_NO_CANDIDATE_FLASH`

Disposition: `RETIRE_SERIAL_BOUND_LIVE_POLICY_AND_REDESIGN_HOST_ONLY`

## Safety Outcome

The run stopped before the one-shot state and before any Odin transfer:

```text
candidate_transfer_attempted  false
candidate_transfer_ok         false
candidate consumed            false
Odin transfer                 0
partition write               0
candidate flash               0
rollback required             no
```

Run evidence:

```text
run
  workspace/private/runs/s22plus-r4w1c-live-20260719T210900Z

result-live.json
  size    14505
  SHA256  86033bb3a25431ae0f339fcf720d8ab794ea9776b2c72d415d05c7a8217ded25

timeline-live.json
  size    223
  SHA256  ca3110e5620e4b2086345fb23f6a3660499971288aff8a5cd222e8d686ec885e

connected_preflight.json
  size    7661
  SHA256  4c918262db0e5f721626b43b7dd418cc4b959e5eab187860ec6d939a46534834
```

The timeline contains only actual `live_session_start` and `live_session_end`.
No candidate or rollback milestone was synthesized.

## Live Observation

The exact Android baseline passed, including clean retained observers and
absence of Odin. `adb reboot download` returned success. The bounded endpoint
wait then expired with:

`bound Download endpoint did not stabilize in time`

While the phone remained visibly in normal Samsung Download, a host sysfs and
direct-node read showed:

```text
sysfs topology  2-1.3
idVendor        04e8
idProduct       685d
product         SAMSUNG USB
manufacturer    Samsung
devpath         1.3
device node     /dev/bus/usb/002/017
node type       character special file
serial          absent
```

The topology exactly matched the Android ADB `get-devpath` binding. The missing
property was specifically the Download-mode sysfs `serial` file.

## Root Cause

`bound_download_node_sample()` reads `serial` together with vendor, product,
bus, and device number. A missing `serial` raises `FileNotFoundError`, which the
sampler interprets as endpoint absence. It therefore returns `None` until the
shared 120-second deadline expires, even though the correct `04e8:685d`
character node is present and stable.

The correction that closed the earlier enumeration-arrival race was sound for
node stabilization, but it added an unsupported identity assumption: Android
ADB mode exposes serial `RFCT519XWGK`; normal Samsung Download mode on this FYG8
target does not expose any serial descriptor through sysfs. Requiring the same
serial digest across those USB personalities makes the gate unsatisfiable.

## Exact Android Return

After physical Download exit, read-only checks proved:

```text
model/incremental     SM-S906N / S906NKSS7FYG8
boot complete         1
boot animation        stopped
verified boot         orange
Magisk root           uid=0(root)
boot SHA256           2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
vendor_boot SHA256    096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
DTBO SHA256           97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
recovery SHA256       93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4
Android USB           2-1.3 04e8:6860 RFCT519XWGK
Odin endpoint         absent
```

Policy-only commit `47fbbc35` changes the R4W1-C live state from ACTIVE to
RETIRED and records the incident. The exact helper, clause, and acknowledgement
must not be reused.

## Replacement Requirements

The replacement remains host-only until fully qualified:

1. Bind exact Android serial and physical topology before reboot.
2. Require Android endpoint disappearance and a new Download arrival at only
   that topology.
3. Require Samsung `04e8:685d`, exact product/manufacturer constraints, one
   exclusive direct character node, and three stable complete node samples.
4. Treat Download serial as tri-state: absence is required for this measured
   target; if unexpectedly present, fail closed rather than silently ignoring
   it.
5. Preserve exact `st_dev`, inode, `st_rdev`, and ctime continuity into the
   hardened Odin ticket and bracket every final sysfs read with pre/post node
   snapshots.
6. Preserve the sealed Odin launch, one-shot consumption, mandatory rollback,
   partition prohibitions, full regression suite, independent review, new
   deterministic binding packet, separate ACTIVE commit, and fresh token.

No second live attempt is permitted under the retired serial-bound policy.
