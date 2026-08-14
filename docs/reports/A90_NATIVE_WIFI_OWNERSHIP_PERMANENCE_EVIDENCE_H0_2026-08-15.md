# A90 native Wi-Fi ownership permanence: the evidence already exists

Date: 2026-08-15
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 public-source audit of existing live evidence
Device or live effect: none
Disposition: recovers an answered question whose answer no current document cites

Scope of the claim, stated once so the title cannot be read past it: what is
live-supported is that **under the current WLAN bring-up path**, the native and
vendor control plane must stay alive **for as long as the Debian steady state
needs Wi-Fi**. That native PID 1 is the only possible permanent owner, and that
a Debian-owned control plane is impossible, are both **unproved** and are not
claimed here.

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

The absent vendor set recorded in that run also includes `pd-mapper` and
`rmt_storage`, which are the protection-domain and remote-storage services the
subsystem depends on.

**WSTA18 enumerated its own successors, and they are not all closed.** The same
report states that the next design "should not keep pushing direct Debian
netdev ownership", and lists four practical choices:

1. preserve/relaunch the minimal vendor WLAN userspace/control-plane set across
   handoff;
2. keep Wi-Fi owned by native init and expose a bounded service/API to Debian;
3. run Debian as a chroot/container under native PID 1 for the Wi-Fi-enabled
   appliance path instead of full `switch_root`;
4. treat full Debian PID 1 handoff as local USB/server-only unless a
   control-plane bridge is built.

The selected isolated-Debian design is choice 2: native keeps the owner and
Debian receives a bounded IP path. The WSTA lineage that followed took choice 3.
Choice 1 was never attempted, and it is materially lighter than reimplementing
the vendor stack — it is carrying a minimal existing set across the handoff, not
rewriting it.

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

- Under the current bring-up path, a surviving native/vendor control plane is a
  **structural requirement**, not a preference, not an artifact of experiment
  sequencing, and not a consequence of having retired the atomic ownership
  diagnostic. "Permanent" here means for the duration of the Debian steady
  state that needs Wi-Fi, not for the life of the device.
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
  WSTA18's own choice 1 is the narrower version of it: preserve or relaunch the
  minimal vendor set across the handoff. That is not the same as reproducing the
  vendor stack in Debian, and this report does not treat it as refuted.
- The later atomic ownership diagnostic is weaker evidence than it first looks
  for this question. It concluded that reproducing H24's *service set* needed a
  new Binder/AF_UNIX/process-broker runtime and still could not reproduce the
  distinct post-fork Android UID/GID/capability roles. That bears on
  reimplementation, not on choice 1's preserve-and-relaunch.
- That native PID 1 is the **only** possible permanent owner is unproved. So is
  the claim that a Debian-owned control plane is impossible. Neither is asserted
  here, and neither follows from WSTA18.
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

## Decision status, stated as separable propositions

| Proposition | Status |
|---|---|
| A persistent WLAN control plane is required | live-supported |
| Removing native/vendor userspace and letting Debian inherit the surviving `wlan0` works | **refuted** |
| Choice 2, native owner plus isolated Debian, works | live-supported |
| While choice 2 is the selected design, the `/proc` isolation is required | follows |
| Native PID 1 is the **only** possible permanent owner | unproved |
| Choice 1, preserve or relaunch a minimal vendor set across handoff | open, never attempted |
| A Debian-owned control plane is impossible | unproved |

The selected isolated-Debian design is therefore **the only currently
live-supported design, not the only possible one**. That distinction is the
whole point of this report: the architecture stands, and the claim that no
alternative could exist does not.

How much change each alternative would need:

| Change | Sufficiency |
|---|---|
| rootfs contents, keys, or `wpa_supplicant` configuration only | **insufficient** — the WCNSS/WMI control plane is already down before any of it runs |
| keep a minimal native/vendor service set alive | the validated direction; still a persistent native owner |
| re-run `cnss-daemon`, QRTR/QMI, protection-domain, `rmt_storage`, property and Binder dependencies inside Debian | theoretically possible, unproved |
| reimplement WLAN driver/firmware control in the kernel or a new userspace | possible, but a much larger separate project |

The first row closes a specific wrong turn: no amount of improving the Debian
rootfs, its authorization key, or its supplicant configuration can recover a
control plane that died at handoff. A proposal to "just fix the rootfs" is
answered by WSTA18 before it is made.

**Operational rule that follows.** The open possibilities do not license
removing native from the next candidate. Acting on choice 1 or on a
Debian-owned control plane requires proving it first, in its own H0 unit, and
that unit is about vendor control-plane reconstruction, not about rootfs
hardening.

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
