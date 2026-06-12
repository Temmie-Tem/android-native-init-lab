# Native Init V2249 Tail Perf Sampler Hook Live

## Summary

- Cycle: `V2249`
- Type: rollbackable live test boot of the helper-started post-FWREADY perf regs/codeword sampler.
- Decision: `v2249-tail-perf-sampler-hook-live-partial`
- Result: PARTIAL PASS
- Private run: `workspace/private/runs/kernel/v2249-tail-perf-sampler-live-20260612-122446`
- Test boot: `workspace/private/inputs/boot_images/boot_linux_v2249_tail_perf_sampler_hook.img`
- Rollback boot: `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`

## Live Result

- V2249 flash/readback SHA matched: `df0a39f03f313d9adff3aa519dfddbf9587a995053793fcf3ac4bca3d66b8536`.
- V2249 boot verified: `A90 Linux init 0.9.269 (v2249-tail-perf-sampler-hook)`.
- V2249 selftest: `fail=0`.
- Helper route result: `wlan0-ready`.
- Tail sampler start marker: `tail_perf_regs_codeword_sampler.started=1`.
- Tail sampler finish marker: `finish.after_fwclass_feeder.output_exists=1`.
- Tail sampler process: `wait_rc=0`, `exit_code=0`, `timed_out=0`.
- Rollback to V2237 verified: `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`, selftest `fail=0`.

## Kernel Observation

- V2216 parser accepted exact per-boot codeword slide for this V2249 boot.
- PC codeword match: `512/512`.
- LR-4 codeword match: `507/507`.
- LR codeword match: `507/507`.
- Printed samples: `512`.
- Perf stats count: `668`.
- Read errors: `12`.
- Unique `ctx_pc`: `297`.
- Unique `ctx_lr`: `242`.
- Unique comms: `31`, including `a90_android_exe`, `cnss-daemon`, `tftp_server`, and `a90_bpf_perf_re`.

## Tail Scoring

- V2247 scorer decision: `v2247-tail-pc-lr-scorer-pass`.
- V2246 target whitelist count: `7`.
- V2247 target hits: `0/512` printed samples.
- Source hit counts: none.
- Symbol hit counts: none.

## Interpretation

V2249 proves the hook placement and ramdisk-packaged sampler are viable: the sampler starts before the helper's post-FWREADY `boot_wlan` trigger, remains alive through the firmware_class feeder, and produces an exact-slide PC/LR capture from the same boot that reaches `wlan0-ready`.

The zero V2247 target hits are not yet a path-negative result. The helper output shows `samples occupied=668 printed=512 capacity=1024`, so the capture lost 156 occupied ring entries at the text-output layer. The next unit must remove that output loss before concluding that CPU-clock sampling misses the narrow firmware_class/qcacld-HDD tail.

## Next Unit

V2250 should keep the same V2237 route and V2249 hook placement, but set the sampler `print_limit` to `1024` or otherwise emit every occupied ring entry. If V2250 still reports exact slide with zero V2247 target hits and no output loss, the next pivot is not another generic CPU-clock retry; it is a target-specific observable for the firmware_class/qcacld-HDD tail.

## Safety

The live run stayed within the current safety scope: boot partition flash only through `native_init_flash.py`, rollback to V2237, read-only BPF perf-event observation, no `probe_write_user`, no tracefs control write, no eSoC/PCIe/GDSC/PMIC/GPIO path, no Wi-Fi credentials, no DHCP/routes, and no external ping.
