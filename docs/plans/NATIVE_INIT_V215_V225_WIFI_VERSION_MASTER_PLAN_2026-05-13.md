# v215-v225 Version Master Plan: Wi-Fi Bring-Up Lifecycle

## Summary

이 문서는 v215 이후 Wi-Fi bring-up 작업을 버전별 큰 흐름으로 다시
정리한다. 기존 `NATIVE_INIT_V215_V225_WIFI_LIFECYCLE_ROADMAP_2026-05-13.md`
는 상세 로드맵이고, 이 문서는 실행 순서와 분기 기준을 더 짧고 명확하게
보는 상위 계획이다.

현재 기준 결론은 보수적으로 잡는다.

- v214에서 generic ICNSS `unbind`/`bind`는 `icnss-rebind-failed`로 중단됐다.
- v215-v219는 read-only evidence와 dry-run planning은 통과했다.
- v220 gate는 `no-go`를 반환했다.
- v221 이후는 active Wi-Fi가 아니라 missing prerequisite closure로 전환한다.
- daemon start, rfkill write, link-up, scan, connect는 계속 금지한다.

## Reference Basis

계획의 기준은 코드베이스 증거와 다음 외부 구조 참고 자료다.

- Linux firmware runtime path는
  `/sys/module/firmware_class/parameters/path`로 변경 가능하지만, 이것은
  파일 검색 문제만 해결한다. ICNSS/CNSS power, recovery, QMI/PDR/SSR,
  Android service ordering은 별도 문제다:
  <https://docs.kernel.org/driver-api/firmware/fw_search_path.html>
- Linux driver model에서 `probe`/`remove`는 실제 driver lifecycle이다.
  v214의 실패는 generic sysfs bind/unbind를 임의 재시도하는 방식이
  안전한 recovery primitive가 아님을 의미한다:
  <https://docs.kernel.org/driver-api/driver-model/driver.html>
- Android init은 `.rc` action/service/property trigger/class/socket/user/
  group/capability 기반으로 서비스를 실행한다. native init에서 Wi-Fi를
  다루려면 단일 binary 실행이 아니라 service environment와 ordering을
  재현 가능한 범위로 모델링해야 한다:
  <https://android.googlesource.com/platform/system/core/+/master/init/README.md>

## Global Guardrails

모든 버전은 아래 규칙을 유지한다.

- `read-only`가 기본값이다.
- `temporary-mutating`은 명시적 opt-in, rollback evidence, timeout, reboot
  recovery path가 있어야 한다.
- `active-network`는 scan-only부터 시작하며, connect는 별도 보안 검토
  이후에만 가능하다.
- `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, supplicant, hostapd 실행은
  v220 gate와 후속 blocker closure 전까지 금지한다.
- generic ICNSS `unbind`/`bind`, `driver_override`, rfkill write, link-up은
  별도 승인 전까지 금지한다.
- serial/ACM 또는 NCM rescue control path가 살아 있어야 다음 단계로
  진행한다.

## Current Evidence State

| Version | State | Decision | Meaning |
| --- | --- | --- | --- |
| v215 | PASS | `lifecycle-map-ready` | Android/native ICNSS/CNSS lifecycle evidence 확보 |
| v216 | PASS | `replay-model-ready` | Android Wi-Fi/CNSS service graph 모델링 완료 |
| v217 | PASS | `state-only-inventory` | ICNSS debug/recovery surface read-only 분류 완료 |
| v218 | PASS | `daemon-dryrun-partial` | CNSS daemon dependency 일부 확인, ELF/library gap 남음 |
| v219 | PASS | `shim-plan-partial` | Android-env shim matrix 작성, property/QMI/recovery blocker 남음 |
| v220 | PASS | `no-go` | lifecycle-aware gate 통과, active Wi-Fi blocker 유지 |
| v221 | PASS | `vendor-root-required` | ELF/library inspection needs host-visible vendor root evidence |

## Version-By-Version Plan

### v215. ICNSS/CNSS Lifecycle Research

Mode: `read-only`

Goal: Android가 정상 Wi-Fi를 올릴 때 사용하는 ICNSS/CNSS lifecycle과 native
상태의 차이를 설명한다.

Status:

- done
- result: `lifecycle-map-ready`
- report:
  `docs/reports/NATIVE_INIT_V215_ICNSS_CNSS_LIFECYCLE_RESEARCH_2026-05-13.md`

Outputs:

- Android/TWRP/native dmesg and service evidence
- vendor init rc ordering hints
- ICNSS/CNSS/interface/firmware evidence chain

### v216. Android Service Replay Model

Mode: `read-only`

Goal: Android init service definitions를 native에서 바로 실행하지 않고,
dependency graph로 재현 가능성을 모델링한다.

Status:

- done
- result: `replay-model-ready`
- report:
  `docs/reports/NATIVE_INIT_V216_ANDROID_SERVICE_REPLAY_MODEL_2026-05-13.md`

Outputs:

- service graph:
  `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, `wpa_supplicant`, `hostapd`
- required mounts, binaries, users/groups, capabilities, sockets, properties

### v217. ICNSS Debug / Recovery Inventory

Mode: `read-only`

Goal: v214에서 실패한 generic bind/unbind 대신 driver-specific state/recovery
surface를 위험도별로 분류한다.

Status:

- done
- result: `state-only-inventory`
- report:
  `docs/reports/NATIVE_INIT_V217_ICNSS_DEBUG_RECOVERY_INVENTORY_2026-05-13.md`

Outputs:

- native controls: `168`
- dangerous controls:
  `/sys/bus/platform/drivers/icnss/bind`,
  `/sys/bus/platform/drivers/icnss/unbind`,
  `/sys/devices/platform/soc/18800000.qcom,icnss/driver_override`
- conclusion: reboot remains the only proven recovery path

### v218. CNSS Daemon Dry-Run Feasibility

Mode: `read-only`

Goal: `cnss-daemon`/`cnss_diag`를 실행하지 않고 executable/library/mount/
property/socket/device-node/capability requirements를 정리한다.

Status:

- done
- result: `daemon-dryrun-partial`
- report:
  `docs/reports/NATIVE_INIT_V218_CNSS_DAEMON_DRYRUN_FEASIBILITY_2026-05-13.md`

Remaining blocker:

- host-visible vendor root가 없어 ELF/shared-library inspection이 incomplete
- recovery path가 reboot-only라 active daemon experiment risk가 높음

### v219. Native Android-Env Shim Plan

Mode: `read-only planning`

Goal: CNSS/Wi-Fi service experiment 전에 필요한 최소 Android-like runtime shim
범위를 allow/deny list로 분리한다.

Status:

- done
- result: `shim-plan-partial`
- report:
  `docs/reports/NATIVE_INIT_V219_NATIVE_ANDROID_ENV_SHIM_2026-05-13.md`

Remaining blocker:

- Android property service recreation denied
- QMI/PDR/SSR writes denied
- binder/hwbinder service publication out-of-scope
- Wi-Fi credential/data path denied

### v220. Wi-Fi Bring-Up Preflight Gate v2

Mode: `read-only`

Goal: v210-v219 evidence를 통합해 active Wi-Fi 준비 여부를 결정한다.

Result:

- `no-go`
- 이유: v218 ELF/library evidence gap, v219 blocked shim items, v217 reboot-only
  recovery, v224 security exposure review 미완료
- report:
  `docs/reports/NATIVE_INIT_V220_WIFI_PREFLIGHT_GATE_V2_2026-05-13.md`
- gate counts: `pass=3`, `warn=1`, `fail=0`, `blocked=3`
- blocked: `icnss_recovery`, `shim_policy`, `security_exposure`

Required outputs:

- `tmp/wifi/v220-bringup-gate-v2/manifest.json`
- `tmp/wifi/v220-bringup-gate-v2/gate.json`
- `tmp/wifi/v220-bringup-gate-v2/summary.md`
- report:
  `docs/reports/NATIVE_INIT_V220_WIFI_PREFLIGHT_GATE_V2_2026-05-13.md`

Decision:

- `go-scan-prep`: v221 can plan a controlled temporary mutation
- `no-go`: v221 must become prerequisite closure, not daemon start
- `manual-review-required`: evidence conflict; stop and document

## v221-v225 Conditional Plan

v221 이후는 v220 gate 결과에 따라 두 갈래로 나눈다. 현재는 **no-go path가
정상 예상값**이다.

### Path A. If v220 Returns `no-go`

이 경로가 현재 기본 계획이다.

#### v221. Host Vendor ELF / Library Evidence Closure

Mode: `read-only`

Goal: v218의 가장 큰 evidence gap인 `cnss-daemon`/`cnss_diag` ELF,
interpreter, DT_NEEDED, config/library path를 host-visible vendor evidence로
닫는다.

Plan:

- `docs/plans/NATIVE_INIT_V221_HOST_VENDOR_ELF_LIBRARY_EVIDENCE_PLAN_2026-05-13.md`

Status:

- done
- result: `vendor-root-required`
- report:
  `docs/reports/NATIVE_INIT_V221_HOST_VENDOR_ELF_LIBRARY_EVIDENCE_2026-05-13.md`
- required paths:
  - `<vendor-root>/bin/cnss-daemon`
  - `<vendor-root>/bin/cnss_diag`

Deliverables:

- host vendor root locator or mounted vendor bundle parser
- `cnss-daemon`/`cnss_diag` dependency manifest
- missing library and executable risk table

Decision:

- `elf-evidence-ready`
- `daemon-native-blocked`

#### v222. Vendor Root Evidence Export / Extraction

Mode: `read-only`

Goal: v221 `vendor-root-required` 결과를 닫기 위해 host-visible vendor root
또는 최소 vendor evidence bundle을 안전하게 확보한다.

Plan:

- `docs/plans/NATIVE_INIT_V222_VENDOR_ROOT_EVIDENCE_EXPORT_PLAN_2026-05-13.md`

Status:

- done
- result: `export-source-required`
- report:
  `docs/reports/NATIVE_INIT_V222_VENDOR_ROOT_EVIDENCE_EXPORT_2026-05-13.md`
- tool: `scripts/revalidation/wifi_vendor_root_evidence_export.py`

Deliverables:

- private/no-follow vendor evidence output model
- required path checklist for `cnss-daemon` and `cnss_diag`
- `--source-vendor-root` export mode for related `lib`/`lib64` vendor shared libraries
- re-run instructions for v221 `--vendor-root`

Decision:

- `vendor-root-ready`
- `export-source-required`
- `vendor-export-blocked`

#### v223. Recovery / Rollback Policy Hardening

Mode: `read-only` plus reboot-only policy documentation

Plan:

- `docs/plans/NATIVE_INIT_V223_RECOVERY_ROLLBACK_POLICY_PLAN_2026-05-13.md`

Goal: reboot-only recovery를 accepted risk로 둘 수 있는지 판단하고, active
experiment 전에 필요한 stop condition과 evidence bundle을 고정한다.

Deliverables:

- ICNSS broken-state detection checklist
- automatic stop/reboot handoff policy
- pre/post evidence capture checklist

Decision:

- `reboot-recovery-accepted`
- `active-mutation-blocked`

#### v224. Android-Env Shim Dry-Run Materialization

Mode: `temporary-mutating` only for reversible mount/path stubs, no daemon start

Goal: v219 shim matrix에서 `shim-required` 항목만 실제 native filesystem/runtime
layout으로 만들 수 있는지 검증한다.

Allowed:

- temporary `ro,noload` vendor visibility
- temporary path aliases under controlled mountpoint
- log/output directory preparation

Forbidden:

- daemon execution
- Android property mutation
- QMI/PDR/SSR write
- Wi-Fi scan/connect

Decision:

- `shim-materialized`
- `shim-too-wide`

#### v225. Wi-Fi Exposure / Credential Security Gate + Gate v3

Mode: `read-only`

Goal: Wi-Fi가 열렸을 때 root-control 채널이 USB-local 밖으로 노출되지 않도록
listener binding, auth token, credential handling, redaction을 재검토하고
v221-v224 결과를 gate v3로 통합한다.

Deliverables:

- exposure matrix for ACM, NCM, tcpctl, rshell, broker
- credential and artifact redaction policy
- test AP isolation requirements
- go/no-go for controlled CNSS start planning

Decision:

- `cnss-start-plan-approved`
- `still-no-go`

### Path B. If v220 Returns `go-scan-prep`

이 경로는 현재 가능성이 낮지만, gate가 통과할 경우의 빠른 진행 순서다.

#### v221. Controlled CNSS Start Experiment

Mode: `temporary-mutating`, explicit opt-in

Start one minimal CNSS component under timeout, collect state deltas, stop/reap,
rollback, and reboot if ICNSS becomes inconsistent.

#### v222. nl80211 / rfkill Passive Transition Check

Mode: `read-only`

If WLAN objects appear, inspect netdev/rfkill/wiphy/nl80211 state without link-up
or scan.

#### v223. First Scan-Only Gate

Mode: `active-network`, scan-only

Run scan-only with no association, no DHCP, no credentials, no Internet routing.

#### v224. Wi-Fi Security Pre-Connect Review

Mode: `read-only`

Approve or deny first test AP connection based on credential and exposure
policy.

#### v225. First Controlled Test AP Connect

Mode: `active-network`, isolated test AP only

Connect only if v223 scan and v224 security review pass.

## Practical Next Action

v222 tooling is implemented and currently returns `export-source-required` because no source vendor root has been provided.

1. collect or validate host-visible vendor evidence for `cnss-daemon` and `cnss_diag` with v222 `--source-vendor-root`;
2. rerun v221 with the exported `vendor-root/` if v222 returns `vendor-root-ready`;
3. alternatively, proceed to v223 recovery/rollback policy hardening while preserving the vendor-root blocker;
4. keep daemon execution blocked;
5. keep Path B inactive unless a future reviewed gate supersedes v220.

## Acceptance For This Master Plan

- It does not approve active Wi-Fi by itself.
- It makes v221 conditional on v220 evidence.
- It keeps v214 safety stop as the core technical constraint.
- It separates evidence closure, recovery policy, security policy, and active
  network tests into different versions.
