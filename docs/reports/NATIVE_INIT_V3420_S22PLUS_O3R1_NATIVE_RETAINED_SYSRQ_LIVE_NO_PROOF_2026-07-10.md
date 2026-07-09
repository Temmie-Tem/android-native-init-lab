# V3420 S22+ O3R1 Native Retained SysRq Live Result

## Verdict

`NO RETAINED O3R1 PROOF; MAGISK BASELINE RESTORED; TRANSIENT ANDROID USB FAILURE RECOVERED`.

The exact O3R1 boot-only candidate transferred and left the original Odin
endpoint. The operator observed a bootloop, not the expected retained panic
screen. No Download endpoint appeared automatically. After attended manual
Download entry, the helper restored the exact Magisk boot AP with Odin rc=0.

The phone reached the normal Android UI, but its Android USB gadget enumerated
for about four seconds and then disappeared. The helper therefore timed out
waiting for ADB and recorded rollback `rc=5`. A later normal Android reboot
restored stable Samsung USB, ADB, and `ttyACM0`. Read-only post-recovery checks
prove the exact Magisk boot, root, MID sec_debug state, and ample storage.

Post-recovery `/proc/last_kmsg` contains neither the exact O3R1 marker nor a
SysRq crash or init-death panic. O3R1 did not prove the direct-PID1 retained
observation channel. Its exception is consumed and O3R2 is not authorized.

## Post-Run Condition Correction

The run did not establish its intended sec_debug prerequisite inside the
candidate boot. Current rooted Android proves `sec_debug` is a loadable module,
not persistent kernel state:

```text
/proc/modules: sec_debug 32768 ... Live
/sys/module/sec_debug/parameters/enable=1
/sys/module/sec_debug/parameters/debug_level=18765
```

The O3 and O3F 59-module plans explicitly contain `sec_debug.ko`. O3R1 instead
forbids all module insertion. Module state is reset on every kernel boot, so the
Android preflight's `sec_debug enable=1` did not carry into O3R1. MID is a
persistent selection, but the candidate did not prove that the sec_debug module
and its retention hooks were loaded before writing kmsg or forcing panic.

Therefore the no-hit does **not** falsify the general hypothesis that a direct
PID1 marker can be retained when the Samsung capture stack is active. It shows
that O3R1 was not a valid test of that hypothesis because a load-bearing runtime
condition was missing. The bootloop is compatible with repeated SysRq panic,
repeated PID1-exit panic, or an earlier boot failure; without the retained
marker those cases remain indistinguishable.

## Exact Runs

Live and rollback run:

```text
workspace/private/runs/s22plus_o3r1_native_retained_sysrq_live_gate_20260709T220353Z
candidate_ap_sha256=2a92008b4632a8907fec96f0d8194a8461c16060cb1d919aeba7446020c4beda
candidate_boot_sha256=fc0dce090f454b621ed90e63dd11cfe29dad8de0fe04d3c1f138a004d9d2f6aa
candidate_flash_attempted=true
candidate_left_odin=true
rollback_entry=attended-manual
rollback_target=magisk
rollback_flash_rc=0
helper_result=rollback-failed
helper_rc=5
```

Delayed read-only collection after Android USB recovery:

```text
workspace/private/runs/s22plus_o3r1_native_retained_sysrq_live_gate_20260709T221905Z
mode=postrollback-read-only-collection
retained_verdict=no-retained-o3r1-proof
retained_rc=9
last_kmsg_bytes=2097136
pstore_files=[]
```

## Timeline

```text
live_session_start    2026-07-09T22:04:08.074125Z
candidate_flash_start 2026-07-09T22:04:18.850752Z
candidate_flash_done  2026-07-09T22:04:20.393170Z
candidate_boot_ready  2026-07-09T22:04:20.666662Z
rollback_flash_start  2026-07-09T22:05:06.772482Z
rollback_flash_done   2026-07-09T22:05:08.122573Z
live_session_end      2026-07-09T22:10:09.256772Z
```

`candidate_boot_ready` has the gate's documented narrow meaning: original Odin
disconnected and the kernel boot attempt began. It is not PID1 proof.
`rollback_boot_ready` is absent because ADB did not remain available during the
helper's 300-second wait.

## Retained Classification

```text
marker_found=false
before_sysrq_found=false
sysrq_trigger_line=false
sysrq_panic_line=false
init_death_panic=false
kernel_panic=false
channel_proven=false
exact_pass=false
verdict=no-retained-o3r1-proof
```

The retained log contains a later `sysrq: Kill All Tasks` line but not
`sysrq: Trigger a crash`, not `Kernel panic - not syncing: sysrq triggered
crash`, and not `Attempted to kill init`. That unrelated line is not promoted
to O3R1 evidence.

## USB Diagnosis

Host kernel evidence after the Magisk rollback:

```text
07:05:46 Samsung Android 04e8:6860 enumerated
07:05:46 ttyACM0 created
07:05:50 Samsung Android disconnected
07:17:23 Samsung Android 04e8:6860 enumerated after normal reboot
07:17:23 ttyACM0 created and remained available
```

This rules out a permanent USB PHY/connector failure. The transient failure is
most consistent with Android USB gadget or Type-C session state after the
candidate/rollback sequence. The normal reboot cleared it.

Healthy post-reboot readback is internally consistent:

```text
persist.sys.usb.config=mtp,conn_gadget,adb
sys.usb.config=mtp,conn_gadget,adb
sys.usb.state=mtp,conn_gadget,adb
sys.usb.configured=configured
sys.usb.controller=a600000.dwc3
/config/usb_gadget/g1/UDC=a600000.dwc3
/sys/class/udc/a600000.dwc3/state=configured
/sys/class/typec/port0/data_role=device
/sys/class/typec/port0/power_role=sink
init.svc.adbd=running
init.svc.DR-daemon=running
```

The four-second first-rollback enumeration proves the physical data path and
UDC could initialize. The later stable normal reboot proves the same boot image
can restore the complete gadget. The missing discriminator is which property,
service, UDC bind, or Type-C role fell back immediately before the first
disconnect; that state was inaccessible after USB disappeared.

Storage is not the cause:

```text
host_root_available=126G
device_data_size=223G
device_data_used=3.8G
device_data_available=220G
device_data_use=2%
device_cache_use=2%
```

## Final Baseline

```text
target=SM-S906N/g0q/S906NKSS7FYG8
boot_completed=1
bootanim=stopped
root=uid=0(root) context=u:r:magisk:s0
boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
debug_level=18765 / 0x494d / MI
sec_debug_enable=1
usb=04e8:6860
adb_serial=RFCT519XWGK
tty=ttyACM0
```

## Interpretation And Next Bound

Do not repeat O3R1 and do not build the previously proposed O3R2. This run does
not distinguish between direct `/init` never executing, direct `/init`
executing and panicking without sec_debug loaded, or a failure before the
marker. The direct-PID1 phase remains `UNVERIFIABLE`.

The next justified architecture step is to return to the stock-first-stage
observation layer. Stock init already loads the sec_debug dependency stack as
well as the known Android USB/module/gadget stack. Add a bounded Magisk
`overlay.d` early-boot marker/control service whose execution and module-ready
condition are observable through normal Android/ADB. Direct PID1 USB work
remains downstream of that proof. A future direct-PID1 retained test would need
an independently derived and statically verified sec_debug module closure, not
another no-module O3R1 variant.
