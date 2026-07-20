# S22+ FYG8 R4W1-C Odin Enumeration-Diff Observer Live PASS

Date: 2026-07-20 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Verdict: `PASS_R4W1C_ENUM_DIFF_OBSERVER_EVIDENCE_CAPTURED`

Scope: one attended zero-transfer observation consisting of one exact Android
baseline, one `adb reboot download`, three stable Download samples, one bounded
exact `odin4 -l`, physical Download exit, and exact Android return. No Odin
transfer, flash, partition write, candidate execution, cleanup, acceptance
decision, or second observer occurred.

## Run Identity

```text
run directory
  workspace/private/runs/s22plus-r4w1c-enum-diff-20260720T145239Z

result.json
  size    10996
  SHA256  c64e0873c722df56c4a4596c73d92367e6f9608dc6ab1cd1d076044a3e3f6ab0

timeline.json
  size    846
  SHA256  27111a3d4d4f7af3b2ba7351f3ee016796f0f4daa30c70e8c2d445a215627013

enumeration-diff.json
  size    1860
  SHA256  98f8b050b0c8d665719d1feaf92b02d232d4e7b4692c57e5e851c452b61525ae

consumed state
  SHA256  5e5be04786b7437bfb79c390132c0222f003df89e3973ff5ac3808f5a80f1c85
```

The one-shot state was durably consumed at `2026-07-20T14:52:41.220734Z`,
before the Download request. The canonical timeline contains all eight ordered
`events:[{name,timestamp_utc}]` entries from
`2026-07-20T14:52:39.086924Z` through `2026-07-20T14:55:58.307556Z`.
Candidate and rollback names retain their explicit zero-flash semantics.

## Exact Odin Observation

```text
argv                   /usr/bin/odin4 -l
return code            0
timeout                false
output truncated       false
cleanup error          null
command error          null
stdout size            21
stdout SHA256           434159d459482113e44209b712c897fa5b301f12294fbb318386170b972dcda1
reported path           /dev/bus/usb/002/021
stderr size            0
stderr SHA256           e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
persist errors          none
transfer authorized    false
```

The exact `/usr/bin/odin4` inode, size `3746744`, and SHA256
`6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b`
were unchanged before and after execution.

## Endpoint Evidence

Three stabilization samples were byte-consistent for the load-bearing endpoint
identity:

```text
topology               2-1.3
vendor:product         04e8:685d
product text           SAMSUNG USB
manufacturer           Samsung
Download serial        absent
usbfs path             /dev/bus/usb/002/021
inode                   2027
st_dev                  7
st_rdev                 48532
device major:minor      189:148
mode                    432 decimal (0660)
uid:gid                 0:46
link count              1
birth_time_ns           1784559171849157342
```

The complete pre-listing bundle matched the final stable sample without any
immutable or metadata difference. Immediately after the single listing, only
these three fields changed:

```text
field         before                 after
st_atime_ns   1784559171875157328    1784559230492125393
st_ctime_ns   1784559171875157328    1784559230492125393
st_mtime_ns   1784559171875157328    1784559230492125393
delta                                 58.616968192 seconds
```

The result classification is `OBSERVED_METADATA_ONLY_MUTATION`. The following
sets are all empty:

- immutable changes;
- inventory additions;
- inventory removals;
- stabilization-to-before differences; and
- unsafe reasons.

The inode, filesystem/device identities, major/minor, mode, owner/group, link
count, birth time, sysfs descriptors, device number, path, topology, and every
inventory member remained unchanged. The prior pre-consumption failure was
therefore a conservative false rejection of listing-time timestamp mutation,
not evidence of USB endpoint replacement.

## Exact Android Return

The final Android sample matched the pre-run Android state and proved:

```text
model / device / build  SM-S906N / g0q / S906NKSS7FYG8
boot complete           1
boot animation          stopped
verified boot           orange
Magisk root             uid=0(root)
known boot SHA256        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
stock vendor_boot       096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
stock DTBO              97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
stock recovery          93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4
Android serial          RFCT519XWGK
USB topology            2-1.3
```

## Decision

The observer fulfilled its evidence-only purpose and is permanently consumed.
Its ACTIVE policy and all acknowledgement tokens are RETIRED and must not be
reused. The result does not authorize a candidate or make an acceptance
decision.

Post-retirement host-only closure returned:

```text
observer policy active   false
observer consumed        true
BEGIN/END markers        1/1
ACTIVE/RETIRED markers   0/1
related regression       185/185 passed
device contact           false
Odin enumeration         false
Odin transfer            false
flash                    false
```

The next bounded unit is host-only design of a new transfer gate. It may treat
only the three measured timestamp fields as mutable across the exact Odin
listing. It must continue to reject every immutable field change, inventory or
topology mutation, endpoint ambiguity, descriptor mismatch, process error,
unexpected output, and rollback uncertainty. Source, tests, binding, policy
activation, independent review, and a fresh acknowledgement remain separate
mandatory gates before any later device action.
