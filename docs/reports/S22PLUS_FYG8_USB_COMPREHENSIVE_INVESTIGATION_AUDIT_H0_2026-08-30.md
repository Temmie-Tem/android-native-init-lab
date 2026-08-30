# S22+ FYG8 USB 총조사 및 증거 점검 리포트 (H0)

Date: 2026-08-30 KST

Target: **Samsung Galaxy S22+ `SM-S906N` / `g0q` /
`S906NKSS7FYG8`**

Status: **H0 evidence synthesis; no device or live authority**

Formal current live verdict:
**`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`**

This report is a host-only synthesis of the repository, retained private run
evidence, exact-target source/artifact audits, and web primary sources. It is
not a new candidate qualification, `PASS_GO`, D0/D1/F1 approval, recovery
authority, or replay authority. No device, ADB, USB, Odin, reboot, module,
sysfs, configfs, partition, or hardware action was performed while producing
it. A90 and S20+ identities, commands, artifacts, evidence, and authority were
not used or changed.

## 1. Executive conclusion

The formal P3.19 result does **not** localize the current S22+ USB problem to
the connector, MAX77705 MUX, PHY, DWC3, UDC, configfs, cable, or host. An
additive H0 reconstruction strongly locates the stop much earlier, immediately
after the first stock module row in the post-load `/dev/kmsg` drain/observer
path. This is a `SUPPORTED` post-live interpretation, not a rewritten formal
result. On that interpretation, the run did not execute the current USB
experiment far enough to test the USB stack.

The most important conclusions are:

1. The exact P3.19 candidate and rollback each transferred exactly once. The
   journal is `CLOSED`, rollback and final rooted FYG8 Android health are
   verified, and `recovery_required=false`. The candidate is consumed and may
   never be replayed.
2. The top-level formal verdict remains
   `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`; its formal observer proof class is
   `NO_PROOF_OBSERVER`. The frozen adapter reported
   `AMBIGUOUS_INTEGRITY_FAILURE`, `stock-envelope-shape`, and
   `[valid,bad-body]`. Neither formal field may be rewritten after the fact.
3. H0 structural reconstruction shows that both retained Carrier slots have
   valid CRCs and canonical padding. They encode generation 10 progress at
   item 1 and generation 11 failure at item 2 with detail `0x6020`. The
   apparent `bad-body` is semantic allowlist rejection, not demonstrated byte
   corruption.
4. The last firm execution progress is row 1, `qcom_hwspinlock.ko`. The
   failure was published at the next checkpoint position, row 2
   (`smem.ko`), but the exact control flow places the strongest failure site
   in the row-1 post-load kmsg drain. **It is not proved that `smem.ko` was
   attempted or failed.**
5. `0x6020` is defined by the candidate as a witness-grammar contradiction,
   and the exact positive-return path is the one-terminal-newline body check.
   However, the same numeric value collides with the older publication-close
   error namespace (`0x6000 + errno 32`). Context supports a kmsg body-shape
   failure, while the absent offending record prevents a unique subclass
   diagnosis.
6. Linux's official `/dev/kmsg` ABI permits continuation dictionary lines,
   future extra header fields, and fragmented records. The P3.19 parser
   deliberately rejects dictionary lines and requires exactly one newline.
   It can therefore reject ABI-valid kernel output. A dictionary/continuation
   record is the leading explanation, but remains a hypothesis because the
   rejected record bytes were not retained.
7. The host USB trace sidecar was requested for 900 seconds but ran only
   16.881 seconds. It ended 0.341 seconds after candidate flash completion and
   57.639 seconds before candidate boot-ready. It did not cover the intended
   observation window through boot-ready, so it cannot support a candidate
   enumeration or silence claim; the host axis is correctly `UNKNOWN`.
8. Earlier artifact-specific campaigns proved substantial USB progress:
   SSUSB/DWC3 bind, exact UDC publication, configfs UDC bind, zero-return
   software pull-up/RUN_STOP calls, and stable `not attached` observations.
   Those facts are valuable history but do not transfer into the newly built
   P3.19 candidate.
9. The current exact 73-row P3.19 plan is statically closed: 73 rows, 110
   declared dependency edges, zero missing/order violations, and 3,566 closed
   imports. Dynamic module execution, supplier bind, DWC3 probe, UDC creation,
   gadget bind, pull-up, and host attach remain unproved in the latest run.
10. The safest next unit is not another flash or hardware intervention. It is
    an H0 repair of the observer contract, failure evidence, detail namespace,
    and sidecar lifecycle, followed by hostile qualification and independent
    review. Only a **new** candidate with fresh authority may later test the
    USB chain.

## 2. Scope, authority, and method

### 2.1 Binding authority

The governing documents are, in order:

1. `AGENTS.md`;
2. `docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md`;
3. `docs/operations/DEVICE_ACTION_RISK_TIERS.md`;
4. `docs/operations/DEVICE_ACTION_PROCESS_V2.md`.

`GOAL.md`, reports, manifests, hashes, tests, reviews, and this document report
state; none grants standing device authority. Candidate replay is forbidden
after the first candidate effect, and recovery proceeds only from the durable
journal.

### 2.2 Evidence classes used here

| Class | Meaning in this report |
|---|---|
| `PROVED` | Directly established by exact retained bytes, exact source/control flow, a current structured result, or a named reviewed artifact closure. |
| `SUPPORTED` | Multiple exact facts support the inference, but the run did not retain a unique discriminating witness. |
| `HYPOTHESIS` | Plausible and source-real, but not selected by discriminating runtime evidence. |
| `UNKNOWN` | Evidence is absent, ambiguous, stopped before the layer, or was not retained. |
| `REFUTED` | A precise hypothesis or expected result is contradicted by valid evidence. |

These evidence classes are separate from Process-v2 terminal spellings such as
`NO_PROOF_OBSERVER`, `NO_PROOF_EXPERIMENT_PRECONDITION`, and
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`.

### 2.3 Repository census

The initial clean checkout was `main` at `2d6d497050`, 30 commits ahead of
`origin/main`. Before adding this report, the H0 inventory counted:

| Surface | Count |
|---|---:|
| S22+-named reports | 685 |
| phased FYG8 reports | 209 |
| S22+ public scripts | 909 |
| S22+ test files | 361 |
| S22+-labelled commits across refs | 611 |
| tracked S22 documents matching USB/DWC3/UDC/MAX77705/Type-C/gadget/ACM terms | 479 |

The report does not restate every historical file. It uses the canonical
ledger and evidence index to compress repeated preparation/review units, then
expands only the load-bearing USB transitions, current evidence, contradictions,
and open questions.

### 2.4 Evidence precedence

For this synthesis, evidence was weighted as follows:

1. current binding contracts and the durable live result;
2. raw retained bytes and exact source/artifact identity;
3. independently reviewed host closures tied to those bytes;
4. current target goal/ledger summaries;
5. official Linux, AOSP, Samsung, and regulatory web sources;
6. secondary service-document indexes;
7. analogy from upstream or other board variants.

An older report, another candidate, stock Android, recovery, Download mode,
upstream Qualcomm code, or an E/U schematic cannot silently replace exact
P3.19/S906N evidence.

## 3. USB system model

The useful diagnostic chain is not simply “USB works or does not work.” It is:

```text
ROLE CONTROL PLANE (one selected source)
  stock: firmware -> PMIC GLINK -> UCSI -> usb_role_switch
  direct: a600000.ssusb mode=peripheral
        |
        v
Qualcomm SSUSB parent -> DWC3 child -> UDC -> configfs UDC bind
        |                                      |
        |                                      v
        |                         gadget pull-up / DCTL RUN_STOP
        |                                      |
        +----------------------+---------------+
                               |
USB2 DATA PLANE                v
  DWC3/HS PHY <-> MAX77705 CONTROL1 MUX <-> USB-C connector/cable/host
                                                   ^
ATTACH INPUTS: VBUS + CC/orientation/policy --------+
                               |
                               v
physical attach -> reset -> address -> configured -> negotiated speed
                               |
                               v
host enumeration -> cdc_acm endpoint -> framed request/response
```

Each arrow is a separate claim. A successful sysfs write, module load, driver
bind, UDC directory, configfs `UDC` readback, zero return from RUN_STOP, host
event, tty node, and framed byte exchange prove different layers.

### 3.1 Exact-target static architecture

The current exact Image advertises built-in USB, gadget, DWC3 dual-role,
role-switch, Type-C, and UCSI support. The shipped `dwc3-msm.ko` has
relocation-backed call edges:

```text
mode_store -> dwc3_msm_set_role
dwc3_msm_set_role -> dwc3_ext_event_notify
dwc3_msm_usb_role_switch_set_role -> dwc3_msm_set_role
dwc3_msm_probe -> usb_role_switch_register
dwc3_otg_start_peripheral -> usb_gadget_connect
```

This proves that the direct `mode=peripheral` recovery-style path is a real
software path independent of successful natural UCSI role selection. It does
not prove that the exact P3.19 platform driver bound or that the calls ran.

### 3.2 MAX77705 and role separation

The exact FYG8 source audit separates two responsibilities:

- UCSI/GLINK is the stock software role-producer path;
- MAX77705 `CONTROL1` selects the USB2 D+/D- analog path.

Source binds `COM_OPEN=0x3f` and `COM_USB=0x09`. A register command/readback
proves the software transaction, not physical switch contact continuity at the
connector. Conversely, a correct device role does not prove the analog path.

### 3.3 Exact 73-row P3.19 module plan

The plan is reproduced here because it is the current static execution order:

```text
00 s22plus_dwc3_event_latch.ko  01 qcom_hwspinlock.ko  02 smem.ko
03 minidump.ko  04 qcom-scm.ko  05 qcom_wdt_core.ko  06 gh_virt_wdt.ko
07 cmd-db.ko  08 debug-regulator.ko  09 icc-debug.ko  10 iommu-logger.ko
11 phy-generic.ko  12 proxy-consumer.ko  13 gdsc-regulator.ko
14 clk-qcom.ko  15 clk-dummy.ko  16 gcc-waipio.ko  17 qcom_iommu_util.ko
18 qnoc-qos.ko  19 sec_class.ko  20 abc.ko  21 sec_debug.ko
22 secure_buffer.ko  23 qcom_ipc_logging.ko  24 qcom-pdc.ko
25 pinctrl-msm.ko  26 pinctrl-waipio.ko  27 qcom_rpmh.ko  28 clk-rpmh.ko
29 rpmh-regulator.ko  30 icc-bcm-voter.ko  31 qrtr.ko  32 socinfo.ko
33 icc-rpmh.ko  34 dispcc-waipio.ko  35 qnoc-waipio.ko  36 arm_smmu.ko
37 qmi_helpers.ko  38 eud.ko  39 phy-msm-ssusb-qmp.ko  40 repeater.ko
41 redriver.ko  42 usb_notify_layer.ko  43 qcom_glink.ko
44 qcom_glink_smem.ko  45 qcom_smd.ko  46 rproc_qcom_common.ko
47 pdr_interface.ko  48 pmic_glink.ko  49 switch_class.ko
50 common_muic.ko  51 vbus_notifier.ko  52 if_cb_manager.ko
53 pdic_notifier_module.ko  54 usb_typec_manager.ko
55 usb_f_ss_mon_gadget.ko  56 phy-msm-snps-hs.ko  57 phy-msm-snps-eusb2.ko
58 qc_usb_audio.ko  59 dwc3-msm.ko  60 usb_notifier_qcom.ko
61 ucsi_glink.ko  62 spmi-pmic-arb.ko  63 pinctrl-spmi-gpio.ko
64 qti-regmap-debugfs.ko  65 regmap-spmi.ko  66 qcom-spmi-pmic.ko
67 msm-geni-se.ko  68 gpi.ko  69 i2c-msm-geni.ko  70 spu_verify.ko
71 mfd_max77705.ko  72 pdic_max77705.ko
```

Static closure proves:

| Check | Result |
|---|---:|
| plan rows | 73: 1 custom + 72 exact vendor modules |
| declared dependency edges | 110 |
| missing declared dependencies | 0 |
| dependency-order violations | 0 |
| imports | 3,566: 3,238 from Image + 328 from earlier modules |
| missing / ambiguous / duplicate providers | 0 / 0 / 0 |
| candidate vendor rows found in recovery list | 72 / 72 |
| candidate module bytes matching vendor ramdisk | 72 / 72 |

The final runtime gates are parent bind, child bind, and exact UDC publication:

```text
10 /sys/bus/platform/drivers/msm-dwc3/a600000.ssusb
11 /sys/bus/platform/drivers/dwc3/a600000.dwc3
12 /sys/class/udc/a600000.dwc3
```

Static completeness removes the broad “add another USB module” explanation.
It cannot prove that a supplier bound, `dwc3_msm_probe()` succeeded, the child
appeared, or the UDC was published.

## 4. Historical USB evidence chronology

### 4.1 Stock and early-service positive controls

Stock Android O0 and early-service O1.1 each completed 128 framed ACM exchanges
with CRC validation. At those exact times and setups, the phone connector,
cable/host path, stock gadget stack, and framed transport could operate.

Direct-PID1 O3F/M34 candidates did not expose ACM, but their internal endpoint
was not retained. Those misses do not prove that native USB is impossible.

Status:

- stock/early Android framed ACM: `PROVED`, control-condition-specific;
- permanent host/cable inability: `REFUTED` for those controls;
- native candidate root cause: `UNKNOWN`.

### 4.2 Retained evidence and PID1 foundation

The Samsung current ring to next-boot `/proc/last_kmsg` retention path became
the durable observer. Source-matched rebuilt kernel Android boot and acceptance
of `kernel_execve("/init")` while PID1 were established. Ramoops/pstore was
refuted as a reliable observer for the relevant reset path. Acceptance of the
exec transition did not by itself prove the first userspace instruction.

This history explains why a parser defect is a primary experiment failure: the
retained channel is the only durable source for many candidate-side states.

### 4.3 Module to SSUSB, DWC3, and UDC ladder

| Unit | Evidence retained | Correct interpretation |
|---|---|---|
| P2.57 | exact modules and gates through SSUSB and DWC3 child bind | DWC3 child bind `PROVED`; the UDC singleton predicate was defective, so UDC absence was not proved. |
| P2.58A | exact `a600000.dwc3` UDC membership and terminal sequence | exact UDC publication `PROVED`; host transport still separate. |
| P2.76 | configfs, gadget, `ttyGS0`, banner queue, role readback, UDC bind/readback | the UDC did not reach `configured/high-speed` within the deadline; host trace was absent. |
| P2.80 | parent/child runtime-PM success, pull-up entry/return, nested RUN_STOP return, controller running | state remained `not attached`; software completion did not prove electrical attach. |
| P2.92 | restart, PHY/power, notify-connect, role, UDC, bind, and final sampling | stable final `not attached/UNKNOWN`; narrowed failure after direct RUN_STOP. |
| P2.94 | external wrapper telemetry design | required external `dwc3-msm.ko` delivery was statically unavailable; not a valid runtime discriminator. |
| P2.96 | built-in DWC3 telemetry | `USBLNKST=0`, `not attached/UNKNOWN`, `COREIDLE=1`, `SUSPHY=0`; intended attach result `REFUTED`. |

Every listed candidate was independently consumed. Its result may guide a new
design, but its runtime proof does not transfer to P3.19 bytes.

### 4.4 Event, PHY, and cycle attribution

P2.98 through P3.15 progressively separated gadget start, endpoint enable,
event ingress/subtype, HS-PHY clocks, role/QSCRATCH, restart, and worker-cycle
geometry.

- P3.12 refuted the specific “missing HS-PHY ref clocks” explanation.
- P3.15 proved the restart-side functional witness bundle, including RUN_STOP
  and several digital states.
- P3.15 simultaneously refuted the expected clean four-outer-worker model: the
  retained final tuple showed eight completed outer-work pairs.
- Because the multiplicity contract revoked clean-cycle causality, P3.15 did
  not prove whether a pull-up reached the connector or which external source
  queued the additional work.

### 4.5 MAX77705/MUIC investigations

| Unit | Retained result | Effective class |
|---|---|---|
| P3.16 | Max77705 parent existed unbound after diagnostic module registration | `NO_PROOF_EXPERIMENT_PRECONDITION`; no CONTROL1 experiment ran. |
| P3.17 | software path recorded `0x3f -> 0x09 -> 0x09`; candidate endpoint later appeared on a physically moved connection | topology precondition changed, so causal MUX result is unavailable. |
| P3.18 | EUD plan index shifted from 37 to 38 while trigger stayed stale | Max77705 was never reached; `NO_PROOF_EXPERIMENT_PRECONDITION`. |

The source-level `CONTROL1` semantics are `PROVED`; physical contact
continuity and a causal MUX explanation are still `UNKNOWN`.

### 4.6 P3.19 reconstruction and preparation

P3.19 changed the strategy from repeated late electrical hypotheses to an
exact stock-path reconstruction:

- exact stock role path and direct-role alternative;
- exact 73-row module plan;
- materialized source/artifact identities;
- observer/result-contract arming;
- D1/D0 V3 fresh baseline;
- global consumed-candidate registry;
- Process-v2 adapter and offline-ready closure;
- a repaired runtime-bound prepared record.

Those host capabilities passed their scoped reviews. They did not predict that
the new kmsg parser would reject a real early-boot record before the USB plan
could execute.

## 5. Latest P3.19 live result: formal record

The authoritative private result is:

`workspace/private/runs/device-action-f1-live-v2/`
`f1-2026-08-30T082903022444Z-1788078543022472744/live-result.json`

### 5.1 Transaction and health

| Field | Result | Class |
|---|---|---|
| transaction | `CLOSED`, 19 journal records | `PROVED` |
| candidate | completed once | `PROVED` |
| rollback | completed once and verified | `PROVED` |
| final target health | rooted, boot-completed FYG8 Android; bound boot/supporting-partition health; Download absent | `PROVED` |
| recovery required | false | `PROVED` |
| replay/retransmission | none | `PROVED` |
| formal verdict | `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` | immutable run result |

The global candidate claim exists. This exact candidate/AP is not a candidate
for another run.

### 5.2 Frozen observer result

The two post-rollback reads are each 2,097,136 bytes, read to EOF with empty
stderr, byte-identical, and SHA-256 identical. The current frozen adapter
reported:

```text
classification = AMBIGUOUS_INTEGRITY_FAILURE
integrity_issue = stock-envelope-shape
slot_status     = [valid, bad-body]
proof_class     = NO_PROOF_OBSERVER
candidate_success = false
causal_result_allowed = false
host_silent_claimable = false
mux_result_claimable = false
```

The P3.19 stock decoder accepts only the final generations 106/107 `MXD5`
stock-witness pair, so generations 10/11 form an incomplete/foreign stock pair.
Separately, the generic Carrier fallback decodes those early slots through the
legacy P2.94 semantic validator; that layer converts the structurally valid
generation-11 slot to `bad-body`. The adapter then records the combined
`stock-envelope-shape` failure. These are two different rejection layers.

## 6. Additive H0 Carrier reconstruction

This section adds forensic facts without altering the formal result.

### 6.1 Structural slots

The unique 192-byte Carrier at retained offset 1,659,990 has:

| Component | Reconstructed value | Result |
|---|---|---|
| header CRC | recorded equals calculated | valid |
| slot 0 CRC | recorded equals calculated | valid |
| slot 0 | generation 10, stage `0x41`, progress, item 1, detail 0 | canonical |
| slot 1 CRC | recorded equals calculated | valid |
| slot 1 | generation 11, stage `0x42`, failure, item 2, detail `0x6020` | structurally canonical |
| slot 1 reserved/padding | zero/canonical | valid |

The old Carrier model decodes a slot structurally, then validates it against
the P2.94 semantic rules. That rule rejects an otherwise canonical detail at or
above `0x0c00` if it is outside the declared route and returns `bad-body`.
Thus:

```text
CRC/body corruption:       not demonstrated
semantic-domain mismatch:  PROVED
formal observer acceptance: false
```

The successor decoder must retain separate states such as
`STRUCTURALLY_VALID_SEMANTIC_OUT_OF_DOMAIN`; it must not relabel the historical
run.

### 6.2 Execution location

For the direct-loop row at issue here (row 1), the candidate loads and verifies
the module, publishes its progress checkpoint, notes successful module state,
increments its module count, and then drains `/dev/kmsg`. A nonzero drain
result returns to the caller and is published at the next failure checkpoint.
Rows 59-72 later use a folded path and are not generalized by this sentence.

The precise conclusion is:

- row 1 `qcom_hwspinlock.ko` completion/progress is the last retained success;
- item 2 is the next checkpoint position associated with `smem.ko`;
- exact control flow strongly locates the error in the row-1 post-load kmsg
  drain;
- it is **not established** that row 2 `smem.ko` was loaded, attempted, or
  failed.

Therefore P3.19 did not reach:

- EUD row 38;
- any USB PHY rows 39, 40, 41, 56, or 57;
- `dwc3-msm.ko` row 59;
- UCSI row 61;
- GENI/I2C rows 67-69;
- MAX77705 rows 71-72;
- parent/child/UDC gates;
- configfs, gadget bind, pull-up, or host attach.

Calling this run a “MAX77705 failure,” “DWC3 failure,” “UDC failure,” “MUX
failure,” “cable failure,” or “host silence” would exceed the evidence.

## 7. `0x6020` and `/dev/kmsg` observer audit

### 7.1 Candidate definition and namespace collision

The P3.19 witness parser defines:

```text
0x6020 witness grammar contradiction
0x6021 witness counter overflow
0x6022 witness boundary
```

But the inherited checkpoint client also reserves:

```text
0x4000 publication open error base
0x5000 publication write error base
0x6000 publication close error base
```

with an errno span. Therefore `0x6020` also aliases “publication close base +
errno 32.” A value-only decoder cannot safely choose between the meanings.

The exact execution location and signed-return flow make the kmsg path the
stronger interpretation here:

- known-witness grammar helpers return negative `-0x6020`, which the inherited
  normalization path does not accept as a normal errno-like return;
- the exact record-body boundary path returns positive `+0x6020` when it does
  not find one and only one terminal newline;
- the failure appears immediately after a successful module row at the
  post-load drain location.

This is `SUPPORTED`, not a unique byte-level proof, because the rejected record
was not retained.

### 7.2 Current parser assumptions

The current Python and generated C parser require:

- a fixed extended header shape;
- only the expected `c` or `-` flag and optional caller field;
- no unknown comma fields;
- exactly one terminal newline;
- no interior newline;
- no dictionary continuation lines.

The builder itself records `dictionary_lines = fail-closed (not parsed by this
predecessor)`.

### 7.3 Official Linux ABI mismatch

The Linux [`/dev/kmsg` ABI](https://www.kernel.org/doc/Documentation/ABI/testing/dev-kmsg)
states that:

- one read returns one whole ring-buffer record;
- the prefix contains priority/facility, sequence, monotonic timestamp, and
  flags;
- future comma-separated fields may appear before `;` and unknown fields must
  be ignored gracefully;
- a line beginning with a space is a valid continuation dictionary entry;
- `SUBSYSTEM=` and `DEVICE=` are official examples;
- a `c` flag denotes a fragment and consumers should handle possible
  fragmentation/interleaving;
- ring overwrite is reported through `-EPIPE`.

The exact FYG8 `printk.c` retained by the project can append newline-terminated
`SUBSYSTEM` and `DEVICE` metadata after messages that carry `dev_info`. Thus a
multi-line read is not automatically corruption.

### 7.4 What is and is not known

| Claim | Status | Reason |
|---|---|---|
| the P3.19 observer rejected an early record | `SUPPORTED` strongly | exact position, detail, and control flow converge. |
| the record violated the parser's one-newline rule | `SUPPORTED` strongly | positive `0x6020` path and execution location. |
| the record contained a dictionary continuation | `HYPOTHESIS` | ABI and exact printk producer permit it, but rejected bytes were not retained. |
| the precise offending record, source, and sequence | `UNKNOWN` | no failure excerpt/hash/length receipt identifies it. |
| the Carrier bytes were corrupt | `REFUTED` for CRC/padding | both slots are structurally valid. |

## 8. Host sidecar audit

The private sidecar receipt records:

| Measurement | Value |
|---|---:|
| requested duration | 900 s |
| actual duration | 16.881081 s |
| fraction of request | 1.876% |
| stop signal | `SIGTERM` |
| stop after candidate flash completed | 0.341052 s |
| stop before candidate boot-ready | 57.639096 s |

Kernel and udev collectors were alive before the stop and their bounded raw
captures were preserved privately. Nevertheless, their window ended before it
covered the intended observation interval through candidate boot-ready. The
final result therefore correctly records:

```text
status = unknown
reason = recovery:interrupted-candidate-window
host_axis = UNKNOWN
```

The receipt establishes the premature end and signal; it does **not** identify
the external reason the parent process entered that termination path. That
cause remains `UNKNOWN`.

No future sidecar may cause or justify candidate replay. It must be journaled
and adoptable/reconcilable across a host-process cut so that observation can
resume without repeating a device effect.

## 9. Layer-by-layer current state

| Layer / claim | Historical exact evidence | Latest P3.19 evidence | Current status |
|---|---|---|---|
| exact target and final health | repeated FYG8 identity/health closure | final rooted FYG8 health verified | `PROVED` for final rollback state |
| stock connector/cable/host/gadget | 128-frame stock and early-service ACM controls | not tested in candidate window | `PROVED` only for controls |
| retained `/proc/last_kmsg` channel | repeated full, byte-identical reads | two identical EOF reads | `PROVED` |
| Carrier integrity | many earlier exact records | header and two slot CRCs valid | `PROVED` structurally |
| observer semantic coverage | earlier phase-specific decoders | rejects early valid P3.19 detail as bad-body | `REFUTED` as complete coverage |
| observer Linux kmsg compatibility | not previously discriminated | fixed header/one-line assumptions conflict with ABI | `REFUTED` as ABI-complete |
| row 1 module progress | other artifacts reached much later | row 1 progress retained | `PROVED` |
| row 2 `smem.ko` execution | historically available | stopped at next position before proof | `UNKNOWN` |
| all 73 modules | static closure only | stopped after row 1 | `UNKNOWN` runtime |
| SSUSB parent bind | proved in earlier candidate artifacts | not reached | `UNKNOWN` for P3.19 |
| DWC3 child bind | proved by P2.57 artifact | not reached | `UNKNOWN` for P3.19 |
| exact UDC publication | proved by P2.58A artifact | not reached | `UNKNOWN` for P3.19 |
| configfs gadget and UDC bind | proved by P2.76 artifact | not reached | `UNKNOWN` for P3.19 |
| pull-up / RUN_STOP | proved as software path by P2.80/P2.92 | not reached | `UNKNOWN` for P3.19 |
| UDC attached/configured/speed | earlier remained not-attached/UNKNOWN | not reached | `UNKNOWN` for P3.19 |
| natural UCSI role path | source/firmware structure audited | not reached; complete runtime producer still unproved | `SUPPORTED` static, `UNKNOWN` live |
| direct `mode=peripheral` path | source and stock recovery design shape | not reached | `PROVED` static, `UNKNOWN` live |
| MAX77705 CONTROL1 software path | source and prior command path | not reached | `PROVED` static, `UNKNOWN` current live |
| physical MUX continuity | no exact causal observation | not reached | `UNKNOWN` |
| physical host attach | prior P3.17 confounded by moved topology | sidecar missed window | `UNKNOWN` |
| candidate ACM endpoint and bytes | none accepted in native PID1 lineage | not observed | `UNKNOWN`; not proved absent |

## 10. Hypothesis ledger

### 10.1 Highest-priority current explanation

**ABI-valid `/dev/kmsg` record rejected by an over-strict parser** —
`SUPPORTED` at the broad class, `HYPOTHESIS` at the dictionary-line subclass.

Supporting facts:

- early checkpoint and `0x6020`;
- exact post-load drain location;
- one-newline-only positive error path;
- explicit dictionary-line rejection;
- official ABI and exact FYG8 printk support for continuation metadata;
- structurally valid Carrier bytes.

Missing discriminator:

- exact rejected record bytes, length, sequence, flags, and bounded excerpt.

### 10.2 Body-shape explanations and separate compatibility gaps

| Hypothesis | Status | Discriminator |
|---|---|---|
| dictionary continuation or missing/trailing/multiple newline | `HYPOTHESIS` for the observed positive `0x6020` | retain the exact failing record. |
| extra future header field rejected | known compatibility gap, not a direct explanation for observed positive `0x6020` | exercise the negative-return path with an official extra-field fixture. |
| fragmented/interleaved record mishandled | known compatibility risk, not a selected explanation for observed positive `0x6020` | retain flags/sequence/read boundaries and exercise fragment/interleave fixtures. |
| old semantic allowlist caused formal `bad-body` | `PROVED` | structural decode passes; P2.94 semantic validation rejects detail. |
| sidecar ended before useful window | `PROVED` | exact timestamps and SIGTERM receipt. |
| why the sidecar parent terminated it | `UNKNOWN` | no causal parent-exit receipt. |

### 10.3 USB hypotheses not tested by the latest run

| Hypothesis | Present evidence state |
|---|---|
| missing current-plan module/dependency | broad static explanation `REFUTED`; runtime bind can still fail. |
| incomplete natural UCSI producer | source-real gap/alternative, but direct-role path exists and latest run did not reach either. |
| EUD/spoof-disconnect suppresses session validity | source-real `HYPOTHESIS`; not executed in latest run. |
| MAX77705 remains `COM_OPEN` or fails physical switching | `UNKNOWN`; latest run did not reach MAX77705. |
| HS-PHY ref-clock failure | specific prior hypothesis `REFUTED` by P3.12; unrelated later PHY failures remain possible. |
| DWC3 RUN_STOP software failure | refuted for earlier artifacts, `UNKNOWN` for P3.19 because not reached. |
| permanent cable/host fault | inconsistent with stock controls; current phase-specific connection still requires a live witness. |

## 11. Web and external-source cross-check

All links in this section were checked on 2026-08-30. Web evidence does not
replace the exact retained FYG8 source or a candidate run.

### 11.1 Exact Samsung target

- [Samsung SM-S906N support page](https://www.samsung.com/sec/support/model/SM-S906NLBWKOO/)
  identifies the Korean Galaxy S22+ model and specifies USB Type-C / USB 3.2
  Gen 1. It does not expose internal D+/D-, CC, SBU, or MAX77705 nets.
- [Samsung Open Source Release Center FYG8 search](https://opensource.samsung.com/uploadSearch?searchValue=S906NKSS7FYG8)
  displayed one exact result containing `SM-S906N` and the exact FYG8 source
  archive name during an interactive browser observation. The dynamic result
  is not a pinned local receipt. The download dialog is hCaptcha-gated, so
  archive bytes and contents were not re-downloaded or re-verified in this web
  pass; exact source claims in this report continue to rely on the repository's
  retained, hash-bound provenance.
- The [Korean regulator SAR listing](https://www.rra.go.kr/en/sar/value.do?cpage=61&maker_en=&model=)
  corroborates the commercial model identity but contains no USB net evidence.

### 11.2 Linux gadget and UDC state model

- [configfs gadget ABI](https://www.kernel.org/doc/Documentation/ABI/testing/configfs-usb-gadget)
  and the [configfs gadget guide](https://docs.kernel.org/usb/gadget_configfs.html)
  define gadget construction followed by writing a UDC name to `UDC` to bind;
  an empty value unbinds.
- [UDC sysfs ABI](https://www.kernel.org/doc/Documentation/ABI/stable/sysfs-class-udc)
  distinguishes the current gadget driver, negotiated speed, states from
  `not-attached` through `configured`, and `soft_connect` pull-up control.
- [Linux gadget lifecycle](https://docs.kernel.org/driver-api/usb/gadget.html#driver-life-cycle)
  separates gadget-driver bind from pull-up/VBUS detection and subsequent host
  reset/address/configuration.
- Permanent upstream source links show
  [configfs UDC store](https://github.com/torvalds/linux/blob/08dbfad3f5040f5bdb6c529da20d6d4e81fefd72/drivers/usb/gadget/configfs.c#L242-L311),
  [UDC bind and pull-up](https://github.com/torvalds/linux/blob/08dbfad3f5040f5bdb6c529da20d6d4e81fefd72/drivers/usb/gadget/udc/core.c#L707-L761),
  [DWC3 RUN_STOP/pull-up](https://github.com/torvalds/linux/blob/08dbfad3f5040f5bdb6c529da20d6d4e81fefd72/drivers/usb/dwc3/gadget.c#L2618-L2839),
  and [Connect Done/speed selection](https://github.com/torvalds/linux/blob/08dbfad3f5040f5bdb6c529da20d6d4e81fefd72/drivers/usb/dwc3/gadget.c#L4223-L4299).

The external sources confirm the project's evidence taxonomy: a nonempty UDC
binding is not proof of physical attach, enumeration, or configuration.

### 11.3 Role and Type-C state

- [USB role-switch ABI](https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-usb_role)
  defines `none`, `host`, and `device`, and directs Type-C role changes to the
  Type-C connector ABI.
- [Type-C class ABI](https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-typec)
  separates data role, power role, and CC orientation.
- Upstream [DWC3 role mapping](https://github.com/torvalds/linux/blob/08dbfad3f5040f5bdb6c529da20d6d4e81fefd72/drivers/usb/dwc3/drd.c#L448-L539)
  maps device role into DWC3 device port capability.
- Upstream [Qualcomm DWC3 glue](https://github.com/torvalds/linux/blob/08dbfad3f5040f5bdb6c529da20d6d4e81fefd72/drivers/usb/dwc3/dwc3-qcom.c#L561-L608)
  documents a generic QSCRATCH/VBUS-valid concern around a later UDC write
  after autosuspend.
- Upstream [PMIC GLINK configuration](https://github.com/torvalds/linux/blob/08dbfad3f5040f5bdb6c529da20d6d4e81fefd72/drivers/soc/qcom/Kconfig#L105-L123)
  describes coprocessor firmware access to USB/battery state.

The last two links are generic/upstream support only. They do not prove that
the exact FYG8 kernel took the same runtime path.

### 11.4 Android implementation comparison

- [AOSP USB HAL documentation](https://source.android.com/docs/core/permissions/usb-hal)
  explains the native USB daemon/HAL boundary and historical sysfs-write error
  propagation concerns.
- AOSP's [USB Gadget implementation](https://android.googlesource.com/platform/hardware/interfaces/+/1a56e38edc2f2f6189ef405ee1edce554e15cbc0/usb/gadget/1.2/default/UsbGadget.cpp)
  illustrates FunctionFS readiness, UDC pull-down/up, and speed observation.

AOSP uses vendor-era conventions that can differ from the upstream configfs
ABI. This is a reason to check exact FYG8 source, not to substitute AOSP
behavior for the device.

### 11.5 Schematic and board evidence

No official exact `SM-S906N` net-level schematic was obtained in this pass.
That means **“official public N-board schematic not found,” not “no schematic
exists.”**

Current source states are:

| Source class | State | Allowed use |
|---|---|---|
| official exact S906N product/source listing | verified | model/build/source provenance only |
| exact S906N net schematic | not obtained | no net claim |
| S906E/U service-schematic indexes | indexed, access/variant barriers | proxy-only |
| [SM-S906B repair guide](https://images.samsung.com/is/content/samsung/assets/mx/support/self-repair/guides/s22/SM-S906B_RepairGuide_Open_Spa_Rev.1.0_230616.pdf) | public other-variant repair material | mechanical reference only, not N-board nets |
| app-protocol/login/payment-gated mirrors | not acquired | no executable/viewer recommendation |

If an exact artifact is later obtained safely, it must first establish title
block, PCB revision, and N-board commonality. Only then should it trace:

- UID/RID to CC/SBU/connector/test pads;
- MAX77705 `COMN1SW`/`COMP2SW` or equivalent D+/D- switch nets;
- AP/QUP UART destination and any debug-accessory path;
- main/sub-board connector continuity.

Do not buy a UART jig or install an unknown viewer on the strength of an E/U
index alone.

## 12. Documentation freshness audit

The latest private P3.19 F1 close is not yet reflected in all tracked status
surfaces.

| Document | Freshness | Required reading |
|---|---|---|
| `docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md` | current/binding | no-replay, exact target, physical topology, raw-first, and result-contract rules remain binding. |
| `GOAL.md` | stale current header | still calls P3.18 the current closed live unit; later text reaches P3.19 D1/D0 V3 and offline-ready preparation but not the live close. |
| `docs/devices/S22PLUS.md` | stale | still describes fresh baseline/F1 as missing. |
| `docs/operations/CAMPAIGN_LEDGER_S22PLUS.md` | stale tail | tail stops at the P3.19 runtime-bound repair review and lacks the latest F1 close. |
| `docs/module-map/s22plus-fyg8/subsystem-usb.md` | historical | mainly reflects the P2.78-era map; later P3.19 firmware analysis separates UCSI/GLINK role production from MAX77705 analog MUX. |
| P3.19 static/offline-ready reports | current for their named host closures | not live result reports and do not grant current authority. |

This comprehensive report records the discrepancy but does not silently edit
the binding contract or retrofit older immutable run rows.

## 13. Newly identified blocking hazards

### H1. Linux ABI-valid records can fail the observer

The parser's one-line and fixed-header grammar is narrower than `/dev/kmsg`.
This is capable of consuming a one-shot experiment before USB execution.

### H2. Detail namespace collision

`0x6020` has both a P3.19 witness meaning and an inherited publication-close
meaning. Detail ranges and signed return domains must be disjoint and
machine-checked.

### H3. Structural validity is collapsed into `bad-body`

The current model merges canonical-but-unknown semantics with malformed body
bytes. Future decoders need orthogonal structural, semantic, and policy states.

### H4. Rejected record evidence is destroyed

The next diagnostic cannot distinguish dictionary continuation from other
missing/trailing/multiple-newline body shapes because the exact rejected record
is absent. It also cannot retrospectively audit whether separate extra-header
or fragment compatibility hazards were present.

### H5. Host observation is not durable across runner cuts

The sidecar was healthy at arm but ended before boot-ready. A process cut must
not erase the only candidate attach window.

### H6. Canonical summaries lag durable state

GOAL, device page, and campaign ledger currently make a fresh reader believe
P3.19 has not run. This is a reporting hazard, though it grants no authority.

### H7. Historical proofs are artifact-specific

Earlier DWC3/UDC/RUN_STOP successes cannot fill P3.19's runtime gap. Any design
that treats them as current candidate facts would overclaim.

## 14. Recommended safe work sequence

### Phase A — preserve and explain the consumed run (H0 only)

1. Add a post-live decoder that never mutates the original result or journal.
2. Emit separate fields for header CRC, slot CRC, padding, semantic-domain
   membership, current-adapter compatibility, and effective H0 interpretation.
3. Bind the exact raw hash, unique offset, slot bytes, decoder source, and
   output bytes in a new immutable private receipt.
4. Record the official result and additive interpretation side by side.

### Phase B — repair the candidate observer (H0 only)

1. Define a length-framed record interface matching one `/dev/kmsg` read.
2. Parse mandatory header fields while safely retaining or ignoring unknown
   comma fields before `;`.
3. Preserve flags, sequence, caller metadata, continuation dictionary lines,
   and fragment state under strict byte/record bounds.
4. Keep known MAX77705 witness grammar strict after extracting only the human
   message line; do not let dictionary metadata impersonate a witness.
5. Treat `-EPIPE`, sequence gaps, boundary exhaustion, and malformed witness
   bodies as distinct outcomes.
6. On rejection, retain privately: failure site, return sign/domain, record
   length, sequence, flags, SHA-256, and a bounded escaped excerpt.
7. Allocate disjoint detail ranges for parser, publication-open/write/close,
   counter, boundary, and errno classes.
8. Exhaustively cross-check generated C emitter, checkpoint client, Carrier
   model, host spec, adapter, and decoder for every reachable detail.

Required hostile fixtures include:

- official `SUBSYSTEM`/`DEVICE` continuation example;
- extra header fields;
- `c` fragment flag and interleaving;
- missing, single, trailing, and multiple newline shapes;
- invalid UTF-8 and escaped bytes;
- sequence gaps and `-EPIPE`;
- maximum record/count/byte boundaries;
- known-witness prefix near misses;
- the exact retained P3.19 Carrier.

### Phase C — make the sidecar durable (H0 only)

1. Bind a sidecar owner and expected lifetime in the transaction journal.
2. Require coverage from before candidate transfer through bounded candidate
   observation, not merely transfer completion.
3. On a host cut, reconcile/adopt the owned process or close it as unknown
   without repeating candidate/rollback effects.
4. Test cuts after arm, during transfer, immediately post-transfer, pre-boot,
   during observation, and before result publication.
5. Preserve private raw identifiers; export only derived redacted claims.

### Phase D — independent review and documentation closure

1. Independently review the observer ABI, detail namespace, generated-C path,
   sidecar state machine, no-replay semantics, and hostile corpus.
2. Add the immutable P3.19 live row to the campaign ledger.
3. Update `GOAL.md` and `docs/devices/S22PLUS.md` to distinguish formal result,
   additive H0 reconstruction, consumed candidate, and next H0 blocker.
4. Keep older reports immutable except for clearly append-only corrections.

### Phase E — only then design a new candidate

A future live attempt requires a new candidate identity, fresh exact baseline,
new manifest/binding, independent review of changed execution-critical closure,
fresh approval, and the same rollback safety. It must not reuse the consumed
candidate.

The first future runtime goal is deliberately early:

1. prove row 1 and row 2 transitions with the repaired observer;
2. finish the exact 73-row plan;
3. prove parent gate 10, child gate 11, and UDC gate 12;
4. prove role request and exact readback;
5. prove configfs bundle and UDC bind;
6. prove pull-up/RUN_STOP and DWC3 event state;
7. correlate a continuous host attach trace;
8. only then assess MAX77705 pre/write/post state and physical MUX causality;
9. final transport proof requires exact endpoint identity and framed bytes.

### Phase F — hardware evidence only when the software path reaches it

An exact N-board schematic or bounded physical continuity investigation becomes
high value only after a new candidate proves the controller/UDC/pull-up path
while a valid host observer still sees no attach. Before that point, hardware
intervention cannot discriminate the current early parser failure.

## 15. Actions not justified by current evidence

Do not:

- replay the consumed P3.19 candidate;
- rerun it because the sidecar window was missed;
- add more USB modules to an already statically closed plan without a runtime
  supplier/bind discriminator;
- blame or write MAX77705, CONTROL1, UART, EUD, PHY, DWC3, UDC, configfs, or
  `soft_connect` based on this run;
- infer host silence from a trace that ended before boot-ready;
- turn historical UDC/RUN_STOP proof into current P3.19 runtime proof;
- promote `0x6020` to a unique root cause without the namespace and missing
  record caveats;
- treat an E/U/B schematic or generic upstream Qualcomm code as exact N-board
  evidence;
- install an unknown schematic viewer, create a paid account, or buy a jig
  without explicit operator direction and exact provenance;
- infer D0/D1/F1/recovery/live authority from this report or any H0 test.

## 16. Evidence index

### 16.1 Binding and current state

- `AGENTS.md`
- `docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md`
- `docs/operations/DEVICE_ACTION_RISK_TIERS.md`
- `docs/operations/DEVICE_ACTION_PROCESS_V2.md`
- `GOAL.md`
- `docs/devices/S22PLUS.md`
- `docs/operations/CAMPAIGN_LEDGER_S22PLUS.md`

### 16.2 Historical USB evidence

- `docs/reports/S22PLUS_FYG8_NATIVE_PID1_USERSPACE_EXPERIMENT_EVIDENCE_LEDGER_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_P257_F1_LIVE_DWC3_CORE_PASS_UDC_TIMEOUT_2026-07-25.md`
- `docs/reports/S22PLUS_FYG8_P258A_F1_LIVE_TERMINAL_UDC_PASS_2026-07-25.md`
- `docs/reports/S22PLUS_FYG8_P276_E3_F1_LIVE_POST_BIND_TIMEOUT_2026-07-26.md`
- `docs/reports/S22PLUS_FYG8_P280_PARENT_PULLUP_DISCRIMINATOR_F1_2026-07-28.md`
- `docs/reports/S22PLUS_FYG8_P292_F1_FINAL_NOT_ATTACHED_2026-08-01.md`
- `docs/reports/S22PLUS_FYG8_P296_F1_BUILTIN_DWC3_REFUTED_2026-08-03.md`
- `docs/reports/S22PLUS_FYG8_MAX77705_CONTROL_PLANE_SUCCESSOR_FEASIBILITY_H0_2026-08-11.md`
- `docs/reports/S22PLUS_FYG8_P318_POSTROLLBACK_FINALIZATION_INCIDENT_H0_2026-08-17.md`

### 16.3 P3.19 static and observer evidence

- `docs/reports/S22PLUS_FYG8_P319_STOCK_USERSPACE_CHOREOGRAPHY_H0_2026-08-19.md`
- `docs/reports/S22PLUS_FYG8_P319_CANDIDATE_WITNESS_PARSER_PREDECESSOR_H0_2026-08-20.md`
- `docs/reports/S22PLUS_FYG8_P319_CANDIDATE_WITNESS_CARRIER_V5_H0_2026-08-20.md`
- `docs/reports/S22PLUS_FYG8_P319_STOCK_WITNESS_RUNTIME_FOLLOWUP_H0_2026-08-21.md`
- `docs/reports/S22PLUS_FYG8_P319_SSUSB_UDC_PLAN_CLOSURE_H0_2026-08-24.md`
- `docs/reports/S22PLUS_FYG8_P319_PROCESS_V2_OFFLINE_READY_H0_2026-08-30.md`
- `docs/reports/S22PLUS_FYG8_P319_PREPARED_RUNTIME_BOUND_REPAIR_H0_2026-08-30.md`
- `workspace/public/src/scripts/analysis/s22plus_fyg8_p319_candidate_witness_parser_v2.py`
- `workspace/public/src/scripts/revalidation/s22plus_fyg8_p310_carrier_model.py`
- `workspace/public/src/scripts/revalidation/s22plus_fyg8_p294_telemetry_spec.py`
- `workspace/public/src/scripts/revalidation/s22plus_fyg8_p319_stock_process_v2_adapter.py`

### 16.4 Private current-run evidence

- `workspace/private/runs/device-action-f1-live-v2/`
  `f1-2026-08-30T082903022444Z-1788078543022472744/live-result.json`
- same run: `candidate-global-claim.json`
- same run: `rollback-observer-1.bin` and `rollback-observer-2.bin`
- same run: `p300-usb-trace/result.json`
- same run: append-only `transaction/journal/`

Private raw captures contain USB identifiers and must not be copied into tracked
reports. This report includes only bounded derived facts.

## 17. Final state

The current state is safe and closed: exact rollback and final health are
verified, and no recovery is pending. The formal experimental answer remains
no-proof. Additive H0 reconstruction `SUPPORTED`-strongly localizes an
observation-contract failure before the USB experiment executed, but does not
rewrite that formal result. The best available H0 conclusion is:

> P3.19 most strongly supports an early observer-contract defect, not a new USB
> hardware verdict. Repair and qualify the observer and sidecar first; then use
> a new, independently reviewed candidate to re-enter the module/SSUSB/UDC
> chain from the beginning. Preserve the consumed run and never replay it.

## 18. Immediate bounded implementation update

Later on 2026-08-30, the first deliberately small H0 follow-up was implemented:

- `workspace/public/src/scripts/revalidation/s22plus_fyg8_p319_postlive_decoder.py`
  reads only the fixed current run, verifies the exact live-result and two raw
  identities, and prints an additive JSON interpretation to stdout;
- it leaves the formal verdict and observer proof class unchanged;
- it reports both Carrier slots as structurally valid while preserving the
  second slot's legacy `semantic-out-of-domain` status;
- it labels the early observer conclusion `SUPPORTED`, keeps the `0x6020`
  subclass and `smem.ko` execution `UNKNOWN`, and grants no USB or replay claim;
- `tests/test_s22plus_fyg8_p319_postlive_decoder.py` adds four focused tests for
  structural/semantic separation, non-promotion, CRC rejection, and the actual
  immutable evidence.

This unit intentionally does not repair the candidate `/dev/kmsg` parser or
sidecar. The next small unit is the bounded parser record-envelope correction
and a short official-ABI fixture set; sidecar lifecycle remains separate.
