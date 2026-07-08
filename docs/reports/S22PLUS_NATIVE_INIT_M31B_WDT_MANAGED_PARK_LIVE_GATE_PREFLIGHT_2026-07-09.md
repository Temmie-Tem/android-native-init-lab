# S22+ M31B Watchdog-Managed Park Live Gate Preflight (2026-07-09)

## Verdict

PREFLIGHT PASS / LIVE NOT EXECUTED IN THIS UNIT.

No candidate flash, rollback flash, reboot, Odin transfer, partition write, or
device write was run while producing this report.

The M31B fail-closed helper, active one-shot `AGENTS.md` exception, candidate
artifacts, rollback artifacts, Android/root baseline, and current boot hash all
passed default dry-run.

## Active Gate

Helper:

`workspace/public/src/scripts/revalidation/s22plus_m31b_wdt_managed_park_live_gate.py`

Live ack:

`S22PLUS-M31B-WDT-MANAGED-PARK-LIVE-GATE`

Rollback ack:

`S22PLUS-M31B-WDT-MANAGED-PARK-ROLLBACK-FROM-DOWNLOAD`

Candidate:

```text
AP.tar.md5       06d1c149c7c09a284062826f21ac848220e99d552d6b91762abbfb80f3679527
boot.img         206fbb40df69a496f7fbe67e32cf862049d9258ef518db6949e1b5db2f4afdc4
/init            b01e52d3762e3cbdcba3501b00bb1dc9f9084899550ea23b92df43884bed23d0
module-list      80da959311e4a0f6bedb40da3c6f74c7fd5918017e40e0787b3e17c153cfe937
source           32d85b4aeb64e5e1615b175b93fde166795598bfa0614934a9dcfb1bb165230d
kernel           bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
```

Rollback:

```text
Magisk boot rollback AP   d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56
stock boot fallback AP    1ee92a86f30e4acb12509272630e1bef5215d1a12686ac69a3b399b43740535e
```

## Dry-Run Evidence

Command:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m31b_wdt_managed_park_live_gate.py
```

Result:

```text
dry-run ok: M31B candidate, rollback APs, AGENTS exception, Android stability, and current boot hash verified
```

Private log:

`workspace/private/runs/s22plus_m31b_wdt_managed_park_live_gate_20260708T162526Z/s22plus_m31b_wdt_managed_park_live_gate.txt`

Redacted dry-run facts:

```text
agents_exception_missing=[]
model=SM-S906N
device=g0q
bootloader=S906NKSS7FYG8
incremental=S906NKSS7FYG8
vbstate=orange
boot_recovery=0
boot_completed=1
su_id=uid=0(root)
android_stability_samples=4
android_stability_result=ok
current_boot_hash=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
odin_l during dry-run: no device
```

The helper verified the candidate manifest safety contract:

```text
boot_only=true
live_flash_authorized=false
requires_new_sha_pinned_agents_exception_before_flash=true
auto_reboot=false
intended_reboot_syscall=false
reboot_request=null
configfs_runtime_gadget=false
acm=false
block_device_writes=false
module_binary_injection=false
```

## Interpretation

M31B live is now ready to run under the active one-shot exception. The live
proof is not self-Download. It is survival past the observation window without
PMIC/RDX reset. Manual Download is recovery-only and should happen only after
the helper asks for rollback.

The expected operator action during live:

- do not press buttons during the observation window;
- if the helper reports the survival window passed, manually enter Download
  mode for rollback when asked;
- if the device shows PMIC/RDX or otherwise stops before the helper asks, report
  the exact screen/state and enter Download mode only for recovery.

## Next

Run exactly one attended live command if proceeding:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m31b_wdt_managed_park_live_gate.py \
  --live \
  --ack S22PLUS-M31B-WDT-MANAGED-PARK-LIVE-GATE
```

If manual recovery is required later:

```bash
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/s22plus_m31b_wdt_managed_park_live_gate.py \
  --rollback-from-download \
  --ack S22PLUS-M31B-WDT-MANAGED-PARK-ROLLBACK-FROM-DOWNLOAD
```
