# OPERATOR SPEC — ACDB `acdb_ioctl` interposition capture of the custom-topology payload (2026-06-15)

**Author:** operator (host-side RE), not the autonomous loop. This is a build spec for the
loop to implement. It supersedes the cross-process dmabuf / file-read source-buffer capture
line (V2463–V2473), which is a dead end for the reasons below.

## Goal

Capture the **4916-byte `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE` (cal_type 39) payload** that V2461
saw delivered via `AUDIO_SET_CALIBRATION` (`mem_handle=37`, `cal_size=4916`) but never read,
because the bytes live behind a dma-buf that is opaque to cross-process inspection
(procfs fd reopen → `ENXIO`, owner-VA read → `EIO`, early-dup → `ENXIO`; see V2466–V2472).

This payload is the missing input for native ACDB replay (V2462 boundary). Once it is pinned
(bytes + length + SHA-256), the native replay scaffolding can send it through
`/dev/msm_audio_cal`.

## Why interposition, not more snooping

Host RE of the stock 32-bit `libacdbloader.so` (+ `libaudcal.so`) from the V2324 vendor dump
shows the topology blob is produced **inside the audio HAL process** by the ACDB engine and
copied into the dma-buf only afterward. The clean capture point is the ACDB database query
call itself, **before** the dma-buf copy. That call is `acdb_ioctl`, which `libacdbloader.so`
imports (`U acdb_ioctl`) from `libaudcal.so` — so it is **interposable via `LD_PRELOAD`**.

Capturing in the HAL's own process avoids: (a) dma-buf cross-process opacity, (b) reversing
the `.acdb` binary format, (c) reversing `acdb_loader_init_v4`'s init struct, (d) injecting
into `audioserver` by ptrace. The HAL inits ACDB and fetches the topology naturally; our
wrapper just observes the output buffer.

## RE facts (evidence)

Tool: `workspace/private/inputs/toolchains/llvm-arm-toolchain-ship-10.0/bin/llvm-objdump`
(LLVM 10, run with `LD_LIBRARY_PATH=tmp/relibs` where `tmp/relibs/libtinfo.so.5` →
host `libtinfo.so.5`). Analyzed files (host-only, proprietary, never commit):

- `workspace/private/runs/audio/v2324-aud0-inventory/vendor_dump/lib/libacdbloader.so`
- `workspace/private/runs/audio/v2324-aud0-inventory/vendor_dump/lib/libaudcal.so`

Confirmed `acdb_ioctl` signature (from prologue at `libaudcal.so` `0xd884`, Thumb):
`push {r4-r9,lr}` (28B) + `sub sp,#4` then `ldr.w r9,[sp,#32]` reads the 5th arg off the
stack; `r0..r3` are args 1–4. Classic Qualcomm ACDB ABI:

```c
int32_t acdb_ioctl(uint32_t command_id,    // r0
                   const uint8_t *in_buf,   // r1
                   uint32_t       in_len,   // r2
                   uint8_t       *out_buf,  // r3
                   uint32_t       out_len); // [sp,#32] -> r9
```

- Command IDs are in the `~0x12xxx–0x13xxx` range (switch/`tbh` jump table on `r0`). The exact
  `ACDB_CMD_GET_AVCS_CUSTOM_TOPO_INFO` constant is **not needed**: filter empirically by
  `out_len == 4916`. Record the observed `command_id` for documentation.
- `acdb_loader_send_common_custom_topology` (`libacdbloader.so` `0x8cf0`) first queries size
  (`ACDB_CMD_GET_AVCS_CUSTOM_TOPO_INFO_SIZE`, `out_len==4` returning 4916), then fetches the
  payload (`out_len==4916`), then `allocate_cal_block` (ION/dma-buf) + `AUDIO_SET_CALIBRATION`.
  The first two are the `acdb_ioctl` calls we interpose.
- `acdb_loader_init_v4` (`libacdbloader.so` `0x808c`) takes `arg0`=acdb-file-list struct ptr,
  `arg1`==4; allocates ~5824B of stack. Replicating it standalone is expensive — **the HAL
  does this for us**, which is why interposition beats an own-process `dlopen` helper.

## Helper to build

A **32-bit `armeabi-v7a`** shared object (the stock audio HAL is 32-bit; must match), e.g.
`libacdbtap.so`:

```c
// real = dlsym(RTLD_NEXT, "acdb_ioctl") resolved lazily on first call
int32_t acdb_ioctl(uint32_t cmd, const uint8_t *in, uint32_t in_len,
                   uint8_t *out, uint32_t out_len) {
    int32_t r = real_acdb_ioctl(cmd, in, in_len, out, out_len);
    if (out && out_len > 0) {
        // append one record to a private capture file:
        //   {pid, tid, cmd(hex), in_len, out_len, ret=r, sha256(out[0:out_len])}
        // and write raw out bytes to <dir>/acdbtap-<cmd>-<seq>-<out_len>.bin
        // (only out_len bytes). Especially flag out_len == 4916.
    }
    return r;
}
```

Requirements:
- Resolve the real symbol with `dlsym(RTLD_NEXT, "acdb_ioctl")`; never recurse.
- Be allocation-light and reentrancy-safe (the HAL calls this many times); guard the dump
  with a simple in-process append, bounded.
- Write raw payloads only under a private capture dir (e.g. `/data/local/tmp/a90-acdb-tap/`),
  then `adb pull` to `workspace/private/runs/audio/<run>/`. **Never commit raw bytes.**
- Public/report output: per-call `command_id`, `in_len`, `out_len`, `ret`, SHA-256 only.

## Injection (the genuinely tricky part — capsule engineering)

`LD_PRELOAD` `libacdbtap.so` into the process that loads `libacdbloader.so` — the audio HAL
(`android.hardware.audio.service`; the worker TID seen as the `/dev/msm_audio_cal` owner in
V2416/V2458). Constraints/contract:

1. The preload must be active **before the HAL initializes ACDB**. If the topology fetch is a
   one-time init-cached call, set the preload, then **restart the audio HAL** (so it re-execs
   with the preload), then trigger playback. If unsure, restart-then-play is the safe order.
2. Mechanism is the transient Magisk measurement capsule's job (you built M0/M1). Candidate
   approaches in order of preference: an init `.rc` `setenv LD_PRELOAD` override for the HAL
   service via a Magisk service overlay; or a wrapper-exec shim for the service binary; or a
   root-set environment on a manual service relaunch. The `wrap.<name>` zygote property likely
   does **not** apply (the HAL is init-started, not zygote-spawned) — verify before relying on it.
3. **SELinux is the main risk:** loading an unconfined preload into a system HAL domain under
   enforcing may be denied. If blocked, capture the denial (`dmesg`/`logcat avc:`) and report
   it; do not silently disable enforcing as a "fix". A bounded permissive-for-the-capture or a
   minimal `magiskpolicy` allow, fully reverted on cleanup, is acceptable only inside the
   recoverable envelope and must be documented.

## Trigger & acceptance

1. Boot stock Android via the checked handoff; stage the transient capsule + `libacdbtap.so`.
2. Establish the preload into the audio HAL; restart the HAL.
3. Run the existing AudioTrack speaker stimulus (reuse the V2377/V2407 path).
4. The wrapper records `acdb_ioctl` calls. **Acceptance = at least one call with
   `out_len == 4916` captured**, its raw bytes saved privately and SHA-256 recorded; ideally
   also the paired `out_len==4` size query returning 4916.
5. Pull artifacts privately, clean up the capsule + any sepolicy change, reboot to recovery,
   checked rollback to **v2321**, final `selftest fail=0`.

This finally pins the V2462-blocked payload (bytes + length 4916 + SHA-256). Combined with the
V2461/V2462 ioctl-sequence + kernel mem-handle/cleanup facts, native N3 replay is then
unblocked: allocate an ION/dma-buf of 4916, fill with these bytes, run the
`ALLOC`/`SET`/`DEALLOC` sequence on `/dev/msm_audio_cal`, keep fds open across the bounded PCM
probe.

## Fallback (only if in-HAL preload is truly blocked)

Own-process ARM32 helper that `dlopen`s `libacdbloader.so` and calls
`acdb_loader_init_v4` + `acdb_loader_send_common_custom_topology` with `acdb_ioctl`
interposed in *our* process. This removes the SELinux-on-HAL risk but requires RE of the
`acdb_loader_init_v4` arg0 struct (acdb file list) — **ping the operator for that RE before
taking this path**; do not guess the struct.

## Boundaries (unchanged)

Measurement only. Transient capsule, no persistent module install. No native
`/dev/msm_audio_cal` calibration ioctls in this unit. No native speaker write. Recoverable
envelope + checked rollback to v2321 + anti-churn/fails-twice all stay in force. Do not commit
raw payload bytes, the vendor `.so` files, or unredacted captures.
