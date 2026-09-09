# S22+ v0.1.2-rc.1 restricted gauge HUD

Internal P378 extends [Status HUD V1](S22PLUS_FYG8_STATUS_HUD_V1.md). It remains
H0 until independent review, exact qualification, connected preparation and
fresh attended Process-v2 approval. Permanent boundaries and the existing
root-console deadline, one-shot return, rollback and final health are unchanged.

## Fixed provider and ownership

The inherited vendor_boot init already loads all 73 USB-plan modules, including
MAX77705 MFD and PDIC. The preceding candidate adds 17 display/return modules.
P378 appends one telemetry module to those additions; the renderer loads it
after the 12 display modules. The five return modules retain their existing
owner. No existing MFD, PDIC or USB module is reloaded or rebound.

The new platform driver binds only the existing unbound `max77705-fuelgauge`
MFD child. It checks the exact parent and adapter OF nodes, existing client
addresses 0x66/0x36, common adapter, client data and reviewed parent structure
layout. The DT resistor value must be 5. Probe performs no I2C transaction.
Root model checks accept the two actual merged Waipio model strings; the F1
owner still binds the exact SM-S906N/g0q/FYG8 device and candidate.

The first sample verifies PMIC ID 0x15 and the reviewed revision bits. Sampling
then reads only SOCREP 0x06, VCELL 0x09 and CURRENT 0x0a with SMBus word reads.
There are no register-write helpers, dummy clients, IRQ handlers, charger work,
firmware updates or stock fuel-gauge initialization. The existing parent mutex
is acquired with trylock to avoid queueing behind the PDIC owner. The SMBus
transaction itself can still block; this is not proof against a kernel stall.
The first bus failure latches and prevents further reads. At most 601 samples
are attempted, cached for one second with the original sample-start timestamp.

A read-only module parameter exposes one bounded ASCII record with sequence,
sample-start monotonic time, validity/error, raw values and converted values.
Raw SOC is retained; display SOC clamps the vendor register estimate at 100%.
Voltage uses raw ×625/8 microvolts. Current interprets the 16-bit register as
signed, then uses raw ×15625×5/100 microamps. It is a gauge measurement, not
Android's battery-policy percentage or a derived charging-state claim.
Temperature and charge state remain N/A unless the existing fixed battery
sysfs interface independently supplies them.

## Consumer and presentation

The separately owned collector adds only the fixed module parameter path.
Its strict parser recomputes converted values from raw fields and rejects
errors, malformed records, inconsistent conversions and out-of-range voltage.
The existing bounded procfs/sysfs reads, process ownership and nonblocking
SOCK_SEQPACKET transport remain. The packet grows from 72 to 96 bytes with a
new magic; PID1 still does not parse metrics or wait for collector cleanup.

System data retains collection-start age; gauge data retains its own read-start
age, which can be later than collection start. Both expire after five seconds.
Renderer checks include run, sequence, ranges, future timestamps and consistent
cached gauge values, preserving the gauge baseline across unavailable packets.
Malformed packets close only metrics FD3. Collector absence, exit or a blocked
read leaves console control available within the existing process model.

White bitmap text on the 120-pixel grid adds GAUGE SOC, VOLTAGE, signed CURRENT
and GAUGE AGE; the footer is `v0.1.2-rc.1` / `GAUGE STATUS HUD`. The immutable GEM
and matched flip-event lifecycle remains unchanged. Evidence age is checked
again at the matched event. Visible text remains operator observation.
The 256 KiB diagnostic budget and finite drain remain unchanged.

## Qualification and review scope

Host qualification covers actual ARM64 conversions and parsers, real wrapper
output to parser, generated PID1/collector/renderer IPC, DRM lifecycle fixtures,
stale/invalid/cache data and blocked/absent collectors with console control.
The module must be A/B identical and resolve every imported CRC against the
exact kernel Image. Build/linkage does not prove live binding or gauge reads.
The sixth live command requires three distinct fresh gauge plus memory/CPU
samples across at least two seconds with a BUSY frame. All five existing root
console qualifications, exact return, one rollback and final health remain.

Changed module source/ABI, register set, ownership, wire format, rendering or
recovery requires scoped review. This document introduces no temporary gate,
standing session, candidate replay, policy activation or device authority.
