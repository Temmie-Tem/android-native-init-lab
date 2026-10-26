# S22+ P463 USB HTTPS APT preparation

State: **H0 READY; DEVICE EXECUTION PENDING CURRENT ATTENDANCE**. This report covers the selected S22+ FYG8
capability and concrete H0 preparation. Device execution requires its own
fresh finite attended grant; P462 is consumed and closed. A90 and S20+ remain
outside this change.

## Bounded capability

P463 adds one authenticated HTTPS APT installation of Debian arm64
`tree=2.2.1-1` to the existing two-boot, four-writable-lifetime owner. It retains
P462's installed hello files, the cron lifecycle, one ordinary reboot, final
Download/original-A return and physical fallback. The second boot verifies
and runs tree without another download or installation. Success retains tree.

The [APT specialization](../operations/S22PLUS_DEBIAN_APT_V1.md) permits one
owned temporary NetworkManager USB share, including its managed DNS/DHCP/NAT
and forwarding. Exact profile ownership and host route/resolver checks precede
activation. Boot two reuses that same UUID. Cleanup follows original-A transfer
or stopped progress, so it cannot consume the automatic return window. Cleanup
proves profile and active-UUID absence; it does not independently prove every
NetworkManager-managed firewall/sysctl/DNS resource was retired.

Each boot accepts one SSH-authenticated run/phase/boot-bound numeric UTC
handoff before cron starts. Only CLOCK_REALTIME changes; RTC and persistent
clock configuration remain untouched. An exclusive intent and the original
deadline bound the operation. A lost reply allows status observation only.

APT_CONFIG redirects configuration, lists, cache, extended state and logs to
RAM before installed config fragments can load. Retained trust roots, TLS
peer/host validation, signature verification and date checks remain enabled.
Update and download run as the existing unprivileged _apt user without root
fallback. Exact signed metadata, the 57900-byte archive and the single-package
simulation must agree before the installation intent. No additional dependency,
upgrade or removal is admitted. The archive has no maintainer scripts,
conffiles, links or triggers, and does not activate an installed file trigger.

One root APT transaction may invoke its normal dpkg unpack/configure children.
PTY creation is disabled so the fixed process-group settlement remains valid.
The entire acquisition/package workload has a 90-second bound within the
original 300-second device boot deadline. Three real ARM64 measurements agree
on the exact successful state: 52 retained hello entries, ten new tree entries
and two database replacements. Status-old is the measured unpacked tree state;
other package paragraphs stay unchanged. The 64-row declaration rejects
missing, changed, linked or extra entries before and after reboot.

Completion requires settled child work, empty audit/verify output, no
transaction remnants, exact state and tree output, synchronization and an
authenticated record. Uncertain installation stops without package retry,
repair, removal or learned acceptance of partial state. Original A does not
undo package writes; it remains the existing attended Android recovery route.

## Android final health correction

P462's returned Android produced an exact same-serial device-disappeared error
at the root health read after an incomplete property capture. Only P463
final/recovery health now permits one complete replacement bracket for that
specific raw failure. All seven captures are fresh and must satisfy the same
health checks within the original 260-second budget and owner deadline.
An available prior boot identity must agree; missing identity is never
invented. The original failed evidence remains retained. Truncation alone,
timeout, corruption, ambiguity, wrong targets and arbitrary diagnostics still
stop. Initial/after-storage health, storage reads, controls and transfers do
not gain retry authority.

## Qualification

- Final physical-format A/B builds are byte-identical; the hook is a static
  AArch64 ELF and all 187 runtime/build inputs match current source bytes.
- The production ARM64 corpus passes all 71 cases: one complete two-boot
  scenario, 51 root/state cases and 19 runtime failures. The positive
  path uses real HTTPS/signature verification and APT, preserves the installed
  hello state, verifies tree across reboot and completes the fixed return
  control with the declared VM hardware substitution. Negative cases reach
  their selected fault branches and prove the corresponding stopped behavior.
- Focused host suites pass 41 related tests, six task tests and 48
  bridge/boundary tests. Sixteen focused qualifier tests pass after the narrow
  post-stop evidence correction. Touched Python compiles successfully.
- Original cold image admission passes from an unrelated working directory
  under isolated Python, without a preloaded build path. File writes, process,
  network and raw-command acquisition are denied during admission.
- Independent review returns PASS_GO for V3_REACHABLE_CAPABILITY with no open
  findings, bound to 164 task-source pins, 187 runtime sources and the exact
  final build, VM result and physical image. The reviewer independently
  rederives the entire corpus and actual archive/payload admission. Separate
  reviewed health, host-sharing, policy and persistent-bridge scopes are joined
  in that final review; they grant no device authority.

Final image receipt SHA-256:
`d2b2135fcfa3f0b1c3fedaee45f2051ac6342094c788b1dde5d05ddcfd4ae721`.
Independent capability review SHA-256:
`8b2f5e9feeb6df857df5ec1e0cdb7f491b03fb7da1d685435af8d02ba27c06cb`.
The new public capability binding is
[the P463 review](../../workspace/public/src/device-action/bindings/s22plus_debian_autoboot_p463_review.json);
prior reviews and consumed source snapshots retain their original identities.

Private evidence is retained under
`workspace/private/outputs/s22plus-debian-apt-p463-h0-20261027-1/`.
Early host-only failures remain preserved: the first physical-format package
selection omitted the new Download registration; the next VM route command
used an interface name that the existing virtual startup had already renamed.
The corrected source uses the established usb0 interface. These were H0
failures before any P463 phone transfer or grant. Separate negative controls
also reject historical false coverage where an earlier network failure never
reached the requested fault branch. The fourth corpus rejected an invalid H0
post-stop assumption: after the intentional package-corruption stop, direct
inode-table reads showed a zero inode while its exact configuration remained
in a committed, checksum-verified journal transaction. Independent read-only
journal analysis preserved that evidence without replay. APT failure cases now
claim only the selected failure and stopped execution, explicitly declining a
post-stop configuration-retention claim. The successful two-boot path remains
the exact retention criterion. Native device code was unchanged; the final
source-bound build and corpus were regenerated for the corrected H0 consumer.

## Execution boundary

The exact prepared task SHA-256 is
`835ad250d473dab358e73c6ae94414429a8daa27896d45accafaaf800749db24`.
It selects one `debian-autoboot` operation, at most 3600 seconds and attended
recovery. The host and runtime source snapshots match the reviewed capability.
Both phase constructors, the fixed eight-step sequence and rejection of
nonexecutable constructor data as a grant pass without command acquisition.

Independent concrete-entry review returns
`PASS_READY_H0_AND_UNEXECUTED_ENTRY`, SHA-256
`0c378be28e808fbb82c3d6d37471110955790b93d390a06d7af1c0d859d2a50b`.
The persisted original Controller accepts the bundle without approval; all nine
missing or mismatched approval fixtures are rejected. The once-only entry
retains the actual returned approval, no-existing-attempt, current source,
exact previous P462 closure, target and original-A requirements.

The fixed D0 baseline observed clean native_data M=38; it does not prove all
post-Android root contents. Fresh live Android health and both complete
protected root admissions remain execution checks. No approval has been saved,
no grant opened, and no P463 image transfer or installation has occurred on the
phone. The operator must supply the new finite grant and current attendance;
P462's consumed grant and ended attendance do not transfer.

H0 success proves the checked implementation and simulated producer/consumer
behavior. Physical USB internet, package persistence and final Android health
remain separate device outcomes. Automatic normal return does not establish
recovery from an unresponsive experimental kernel.
