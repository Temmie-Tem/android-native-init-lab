# V1193/V1194 eSoC MDM Power-On Gate Plan

- **cycle**: V1193/V1194
- **date**: 2026-05-29
- **type**: V1193 live FAIL → V1194 host-only then live

## V1193 Evidence

| metric | value |
|---|---|
| `policy_load_result` | `policy-load-pass` |
| `gate_open` | True |
| `per_mgr_domain` | `u:r:vendor_per_mgr:s0` |
| `mdm_helper_early_esoc0_found` | True (500ms) |
| `per_mgr_subsys_esoc0` | count=0 |
| `mhi_pipe_count` | 0 |
| `ks_count` | 0 |
| `ESOC_WAIT_FOR_REQ` | blocked 53 minutes (t=3192s) |
| `esoc0 crash` | t=3193s (vs V1191 t=253s) |

## Root Cause Analysis

### ESOC_REQ_IMG never arrived

mdm_helper (pid 3449) blocks in `ESOC_WAIT_FOR_REQ` (ioctl `0x8004cc02`) for 53 minutes.
`ESOC_REQ_IMG` never arrived. Therefore MDM firmware transfer never happened.

### Why ESOC_REQ_IMG never arrives

`ESOC_REQ_IMG` is sent by the MDM hardware (SDX50M) when it powers on and requests
firmware from the host. MDM hardware powers on via:

```
subsys_esoc0 open → subsys_device_open → __subsystem_get(esoc0) → subsys_start
  → provider powerup() → mdm_subsys_powerup() → AP2MDM GPIO toggle → MDM powers on
  → MDM sends ESOC_REQ_IMG
```

Without `subsys_esoc0` being opened, MDM hardware is never powered on, so `ESOC_REQ_IMG`
never arrives.

### Why per_mgr's subsys_esoc0 open fails

per_mgr (pm-service) opens subsys_esoc0 in response to a client request (cnss-daemon
modem peripheral). The open enters `mdm_subsys_powerup()` (D-state). The open is on a
**binder thread** of per_mgr. When the binder transaction times out (~5s), the kernel
cancels the transaction. Later (at t=3193s), the deferred fput cleanup runs:
`subsys_device_close → subsystem_put(esoc0 count:0) → Reference count mismatch → modem SSR`.

### Correct fix

The helper must open `subsys_esoc0` **directly** (as a subprocess) AFTER mdm_helper has
registered REQ_ENG (via esoc-0 open). This is the V849 approach combined with V1193:

```
1. mdm_helper opens esoc-0, registers REQ_ENG, blocks in ESOC_WAIT_FOR_REQ
2. Helper subprocess opens subsys_esoc0 → mdm_subsys_powerup() → MDM powers on
3. MDM sends ESOC_REQ_IMG → mdm_helper wakes up
4. mdm_helper handles firmware transfer → IMG_XFER_DONE + BOOT_DONE
5. GPIO 142 fires → mdm_subsys_powerup() unblocks → subsys_esoc0 open succeeds
6. per_mgr can then serve modem peripheral as ONLINE → WLFW published
```

### V849 vs V1194

V849 (helper-only esoc0 open) blocked in D-state because there was no mdm_helper to
handle `ESOC_REQ_IMG`. Now with mdm_helper running (V1193 proved it), the sequence
should complete.

## V1194 Gate

**New helper flag**: `--pm-observer-open-subsys-esoc0-after-mdm-helper-esoc`

After mdm_helper has esoc-0 (confirmed by esoc0_found poll), spawn a bounded
`subsys_esoc0` hold subprocess that:
1. Opens `/dev/subsys_esoc0` (blocks in D-state / mdm_subsys_powerup)
2. Holds it until GPIO 142 fires OR timeout (5 minutes)
3. Reports GPIO 142 IRQ count at intervals (from `/proc/interrupts`)
4. Also monitors for MHI device node appearance

Constraints:
- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping
- Bounded timeout (5 minutes max)
- Reboot-required if subsys_esoc0 blocks (known from V849)
