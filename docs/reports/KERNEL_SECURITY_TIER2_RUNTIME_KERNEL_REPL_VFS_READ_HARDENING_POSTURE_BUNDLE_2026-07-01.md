# Kernel Security Tier-2 Runtime Kernel REPL - VFS-read hardening-posture bundle

Date: 2026-07-01

- Decision: `a90-repl-vfs-read-hardening-posture-bundle-pass`
- Scope: named observation bundle built on the live-proven VFS-read primitive;
  boot partition only; rollback to `v2321`
- Bundle: `hardening-posture`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img`
- Candidate SHA256: `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback image: `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img`
- Rollback SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Private evidence: `workspace/private/runs/kernel/vfs-read-hardening-posture-bundle-20260701T102654Z/proof/hardening-posture/a90_repl_evidence.json`
- Private result: `workspace/private/runs/kernel/vfs-read-hardening-posture-bundle-20260701T102654Z/result.json`
- Private timeline: `workspace/private/runs/kernel/vfs-read-hardening-posture-bundle-20260701T102654Z/timeline.json`

## Selection

This is the first named bundle layered on the VFS-read keystone. It reads
kernel hardening posture through `/proc/sys/kernel` file nodes instead of
adding redundant state-getter call-proofs. Baseline path preflight showed these
six paths are readable:

- `/proc/sys/kernel/kptr_restrict`
- `/proc/sys/kernel/dmesg_restrict`
- `/proc/sys/kernel/perf_event_paranoid`
- `/proc/sys/kernel/modules_disabled`
- `/proc/sys/kernel/randomize_va_space`
- `/proc/sys/kernel/unprivileged_bpf_disabled`

`/proc/sys/kernel/kexec_load_disabled` and
`/proc/sys/kernel/yama/ptrace_scope` were absent on this image and are not part
of this bundle. `panic_on_oops` is deliberately excluded because the REPL proof
temporarily changes that sysctl as a runtime guard, so including it would
self-contaminate the observation.

Trusted input contract:

- Fixed named path list above.
- Read-only `filp_open(path, O_RDONLY, 0)`.
- Owned pathname/read/`loff_t` buffers.
- Bundle default `read_len=64`.
- Per-path `filp_close(file, NULL)` and `kfree` cleanup.

## Static Gate

The bundle reuses the VFS-read static gate before live use:

| Symbol | Resolution | Source contract | Safety |
| --- | --- | --- | --- |
| `filp_open` | `export-recovery`, map agrees | `extern struct file * filp_open(const char *, int, umode_t)` | `SAFE-WITH-VALID-PTR`, x0 pathname |
| `kernel_read` | `export-recovery`, map agrees | `extern ssize_t kernel_read(struct file *, void *, size_t, loff_t *)` | `SAFE-WITH-VALID-PTR`, x0/x1/x3 verified pointers |
| `filp_close` | `export-recovery`, map agrees | `extern int filp_close(struct file *, fl_owner_t id)` | cleanup-only `SAFE-WITH-VALID-PTR` |
| `__kmalloc` / `kfree` | `export-recovery`, map agrees | owned-buffer setup/cleanup | existing REPL allocator contract |

This is not a new arbitrary close/read permission. `filp_close` is used only
for the `struct file *` returned by the same path's `filp_open`, and all read
buffers are tool-owned.

## Live Run

Flash gate:

- Candidate, rollback, v2237 fallback, v48 fallback, and TWRP recovery
  artifacts were present before flash.
- Baseline v2321 `version/status/selftest` passed.
- Candidate flash used `native_init_flash.py`; pushed-image SHA and boot
  readback SHA matched the candidate SHA.
- Candidate health first attempt hit known serial input/END-marker
  fragmentation. Bridge restart + retry passed.
- REPL selftest returned `a90-repl-v2a1-selftest-pass`.

Bundle result:

| Path | Result | Observed bytes | Public classification |
| --- | --- | ---: | --- |
| `/proc/sys/kernel/kptr_restrict` | PASS | `2` | text decimal |
| `/proc/sys/kernel/dmesg_restrict` | PASS | `2` | text decimal |
| `/proc/sys/kernel/perf_event_paranoid` | PASS | `2` | text decimal |
| `/proc/sys/kernel/modules_disabled` | PASS | `2` | text decimal |
| `/proc/sys/kernel/randomize_va_space` | PASS | `2` | text decimal |
| `/proc/sys/kernel/unprivileged_bpf_disabled` | PASS | `2` | text decimal |

Every path passed owned buffer allocation, pathname poke/peek verification,
`filp_open`, `kernel_read` return/position advancement, `filp_close`, and
`kfree` checks. Raw sysctl values, runtime pointers, and KASLR slide remain
private-only and are not committed.

Post-proof candidate `version/status/selftest` passed. Rollback to v2321 used
`native_init_flash.py`; pushed-image SHA and boot readback SHA matched the
v2321 SHA. Final rollback health first attempt hit the same serial
fragmentation class; bridge restart + retry passed with
`selftest pass=11 warn=1 fail=0`. Final bridge status was
`connected-no-immediate-error`.

## Timing

Timing was recorded in:

- `workspace/private/runs/kernel/vfs-read-hardening-posture-bundle-20260701T102654Z/timeline.json`.

The live run started at `2026-07-01T10:26:54Z`.

| Phase | Elapsed |
| --- | ---: |
| rollback/fallback/recovery artifact precondition | `0.642s` |
| baseline bridge status | `0.320s` |
| baseline version/status/selftest | `2.099s` |
| candidate flash helper total | `64.571s` |
| candidate bridge restart after flash | `1.657s` |
| candidate health first attempt | serial fragmentation at `10.151s` |
| candidate bridge restart | `1.645s` |
| candidate health retry | `7.105s` |
| REPL selftest | `5.893s` |
| live hardening-posture bundle | `117.420s` |
| post-proof candidate health | `1.455s` |
| rollback flash helper total | `65.706s` |
| rollback bridge restart after flash | `0.885s` |
| rollback health first attempt | serial fragmentation at `10.139s` |
| rollback bridge restart | `1.637s` |
| rollback health retry | `8.089s` |
| final bridge status | `0.322s` |

All serial bridge operations in the accepted live path were run sequentially.

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py SelftestIntegrationTests.test_vfs_read_files_reads_proc_nodes_with_redacted_summary SelftestIntegrationTests.test_vfs_read_hardening_posture_bundle_uses_named_contract`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90_repl.py vfs-bundle --help`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img --no-objdump filp_open kernel_read filp_close`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 tests/test_a90_repl.py` (`204` tests, OK)
- `git diff --check`

Live validation:

- Candidate flash passed with matching candidate readback SHA.
- Candidate health retry and REPL selftest passed.
- `vfs-bundle hardening-posture` passed for all six paths.
- Post-proof candidate health passed.
- Rollback to v2321 passed with matching rollback readback SHA.
- Final v2321 health retry and bridge status passed.

## Bundle Outcome

`hardening-posture` is now the preferred observation bundle for these
`/proc/sys/kernel` file-node equivalents. Do not add individual call-proofs for
the same state unless a future target has no file-node equivalent or requires a
genuinely new ABI shape.
