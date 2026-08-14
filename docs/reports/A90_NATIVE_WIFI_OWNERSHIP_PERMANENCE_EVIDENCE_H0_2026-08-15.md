# A90 native Wi-Fi ownership permanence: the evidence already exists

Date: 2026-08-15
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 public-source audit of existing live evidence
Device or live effect: none
Disposition: recovers an answered question whose answer no current document cites

## Why this report exists

The selected isolated-Debian direction keeps native PID 1 alive as the permanent
Wi-Fi owner. Reading only the current documents, that choice looks like it was
reached by elimination: the alternative closure
`DEBIAN_OWNS_WIFI_ZERO_NATIVE_SIDECARS` was attempted as an atomic ownership
diagnostic and retired as "disproportionate for a single measurement", which is
a cost judgement rather than a disproof.

That reading is wrong, and it is wrong in a way that invites the architecture to
be reopened on false grounds. The question was answered live on 2026-07-04, by
experiment, for a structural hardware reason. **No document in `docs/plans/` or
any current `docs/reports/` A90 file cites that evidence.** This report connects
it back.

## The question

> Must native own Wi-Fi permanently, or is native only a bootstrap owner that
> can hand the WLAN path to Debian and then disappear?

If bootstrap ownership were sufficient, native userspace could be retired at
handoff, no native task would survive into the Debian steady state, the
`/proc/<native-pid>` capability-exposure blocker would have nothing to expose,
and most of the isolated design's namespace, veth, and supervision machinery
would be unnecessary.

## The evidence chain

The `SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA*` series worked this exact problem.

**Symptoms, repeatedly, in Debian after handoff.** WSTA13 (`SCAN_VISIBILITY_BLOCKED`),
WSTA14 (`LINKSTATE_SCAN_BLOCKED`), WSTA16 (`IMMEDIATE_HANDOFF_SCAN_BLOCKED`),
WSTA17 (`HANDOFF_MATERIALIZATION_BLOCKED`), WSTA25 and WSTA29
(`SCAN_BLOCKED`). WSTA14's terminal is `wifi-sta-assoc-failed`: `wlan0` exists
as a managed wireless interface and is administratively UP, but never reaches
RUNNING or LOWER_UP; a direct `iw` scan returns rc 234 with BSS count 0, and
`wpa_cli` scan windows stay at result count 0.

Critically, the WSTA14 live path was not a configuration in which native still
held the interface. It was
`native materialization -> Debian switch_root -> firstboot STA helper`, with
native's own pre-handoff materialization passing
(`wlan0_present=1`, `link_up_rc=0`, `softap-iftype-probe-pass`). Native brought
the interface up, then handed the machine over, and Debian could not use it.

**Root cause, WSTA18 (`CONTROL_PLANE_BLOCKED`).** This unit compared native
pre-handoff WLAN control-plane evidence against Debian post-handoff evidence on
the same image. Native STA-only scan materialized `wlan0` and visible BSS before
handoff. After `switch_root`, Debian still saw a managed `wlan0`, a phy, and an
unblocked WLAN rfkill, but a direct `iw scan` returned rc 234 /
`Invalid argument (-22)`. The report's own stronger finding is from dmesg:

> after PID1 handoff, the WLAN firmware/control path reports `firmware down
> indication`, `PD service down ... Root PD shutdown`, and repeated
> `WMI stop in progress`. The Debian process snapshot lacks the native vendor
> WLAN userspace (`cnss-daemon`, `cnss_diag`, and related Android/vendor
> companions); only kernel WLAN threads and Debian `dropbear` remain.

**Resolution, WSTA19 (`NATIVE_OWNED_CHROOT_WIFI_PASS`).** Its opening sentence
states the conclusion directly:

> WSTA18 showed that full `switch_root` loses the vendor WLAN control plane:
> Debian keeps enough kernel objects to see `wlan0`/phy/rfkill, but WCNSS/WMI
> goes down and direct scans return `Invalid argument`.

WSTA19 then validated the alternative model live: native PID 1 stays alive and
owns the WLAN control plane while Debian runs as a service consumer. Native scan
passed before the handoff, SSH reached Debian, and native scan still passed
while Debian's `dropbear` was active. Terminal:
`wsta19-native-owned-chroot-wifi-boundary-pass`.

## Mechanism

The netdev is not the radio. On this SoC the WLAN firmware runs on a separate
connectivity subsystem, and the host drives it over WMI. Keeping that subsystem
and its protection domain alive is the job of vendor userspace daemons —
`cnss-daemon` and `cnss_diag` are the two the WSTA18 snapshot names. `switch_root`
replaces PID 1 and destroys that userspace. The kernel objects survive, so
Debian still sees `wlan0`, a phy, and rfkill; the firmware behind them does not,
so every command that needs the firmware fails with `Invalid argument`.

This is why the failure presents as "the interface is there and up but scanning
returns nothing useful" rather than as a missing device.

## What this settles

- Native Wi-Fi ownership is a **structural requirement of this device**, not a
  preference, not an artifact of experiment sequencing, and not a consequence of
  having retired the atomic ownership diagnostic.
- The isolated-Debian design's central premise — that native must survive the
  handoff — is **correct and live-supported**.
- Consequently the `/proc/<native-pid>` exposure is a real and unavoidable
  consequence of the required architecture, not an incidental one. Something
  native must survive, so something must bound what Debian can name.
- A full `native -> Debian` handoff with no surviving native task cannot deliver
  Wi-Fi on this device as the WLAN path is currently brought up.

## What this does not settle

- Whether Debian could **re-materialize** the control plane itself — load the
  firmware, bring up the protection domain, and speak the vendor control
  protocol from Debian userspace. WSTA14 recommended exactly this as the open
  alternative: "the Debian handoff can either preserve a usable `wlan0` scan
  state or explicitly reset/re-materialize the WLAN path after switch_root."
  Neither was implemented.
- That path means reproducing the vendor connectivity daemons in Debian, which
  is the same conclusion the later atomic ownership diagnostic reached from a
  different direction when it required a new Binder/AF_UNIX/process-broker
  runtime and still could not reproduce the distinct post-fork Android
  UID/GID/capability roles. The two findings agree.
- Whether a different bring-up path exists at all is a separate H0 question. It
  is not answered here and no work on it is authorized here.

## Corrections this report makes to the current record

- The current documents present native Wi-Fi ownership as the residue of a
  retired experiment. It is instead the validated outcome of WSTA18/WSTA19.
- "Debian owning Wi-Fi is untested" is false; it was tested across roughly
  fifteen WSTA units.
- "Debian's attempt failed only because native still held the interface" is also
  false; WSTA14 and WSTA18 both ran after `switch_root`, with native userspace
  gone.

## Consequence for the selected direction

This report **supports** the selected closure `NESTED_PID_NAMESPACE_ISOLATION`
and does not reopen it. It also removes a specific risk: that the architecture
would be reopened later on the incorrect belief that native survival was never
justified.

It does not license the reverse error either. The isolated design's statement
that the native supervisor "is production machinery and therefore remains in the
permanent execution-critical closure" is now supported for the **Wi-Fi owner**
specifically. It remains unargued for anything else the supervisor accumulates,
and any additional permanent native responsibility still needs its own
justification.

## Sources

All public, all previously committed:

- `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA14_LINKSTATE_SCAN_BLOCKED_2026-07-04.md`
- `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA18_CONTROL_PLANE_BLOCKED_2026-07-04.md`
- `docs/reports/SERVER_DISTRO_WIFI_STA_UPSTREAM_WSTA19_NATIVE_OWNED_CHROOT_WIFI_PASS_2026-07-04.md`
- `docs/reports/A90_NATIVE_WIFI_SIDECAR_PROC_ROOT_EXPOSURE_HOST_INCIDENT_2026-08-13.md`
- `docs/plans/A90_HEADLESS_HANDOFF_MINIMUM_AND_WIFI_OWNERSHIP_DECISION_2026-08-13.md`
- `docs/plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md`

## Boundary

Produced from public repository documents only. Device, `/dev`, USB, network,
`workspace/private`, S22+, and S20+ contacts are zero. No ordinal, identity,
artifact, approval, candidate, qualification, or command is created, and no D0,
D1, or F1 authority is granted or implied.
