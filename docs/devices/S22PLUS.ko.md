# Samsung Galaxy S22+ FYG8

[English](S22PLUS.md) · **한국어**

## 기기 / SoC / kernel

- 기기: Samsung Galaxy S22+ (`SM-S906N`, `g0q`), exact firmware
  `S906NKSS7FYG8`.
- SoC: Qualcomm SM8450 / Snapdragon 8 Gen 1 (`taro`).
- Kernel: source-matched Samsung vendor Linux
  `5.10.226-android12-9-30958166-abS906NKSS7FYG8`.

## 역할

S22+는 source-matched rebuilt-kernel과 direct-native-PID1 연구 대상입니다.
Kernel-to-native-exec 경계를 확립했으며, 현재는 Android userspace 없이 native
runtime을 관측할 수 있도록 vendor module, supplier, role, gadget, physical-attach
chain을 충분히 재구성하는 더 어려운 early USB 문제에 집중합니다.

## 증명된 capability

- **PROVED(증명됨) — reproducible source-matched kernel build.** Rebuilt
  Full-LTO kernel은 예상된 format과 identity를 가지며, bounded live candidate가
  clean rollback 전에 exact FYG8 Android userspace를 boot했습니다.
- **PROVED(증명됨) — rebuilt-kernel early Android witness.** 이후 guarded
  candidate가 예상된 early Android PID1 path에 도달했고, accepted acquisition
  channel을 통해 retained marker를 보존했습니다.
- **PROVED(증명됨) — direct native `/init` exec acceptance.** R4W1-D는 current가
  PID 1인 동안 `kernel_execve("/init")` 성공 이후 exact retained marker 하나를
  생성했습니다. 이는 kernel이 의도한 native executable을 PID 1로 받아들였음을
  증명합니다. 첫 userspace instruction 실행은 증명하지 않습니다.
- **PROVED(증명됨) — recovery-safe experiment mechanics.** Process-v2 run은
  transfer, observation, rollback, final health를 구분하고 candidate no-replay를
  보존합니다. 이후 여러 USB experiment는 candidate success를 승격하지 않은 채
  no-proof 또는 refutation으로 안전하게 종료됐습니다.
- **PROVED(증명됨), host-side 한정 — current USB plan static closure.** P3.19
  plan은 73개 row, 누락된 declared dependency 0개, ordering violation 0개, 72개
  vendor row의 exact module byte, built-in DWC3/gadget core를 가집니다. 이는 static
  membership/order/ABI 결과에만 해당합니다.
- **PROVED(증명됨) — P3.19 recovered final health.** Exact candidate와 rollback이
  각각 한 번 전송됐고 journal이 닫혔으며 rooted FYG8 Android health가
  통과했습니다. Formal result는 USB 성공이 아닌 `NO_PROOF_OBSERVER`이며
  candidate는 replay 없이 소비됐습니다.

## 부분 증명 / 관측

- **observed(관측됨) — stock Android와 stock first-stage CDC ACM은
  functional합니다.** Bounded stock control이 framed exchange 128회를 완료했고,
  early Android boot service도 같은 결과를 반복했습니다. 어느 쪽도 native-PID1
  USB bring-up을 증명하지 않습니다.
- **observed(관측됨) — direct-native candidate에서 host-visible ACM이 반복해서
  나타나지 않았습니다.** 이는 실제 symptom이지만, 과거 witness는 첫 device-side
  failure gate를 식별하지 못한 경우가 많았습니다.
- **PROVED(증명됨), P3.15 내부에 한정 — restart-side functional witness가
  실행됐습니다.** 같은 run은 clean four-outer-work model을 refute했습니다. USB2
  connector pull-up, attachment, transport는 증명하지 않았습니다.
- **observed(관측됨) — stock recovery는 SSUSB mode에 `peripheral`을 쓰고
  `a600000.dwc3`를 기다릴 수 있습니다.** 이 positive control은 direct-role design
  shape를 뒷받침하지만 다른 runtime/Image를 사용하므로 candidate bind를
  증명하지 않습니다.

## 아직 증명되지 않은 것

- Direct native userspace의 첫 instruction, 이후 mount, child execution, native
  control loop.
- Candidate runtime에서 `a600000.ssusb` parent bind.
- Built-in `a600000.dwc3` child의 creation/bind와
  `/sys/class/udc/a600000.dwc3` publication.
- Configfs gadget bind, DWC3 pull-up/connect, physical host attach, tty
  publication, framed native transport의 성공.
- 현재 candidate plan에서 complete natural UCSI/PMIC-GLINK role path.
- P3.20 successor candidate, 현재 ready/run manifest, standing live authority.

## 현재 프론티어

USB 프론티어는 의도적으로 네 causal layer로 분리합니다.

```text
SSUSB parent (a600000.ssusb)
  -> DWC3 child (a600000.dwc3)
    -> UDC (/sys/class/udc/a600000.dwc3)
      -> transport (gadget bind -> pull-up/connect -> host tty -> framed bytes)
```

현재 P3.19 closure에서는 module membership, declared dependency, ordering,
relevant symbol provider, `mode_store -> dwc3_msm_set_role` edge, runtime이
의도한 `mode=peripheral` write가 **PROVED(증명됨), host-side 한정**입니다.
Dynamic supplier availability, `dwc3_msm_probe()`, parent bind, child creation,
UDC publication, 모든 transport step은 **unproved(미증명), candidate runtime
한정**입니다.

이후 P3.19는 healthy close했지만 USB plan이 실행되기 전에 observer가
실패했습니다. Additive H0 decoding은 formal no-proof result를 보존하면서 가장 강한
설명을 row 1 이후 kmsg drain으로 국한합니다. Bounded P3.20 host prototype은 valid
kmsg dictionary line을 human message와 분리하고 같은 C envelope도 compile합니다.
아직 candidate에 연결되지 않았으며 현재 live authority는 없습니다.

## 주요 milestone

1. Exact FYG8 source와 Full-LTO build closure가 Android를 boot하는 rebuilt
   kernel을 만들었습니다.
2. Retained-witness 작업이 reliable acquisition과 strict absence classification
   boundary를 확립했습니다.
3. R4W1-D가 PID 1에서 direct native `/init` exec acceptance를 증명했습니다.
4. 이후 USB run은 명시적 refutation과 no-proof terminal을 포함해 functional
   restart witness를 connector/transport claim과 분리했습니다.
5. P3.19는 broad connector/MUX speculation에서 명시적인 SSUSB-parent →
   DWC3-child → UDC → transport chain으로 프론티어를 옮겼습니다.
6. 현재 73-row plan은 static module/order/ABI 문제를 닫으면서 모든 dynamic
   runtime 문제를 unproved(미증명)로 보존했습니다.
7. P3.19는 healthy close했지만 early observer-contract failure를 드러냈으며,
   소비된 run은 새로운 USB hardware verdict를 제공하지 않습니다.

## Architecture 요약

```text
bootloader
  -> source-matched Samsung 5.10.226 kernel
    -> custom static /init accepted as PID 1
      -> load ordered vendor USB/provider closure
      -> bind a600000.ssusb parent
      -> materialize built-in a600000.dwc3 child and UDC
      -> set peripheral role and bind configfs gadget
      -> enumerate ACM and exchange framed bytes
```

Exec acceptance까지의 첫 두 line만 direct native live result로 확립됐습니다. USB
line은 현재 test 대상 architecture와 runtime gate를 나타내며 completed path가
아닙니다.

## 정본 증거 링크

- 현재 프론티어: [GOAL.md](../../GOAL.md)
- Binding target contract: [S22+ FYG8 target contract](../operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md)
- Historical run ledger: [S22+ campaign ledger](../operations/CAMPAIGN_LEDGER_S22PLUS.md)
- Epistemic experiment index: [native PID1/userspace evidence ledger](../reports/S22PLUS_FYG8_NATIVE_PID1_USERSPACE_EXPERIMENT_EVIDENCE_LEDGER_2026-07-22.md)
- Rebuilt-kernel Android proof: [R3C1 live result](../reports/S22PLUS_FYG8_R3C1_LIVE_RESULT_2026-07-12.md)
- Direct PID1 boundary: [R4W1-D live pass](../reports/S22PLUS_FYG8_R4W1D_F1_LIVE_PASS_2026-07-21.md)
- Stock ACM positive control: [O0 stock USB control](../reports/NATIVE_INIT_V3403_S22PLUS_O0_STOCK_USB_CONTROL_LIVE_2026-07-10.md)
- 현재 static USB closure: [P3.19 SSUSB/UDC plan closure](../reports/S22PLUS_FYG8_P319_SSUSB_UDC_PLAN_CLOSURE_H0_2026-08-24.md)
- 현재 USB audit와 live interpretation: [P3.19 comprehensive USB audit](../reports/S22PLUS_FYG8_USB_COMPREHENSIVE_INVESTIGATION_AUDIT_H0_2026-08-30.md)
- Additive post-live decoder: [`s22plus_fyg8_p319_postlive_decoder.py`](../../workspace/public/src/scripts/revalidation/s22plus_fyg8_p319_postlive_decoder.py)
- 현재 H0 kmsg successor prototype: [`s22plus_fyg8_p319_kmsg_record_envelope.py`](../../workspace/public/src/scripts/analysis/s22plus_fyg8_p319_kmsg_record_envelope.py)
