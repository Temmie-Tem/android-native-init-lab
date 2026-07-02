# Native Init V3353 §0.2 Write-Probe E3b 1MiB Live

- Cycle: `V3353`
- Decision: `v3353-boot-write-e3b-1mib-live-pass`
- Candidate: `A90 Linux init 0.11.117 (v3353-boot-write-e3b-1mib)`
- Candidate boot SHA256: `a4cc3c93a37ba350ed7b0fd94503e82fae8f8169dc3ddaa76a9256bac5257091`
- Private run log: `workspace/private/runs/self-dd-v3353-e3b-live-20260702T002910Z/`
- Final state: rolled back to `v2321-usb-clean-identity-rodata`, final `selftest fail=0`.

## Gate

- Rollback images were present and SHA-confirmed before flash: v2321, v2237, and v48.
- Pre-flash resident was v2321 with `selftest fail=0`.
- Candidate flash used the checked helper `native_init_flash.py` with expected SHA and version guard.
- Candidate helper readback matched the V3353 boot SHA, then native boot verified `version/status`.
- Candidate selftest passed on a fresh command: `selftest: pass=12 warn=1 fail=0`.

The first candidate selftest host attempt using `--hide-on-busy` produced no command output and was
terminated host-side. A fresh `version` and `selftest` immediately passed; no device-side command
failure was observed.

## E3b Probe Result

Command:

```text
boot-write-e3b BOOT-WRITE-PROBE-E3B-1MIB-SLACK
```

Observed E3b output:

```text
A90BWE3B boot_header=ok version=1 page_size=4096 used_len=62644224
A90BWE3B slack_start=62644224 slack_end=66060288 footer_guard=1048576
A90BWE3B target_off=62644224 len=1048576 nonzero_bytes=833364 nonzero_sectors=252 zero_sectors=4
A90BWE3B full_sha_before=150466f09cfcb3dbf25cac139a50241397ddef09d79d9218763d209a1885a024
A90BWE3B pwrite_rc=1048576
A90BWE3B pwrite_count=1 pwrite=ok fsync=ok
A90BWE3B readback_rc=1048576 region_match=1
A90BWE3B region_match_all=1
A90BWE3B full_sha_after=150466f09cfcb3dbf25cac139a50241397ddef09d79d9218763d209a1885a024
A90BWE3B full_match=1
A90BWE3B result=ok pwrite-permitted-identity-verified
A90BWE3B end rc=0
```

This proves normal-boot PID1 can perform one 1MiB identity `pwrite` to parsed boot tail slack with a
non-zero source buffer. The region readback matched and the full 64MiB boot-partition SHA stayed
unchanged.

## Health And Rollback

- Post-probe status: `selftest fail=0`, pstore entries `0`.
- Post-probe selftest: `pass=12 warn=1 fail=0`.
- Rollback flash used v2321 SHA
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`; readback SHA matched.
- Final v2321 selftest: `pass=11 warn=1 fail=0`.
- Final pstore summary after `hide`: `entries=0`.

## Timeline

Private `timeline.json` uses the canonical single top-level `events` schema and contains the required
phase events:

```text
candidate_flash_start
candidate_flash_done
candidate_boot_ready
live_session_start
live_session_end
rollback_flash_start
rollback_flash_done
rollback_boot_ready
```

## Conclusion

V3353 E3b passed. The self-dd mechanism has now progressed from first 4KiB write, to four sparse
sectors, to sixteen sparse sectors, to one contiguous 1MiB non-zero identity write, all with
full-partition SHA preservation and clean v2321 rollback.
