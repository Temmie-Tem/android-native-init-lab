# pm-service OFFLINE-exit is a SYMPTOM, not the blocker — causality handoff (2026-06-02)

**Out-of-band host-only review (no vNNN cycle, no device writes).** Read this
before continuing the V1616–V1630 pm-service / system-info track. It flags an
inverted-causality loop and redirects to the real blocker. It does NOT discard
the genuine findings of that track (listed below).

## What the loop has been doing (V1616–V1629)
Treating `pm-service` exiting cleanly (code 0) after publishing
`vendor.peripheral.SDX50M.state=OFFLINE` / `modem.state=OFFLINE`, before taking
Binder/PM fds, as the blocker — and chasing it through property-root,
shutdown-critical-list, system-info-surface, per_mgr nonstop-context, etc. Six
live test-boots (V1606/1610/1614/1619/1623/1627) all returned the SAME
`test-boot-no-downstream-wifi-progress-blocked`. V1630 proposes bind-mounting
**fake ONLINE** state files over the helper-private mdm3/subsys9 system-info
paths to make pm-service advance.

## Why that is inverted causality (STOP before V1630 fake-ONLINE)
`subsys9 = esoc0 = OFFLINING` is **a true fact, not a bug**. The SDX50M modem is
genuinely not powered up, so OFFLINE is correct, and `pm-service` publishing
OFFLINE then exiting is **correct behavior**. V1616 states the causality plainly:
Android-good keeps per_mgr/per_proxy alive **because** SDX50M/modem are ONLINE —
ONLINE is the cause, pm-service staying alive is the effect.

Faking ONLINE inverts that. Even if pm-service is tricked into proceeding, the
real modem is still dead, so the very next step (`/dev/subsys_esoc0` open →
`mdm_subsys_powerup` → wait for MDM2AP) blocks exactly as V849/V1238/V1552 already
proved. Net result: one more layer entered on a false premise, same wall, plus a
move away from this project's fact-based-observation principle into state
spoofing.

## This is a re-visit of an already-closed track
V1629's own inputs prove it: **V857** (pm-service property contract) and **V860**
(property superset, `property_denials.total=0`) already closed
"property-cleanup alone does not make pm-service hold subsystem nodes." V1621–
V1628 re-derived that same closed result via property-root / shutdown-list /
system-info and re-confirmed it with 6 BLOCKED boots. The property/system-info
input is not the lever.

## The real blocker (unchanged, cross-confirmed)
The modem (SDX50M) never completes power-on. Cross-confirmed:
- Host static analysis (2026-06-01, `ESOC_PROVIDER_STATIC_ANALYSIS_2026-06-01.md`):
  the eSoC provider is a built-in GPIO/ioctl shim; it asserts AP2MDM and waits
  for MDM2AP; it does NOT power the rail or PCIe/MHI.
- Loop's own V1552/V1556/V1559: native AP-side pcie1 power/refclk/PERST all
  proven, but **endpoint stays electrically silent** — GPIO104/WAKE=0,
  GPIO142/MDM2AP=0, IRQ252/IRQ290=0, no L0.
- V1559: Android asserts **GPIO135/AP2MDM after the esoc0 trigger and before
  BDF**; native never produces GPIO135/AP2MDM or any endpoint wake/status.

So `subsys9=OFFLINING` ← modem not booted ← **no MDM2AP/GPIO142 response** ←
(provider asserts AP2MDM but the modem side never answers). That last link is the
blocker, and it is BELOW pm-service, not inside its property/system-info input.

## Genuine findings to KEEP from V1586–V1629 (not discarded)
- V1586: software/firmware route (PM + firmware overlay) first produced
  `wlfw_progress=True` + firmware/PIL mounts — better than the forced-RC1 path.
- V1615/V1616: pm-service's clean exit is the normal OFFLINE-system-info path;
  the per_mgr/per_proxy lifetime mechanism is now well characterized.
- mdm_helper holds `/dev/esoc-0` (fd_count=1) and the subsys trigger gate opens.
These are real; only the "fix pm-service's offline decision" framing is wrong.

## Recommended redirect (read-only first; do NOT fake ONLINE)
The question is not "how do I make pm-service see ONLINE," but **"what asserts
GPIO142/MDM2AP — i.e. what actually powers/boots the SDX50M — and why does the
native AP2MDM(GPIO135) assertion not get an answer?"**
1. Android-positive recapture: on a known-good boot, what is the FIRST cause of
   `esoc0 -> ONLINE` / GPIO142 assert? Order: provider AP2MDM(GPIO135) assert →
   modem PBL → MDM2AP(GPIO142). Confirm whether Android does anything between
   GPIO135 and GPIO142 that native omits (PM8150L GPIO9 PON level/hold, a
   regulator, or a clock the EP needs before it can answer).
2. Native vs Android GPIO135/PM8150L-GPIO9 electrical parity: is native's
   AP2MDM/PON assertion actually reaching the modem at the right level/timing
   (`reset-time-ms`), or asserted-but-ineffective? (V1552 shows GPIO102/PERST
   toggles but GPIO135/AP2MDM count = 0 on the RC path.)
3. Only after the GPIO142/MDM2AP cause is understood, revisit the upper PM/WLFW
   path — which V1586 already shows will follow once the modem is actually up.

## Hard stops (unchanged)
No fake-ONLINE/system-info spoof as a way to advance pm-service; no PMIC/GPIO/GDSC
direct writes; no eSoC notify/BOOT_DONE spoof; no Wi-Fi HAL/scan/connect,
credentials, DHCP/routes, external ping; no flash/boot-image/partition write.
Keep everything read-only / source-build until the GPIO142 cause is classified.

## Host follow-up analysis (2026-06-02, DTS + provider strings + Android dmesg)

Done while the loop was paused, to push the redirect question as far as host data
allows. Results — one hypothesis REJECTED, three facts CONFIRMED, and the host
limit reached:

### REJECTED hypothesis (do not pursue): "GPIO9 PON MUX UNCLAIMED is the defect"
V1246 shows native PM8150L `gpio9` as `(MUX UNCLAIMED)`. This is NOT a native
defect: the Android positive-control V852 shows the SAME
`pin 7 (gpio9): (MUX UNCLAIMED)`. The PM8150L GPIO9 PON pad is not claimed by
kernel pinctrl on either side (handled at PMIC/bootloader level). Native also
claims the AP-side pins correctly — V1502/V1506 show
`pin 135/142: soc:qcom,mdm3`, identical to Android. So the AP-side GPIO
infrastructure is at parity; do not spend live cycles on GPIO9/pinctrl claim.

### CONFIRMED facts
1. On A90 (r3q overlay r03), the ONLY AP-controlled modem-power lever is
   `qcom,ap2mdm-soft-reset-gpio = <pm8150l_gpios 9>` (PON). There is NO board
   modem regulator-supply and NO `ap2mdm-pmic-pwr-en-gpio` populated (the
   provider has that code branch, but this board does not wire it). DTS itself is
   complete and correct; pinmux for GPIO135/141/142/53 is fully defined.
2. Android modem-boot order (V852 dmesg, exact): `8.541 __subsystem_get esoc0`
   → **+255 ms** → `8.796 PCIe Assert reset RC1` → `8.803 PHY ready / Release` →
   `8.820 LTSSM_L0 / link initialized GEN2 x2` → `11.582 sysmon-qmi esoc0 SSCTL`.
   The 255 ms window where the modem PON/PBL actually happens emits NO dmesg
   (`mdm_subsys_powerup` / "Powering on modem" / "MDM2AP went LOW" never print —
   it is hardware-level).
3. The native and Android PCIe-enable code paths are identical; native reaches
   PHY-ready + Release + LTSSM but stalls DETECT_QUIET→POLL_ACTIVE→
   POLL_COMPLIANCE→fail, while Android goes DETECT_QUIET→L0. The only difference
   is whether the endpoint (modem) is alive at PERST release.

### New discriminator for the next gate
Android does a NATURAL `__subsystem_get(esoc0)` at 8.541 s (subsystem framework
requests the modem), THEN 255 ms later PCIe enumerates and links. Native forces
RC1 enumerate directly without that preceding successful esoc0 powerup, so the
endpoint is dead at PERST. The question is not "fake ONLINE" or "more RC1
retries" but: **what makes Android's `__subsystem_get(esoc0)` actually power the
modem in that 255 ms, and can native reproduce that specific powerup (provider
`mdm_subsys_powerup` reaching a real modem PON) BEFORE attempting PCIe?**

### Host limit reached
Why the modem does not answer PON is hardware-level (PM8150L PON timing / PBL),
not present in any on-disk artifact. Further progress needs LIVE evidence: a
bounded native run that drives the provider's natural `__subsystem_get(esoc0)` /
`mdm_subsys_powerup` path (not forced RC1 enumerate) and captures whether MDM2AP/
GPIO142 ever responds — read-only/observational, still no PMIC/GPIO/GDSC write,
no fake-ONLINE, no eSoC notify/BOOT_DONE.

## Cross-refs
`ESOC_PROVIDER_STATIC_ANALYSIS_2026-06-01.md`, V1552/V1556/V1559 (endpoint
silence), V1616 (causality), V857/V860 (property track already closed),
V849/V1238 (mdm_subsys_powerup blocks on absent MDM2AP), V852 (Android modem-boot
dmesg timeline), V1246/V1502/V1506 (GPIO9/135/142 claim parity).
