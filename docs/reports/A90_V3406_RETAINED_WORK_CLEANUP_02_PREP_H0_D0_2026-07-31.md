# A90 V3406 retained-work cleanup 02 preparation

Date: 2026-07-31
Decision: `A90_V3406_RETAINED_WORK_CLEANUP_02_PREP_H0_D0_PASS`

Independent verdict: GO
Unresolved HIGH: 0
Unresolved MEDIUM: 0
Unresolved LOW: 0
Device actions by reviewer: none

## Result

Fresh run `a90-v3406-debian-display-f1-20260731-03` has a new-inode keyed
Debian image from the reviewed ab-07 clean source. Its host-only materialization
passed read-only e2fsck and all six runtime-absence checks. It remains private
and has not been staged or used by a candidate.

The first connected-preflight attempt stopped before sending a device command.
The bridge status helper compared the literal host name `localhost` with the
numeric `127.0.0.1` address parsed from `/proc/net/tcp`, so it incorrectly
reported that the existing listener was absent. The common bridge helper now
treats the IPv4 loopback spelling as the same local listener. A regression test
covers that exact input, and the real host preflight now resolves the listener
through its socket fd.

The corrected bounded D0 then proved one exact A90, V2321 version/build,
selftest `fail=0`, and pstore `entries=0`. The V3406 final and stage paths were
absent, but the fixed work path was present. No command was sent to the
separately connected S22+.

## Runtime evidence preservation

The retained work image is a regular 2 GiB file with mode `0600`, link count
one, and SHA256:

```text
d1353db59571c3ca4b8be14fed0d19e4a46217ded285e7ceb62ac85b1c6f94c0
```

It was neither mounted nor used as loop backing. One exact A90 `cdc_ncm`
interface was selected from USB vendor/product and driver attributes. A
run-specific host profile was bound to that current interface, and the peer
was checked against the already prepared private V3406 manifest.

A device-to-host read-only stream received exactly `2147483648` bytes into a
new private mode-`0600`, single-link file. The streaming host SHA256 equals the
device SHA256. A post-transfer device read proved the retained file still had
the same type, size, mode, link count, and SHA256. The extraction did not write
the device, stage a rootfs, flash, or reboot.

## Cleanup closure

The one-shot retained-work cleanup helper now selects only the new hash above.
The previously consumed `0beb73d3...` work identity cannot satisfy the current
source or manifest contract. The fresh private cleanup manifest binds:

- run `a90-v3406-debian-display-f1-20260731-03` and its connected D0 result;
- one exact A90 bridge identity and exact healthy V2321 baseline;
- the fixed work path, new size/mode/hash, and exact host preservation;
- the run-derived V3406 source and stage paths, both required absent;
- the current cleanup helper identity;
- the exact `a90ctl.py` transport source whose non-retry dispatch is required;
  and
- a single non-recursive unlink with no unsafe retry.

Independent review found that the first provisional manifest did not bind the
`a90ctl.py` source even though cleanup safety relies on its
`retry_unsafe=False` dispatch. That manifest never received an approval receipt
or live directory and is superseded. The helper, approval binding, intent, and
host inspector now bind the exact transport source. A mutation test rejects
transport hash drift.

Host-only inspection accepted the corrected manifest SHA256:

```text
995413a8c0a0fcfa41753c0d7e0e6520fd91d197de39affdc3451daa27cd5a5d
```

No cleanup approval receipt has been prepared and no unlink has been
dispatched. The persistent cleanup remains a separate approval-bound action.

## Validation

- bridge focused tests: `15/15` PASS;
- cleanup focused tests: `18/18` PASS;
- integrated Phase2 and cleanup tests: `237/237` PASS;
- Python `py_compile`: PASS;
- `git diff --check`: PASS;
- cleanup manifest host-only inspection: PASS;
- device actions: bounded A90 D0 reads only;
- S22+ commands: zero.

Current source identities are:

```text
a90_bridge.py                               922c55a0afdef9d237a679203f576226583f4463eec15fb0091871c241f8be01
test_a90_bridge.py                          26b48825444542b73af154f0df12312a1536d2ffb7562c217f4310d6da430e73
a90_v3405_retained_work_cleanup.py          922cf8c4c535d5149f66c5fef67632ba9a83e21fe5f0b71dc1238b2f4404c8f4
test_server_distro_a90_v3405_retained_work_cleanup.py
                                                7dbc4880013070426465d03c2b38afa14af758cbd4ac430ce1d32701879a4d64
a90ctl.py                                    11c567c5ec4d7b95dfbe0409af1759a90087eb937e47ce627b21511316d5766d
```

## Next gate

Independent review closed the bridge status correction, new cleanup hash, and
transport-source binding with GO and no unresolved High, Medium, or Low
finding. The next host-only step is one exclusive cleanup approval receipt.
Only its fresh exact token may authorize the single unlink. After a cleanup
PASS, repeat connected D0 with a new evidence sequence before preparing the F1
manifest.
