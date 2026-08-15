# A90 WLAN kernel-side composition and what it changes about the 13 roles

Date: 2026-08-15
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 host-only reading of an already-staged A90 kernel configuration
Device or live effect: none
Disposition: shifts the prior on which vendor roles are load-bearing; settles
that a same-tree kernel rebuild does not shorten the ablation program

Follow-up (2026-08-16):
[`A90_WLAN_KERNEL_SOURCE_CONFIRMATION_H0_2026-08-16.md`](A90_WLAN_KERNEL_SOURCE_CONFIRMATION_H0_2026-08-16.md)
preserves this pre-source prior and records what the matching source confirms,
corrects, or leaves unproved. This report remains the historical prior, not the
current source-backed conclusion.

Scope of the claim, stated once so nothing below is read past it: a kernel
configuration proves what is **compiled in**, never what **executes**. Every
statement here about which component performs a runtime step is a **prior**, to
be confirmed or refuted by the WP2 ablation program. Nothing here retires a
gate, and nothing here is a substitute for the one-factor evidence.

## Why this report exists

Two questions were open at the same time.

The first was asked directly: can a kernel rebuild solve part of the WLAN
ownership problem? The S22+ target has a proven rebuild-and-boot workflow, so
the question is reasonable on its face.

The second was implicit and more consequential. WSTA18 recorded that the
Debian process snapshot had lost `cnss-daemon`, `cnss_diag` and their vendor
companions while the firmware went down. Because `cnss-daemon` is named first
and matches the subsystem's name, the record invites the reading that
`cnss-daemon` is the load-bearing component. WSTA18 is an aggregate negative
and cannot support that attribution, but nothing in the current record pushes
back on it either.

The A90 kernel configuration is already staged on the host and answers both.

## What the configuration establishes

Read from the staged A90 configuration
(`Linux/arm64 4.14.190`, private path recorded under Sources):

```
CONFIG_QCA_CLD_WLAN=y            # WLAN driver is downstream qcacld-3.0
CONFIG_ICNSS=y                   # integrated connectivity subsystem path
CONFIG_ICNSS_QMI=y               # WLFW QMI client is compiled into the kernel
CONFIG_BTFM_SLIM_WCN3990=y       # connectivity part is WCN3990
# CONFIG_CNSS2 is not set        # not the PCIe-attached CNSS path
# CONFIG_CNSS is not set
# CONFIG_PCIE_QCOM is not set
CONFIG_QRTR=y                    # QRTR transport in kernel
CONFIG_QRTR_SMD=y
CONFIG_QCOM_QMI_HELPERS=y        # QMI encode/decode in kernel
CONFIG_QCOM_MDT_LOADER=y         # firmware image loading in kernel
CONFIG_QCOM_SCM=y
CONFIG_QCOM_SMEM=y
CONFIG_MSM_PIL=y                 # downstream peripheral image loader
CONFIG_MSM_PIL_SSR_GENERIC=y
CONFIG_MSM_SUBSYSTEM_RESTART=y
# CONFIG_REMOTEPROC is not set   # mainline remoteproc unused; PIL instead
CONFIG_CNSS_UTILS=y
CONFIG_CNSS_GENL=y
CONFIG_WCNSS_MEM_PRE_ALLOC=y
```

Three facts follow directly, with no inference about runtime behaviour:

1. This is the **integrated** WCN3990 path, not the PCIe CNSS2 path. The two
   have different userspace obligations, and evidence written for one does not
   describe the other.
2. The **WLFW QMI client, the QMI helper layer, the QRTR transport, and the
   firmware image loader are all compiled into the kernel.** They are not
   exclusively userspace responsibilities on this build.
3. Subsystem lifecycle uses the **downstream MSM PIL / subsystem-restart**
   stack, not mainline remoteproc, so nothing written about mainline
   remoteproc describes this kernel.

## First answer: a same-tree kernel rebuild does not shorten the program

The thirteen vendor roles do not exist because a configuration symbol was left
off. QRTR, the QMI helpers, the MDT loader, SCM, SMEM, PIL and
subsystem-restart are **already** `=y`. There is no symbol in this tree that
relocates `pd_mapper`, `rmt_storage`, `per_mgr` or the Binder and property
plumbing into the kernel; those are userspace by architecture on this vintage.

Consequently, **rebuilding this kernel from its own sources removes none of the
thirteen roles**, and the ablation program's execution cost is unchanged by it.
A kernel rebuild remains useful for other purposes; it is not a WLAN ownership
lever.

## Second answer: the prior on which roles are load-bearing moves

The configuration does not prove any component unnecessary. It does change
which components are the better suspects, because it shows which work the
kernel already contains and which work it does not.

| Role | Does the kernel contain this work? | Prior |
|---|---|---|
| `cnss_daemon` | WLFW QMI client and firmware image loading are in-kernel (`ICNSS_QMI`, `QCOM_MDT_LOADER`) | **weaker suspect than the record implies** |
| `cnss_diag` | diagnostics channel only (`CNSS_GENL`) | weak; already ordered first for removal |
| `pd_mapper` | no protection-domain mapper in this tree | **stronger suspect** |
| `per_mgr`, `pm_proxy_helper` | no in-kernel peripheral-manager service | **stronger suspect** |
| `rmt_storage`, `tftp_server` | no in-kernel remote filesystem service | **stronger suspect** |
| `qrtr_ns` | transport is in-kernel; the **name service is not** on this vintage, which is why it appears as a userspace role at all | near-certain requirement |
| `servicemanager`, `hwservicemanager`, `vndservicemanager` | Binder infrastructure, unrelated to the WLAN control path in the kernel | unknown; only ablation can say |
| `property-service-shim` | Android property, no kernel counterpart | unknown; ties to the property terminal work |
| `modem-holder` | subsystem lifetime via PIL/SSR | unknown |

The direction of the shift is the useful part: suspicion moves **away from the
single daemon whose name matches the subsystem** and **toward the
protection-domain and remote-filesystem group**, which supplies exactly the
services the kernel does not implement here.

That the `qrtr_ns` role exists in the component list at all is an independent
corroboration of this reading: the transport is compiled in, so a userspace
`qrtr_ns` can only be present because the name service is not.

## What this does not settle

- **It does not prove `cnss_daemon` removable.** Compiled-in code is not
  executed code, and `icnss` may still depend on userspace for protection-domain
  notification, firmware access, or sequencing. `WP-H0-2-A8` remains a real
  experiment with a real possible failure.
- **It does not prove the protection-domain group required.** "The kernel does
  not implement this" is not "a userspace daemon must supply it"; the firmware
  may already hold what it needs by the time the role would matter.
- **It does not re-attribute WSTA18.** WSTA18 removed the whole set at once and
  supports only that some surviving vendor control plane was required. This
  report changes which single-role outcome is *expected*, not what was proven.
- **It does not license reordering the ablation program.** The current order
  banks low-risk removals first, which is a defensible budget strategy; whether
  information ordering should override it is a separate design decision.

## The mainline alternative, and its honest cost

⚠️ **The following is unverified recollection, not repository evidence, and is
recorded as a lead requiring its own H0 confirmation. Do not cite it as a
basis for any decision until checked against upstream sources.**

Upstream Linux is believed to have absorbed several of these roles for this
chip family: WCN3990 supported through `ath10k` on the SNOC bus, the QRTR name
service moved into the kernel around 5.7, an in-kernel protection-domain mapper
added around 6.12, and remote filesystem service provided by a small
standalone `rmtfs` daemon rather than Android vendor userspace. If accurate,
most of the thirteen roles would not exist on such a system.

The cost is the reason this is a lead and not a plan. It is not a rebuild but a
replacement: `qcacld-3.0` for `ath10k`, a 4.14 downstream tree for a mainline
one, and the Samsung device tree for a mainline device tree. Display, GPU,
audio, modem and USB gadget all currently run on downstream drivers, and those
are the completed A90 native baseline. The trade is a working system for an
unproved one.

This belongs in the record as a costly open option so it is not rediscovered as
a novelty later. It is not proposed here.

## Source acquisition remains open

The A908N kernel sources are **not staged**. What is present under the OSRC
package name is a residue of eleven files, every one matching `recovery` in its
filename, left by an earlier search rather than an extraction.

`docs/plans/NATIVE_INIT_V759_SOURCE_ACQUISITION_PLAN_2026-05-24.md` already
identified this work, including work item 3, "detect whether the source
download is gated by human verification", and the non-goal
`no hCaptcha bypass attempt`. That plan has **no runner and no report**; it was
never executed, and the item has been open since.

Current status, re-confirmed on this date by host-only means: the Samsung Open
Source Release Center search endpoint is reachable and lists
`SM-A908N_KOR_12_Opensource.zip` under two upload identifiers. The download
itself terminates at an hCaptcha human-verification step. **No bypass was
attempted and none is authorized.** Acquisition is an operator action.

The correct package is the one matching the installed firmware
`A908NKSU5EWA3`, which is upload identifier `13272`. The other listed package
covers later builds that are not installed on this unit, and reasoning about the
running kernel requires the matching build.

Three questions are held for that source and cannot be answered without it:

1. what `icnss` requires from userspace before and during firmware bring-up;
2. which QMI services the kernel is a **client** of, versus which require a
   userspace **server** — this is what confirms or refutes the
   protection-domain and remote-filesystem prior above;
3. which `cnss_utils` and `cnss_genl` consumers exist in `qcacld-3.0`, which is
   what `cnss_daemon` is actually needed for.

## Consequence for the WLAN ablation program

This report is an input to the ablation program and changes none of its gates.
`H0D01` through `H0D10` remain `UNPROVED`, no component is retired, no
execution authority is created, and the measured-budget requirements are
untouched.

Its practical effect is on interpretation. When `WP-H0-2-A8` removes
`cnss_daemon`, a surviving control plane should not be read as surprising, and
when the protection-domain or remote-filesystem roles are removed, a failure
should not be read as merely confirming WSTA18. Recording the prior before the
experiment is what keeps the result from being fitted to expectation afterwards.

## Sources

- staged A90 kernel configuration, private:
  `workspace/private/outputs/a90-phase2a-kernel.tBOMsQ/v3404.config`
- OSRC package residue, private:
  `workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/`
- `docs/plans/NATIVE_INIT_V759_SOURCE_ACQUISITION_PLAN_2026-05-24.md`
- `docs/reports/A90_NATIVE_WIFI_OWNERSHIP_PERMANENCE_EVIDENCE_H0_2026-08-15.md`
- `docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15/proposals/wlan-vendor-property-ablation.md`
- `docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15/design/a90-h24-wlan-one-factor-ablation-design-v1.json`

## Boundary

Produced from an already-staged host artifact and public repository documents
only. Device, `/dev`, USB, `workspace/private` mutation, S22+, and S20+ contacts
are zero. Network use was limited to reading a public vendor source-release
listing; no download, no authentication, and no human-verification bypass
occurred. No ordinal, identity, artifact, approval, candidate, qualification, or
command is created, and no D0, D1, or F1 authority is granted or implied.
