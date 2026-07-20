# S22+ FYG8 R4W1-C No-Serial Pre-Consumption Enumeration Mutation

Date: 2026-07-20 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Verdict: `FAIL_R4W1C_PRECONSUMPTION_NO_CANDIDATE_FLASH`

Disposition: `RETIRE_NOSERIAL_LIVE_POLICY_AND_BUILD_ZERO_TRANSFER_ENUM_DIFF_OBSERVER`

## Safety Outcome

The freshly acknowledged run stopped before the one-shot state and before any
Odin transfer:

```text
candidate_transfer_attempted  false
candidate_transfer_ok         false
candidate consumed            false
Odin transfer                 0
partition write               0
candidate flash               0
rollback required             no
```

Evidence:

```text
run
  workspace/private/runs/s22plus-r4w1c-live-20260720T071009Z

result-live.json
  size    14765
  SHA256  73afc646b345e3e758bc151883509e4ee510fac8cf9bbe6dadece7a50c084da6

timeline-live.json
  size    223
  SHA256  28dc8113812f6a4dcbac9948f90b146df747806312081b5548619f42131d1383

connected_preflight.json
  size    7661
  SHA256  17e7ecd81f1828fc40c4d09c714f25dd3a3f3b5a9c4284fe8e64db5f3afa5f7f

transaction.jsonl
  size    1273
  SHA256  8b30c52763b97cf68c870f97d99d6ea3d3943a33cdbb0fb6ca68f3e63deb2141
```

The public timeline contains only actual `live_session_start` and
`live_session_end`. The durable consumed-state path remains absent.

## Live Observation

The exact Android baseline passed, including clean retained observers, absent
pstore consoles, and clean-empty Odin evidence. `adb reboot download` returned
success. The bound Download personality was:

```text
topology       2-1.3
USB ID         04e8:685d
product        SAMSUNG USB
manufacturer   Samsung
serial         absent
usbfs node     /dev/bus/usb/002/019
```

The helper reached the post-stabilization Odin ticket wait and failed with:

`Odin endpoint changed during enumeration: /dev/bus/usb/002/019`

## Host Timeline

Read-only host kernel and filesystem evidence after failure showed:

```text
16:10:17 KST  Android USB device 18 disconnected at topology 2-1.3
16:10:24 KST  one SuperSpeed device 19 arrived at topology 2-1.3
16:10:24 KST  exact 04e8:685d descriptors, SerialNumber=0
16:10:24.751  usbfs node birth
16:10:24.777  udev database record completed
16:10:25.488  final node atime/mtime/ctime
16:10:25.501  failure result sealed
```

No second USB disconnect or replacement was logged between device-19 arrival
and failure. The surviving node was character device major/minor `189:146`,
inode `1989`, owner/group `root:plugdev`, mode `0660`, with a `temmie:rw-` ACL.

## Proven And Unproven

Proven:

- the three-sample Download node stabilization completed, because execution
  reached `wait_for_single_live_endpoint()`;
- `odin4 -l` reported `/dev/bus/usb/002/019` and the post-call node existed;
- the shared core rejected either a missing pre-call identity or any difference
  in its combined `st_dev:inode:st_rdev:ctime` identity;
- there was no kernel-observed USB replacement after device 19 arrived;
- no candidate action occurred.

Not proven:

- which exact identity field changed;
- whether the pre-call inventory omitted the path or held a different ctime;
- whether the transition was udev/logind ACL settling or an effect of Odin
  opening the usbfs node.

The current helper did not persist the stabilized tuple or the failed
enumeration's pre/post inventories. Therefore the metadata-settling explanation
is strong but not load-bearing enough to relax a safety gate.

## Required Replacement

The next unit is observation-only and must contain no AP path or transfer mode:

1. Persist the complete stabilized sysfs identity and usbfs tuple before Odin.
2. Persist complete usbfs inventories immediately before and after one bounded
   `odin4 -l`, including `st_dev`, inode, `st_rdev`, ctime, mode, uid, gid, and
   birth time where available.
3. Persist an exact per-field diff and bracketing sysfs reads even when the
   enumeration result would otherwise raise.
4. Keep topology, device number, `st_dev`, inode, `st_rdev`, descriptors,
   endpoint ambiguity, disconnect, and replacement fatal.
5. Do not decide whether ctime-only settling is acceptable until the observer
   has live evidence and independent review.
6. Require host tests proving that no AP-bearing Odin invocation, transfer,
   candidate consumption, or partition write surface exists.

The current helper, ACTIVE rendering, and acknowledgement are retired. This
report authorizes no retry or new device contact.

## Exact Android Return

After physical Download exit, a read-only verification proved:

```text
serial/model/device    RFCT519XWGK / SM-S906N / g0q
incremental            S906NKSS7FYG8
boot complete          1
boot animation         stopped
verified boot          orange
Magisk root            uid=0(root)
boot SHA256             2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
vendor_boot SHA256      096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
DTBO SHA256             97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
recovery SHA256         93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4
Android USB topology    2-1.3
Odin endpoint count     0
```
