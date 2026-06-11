# Native Init V2196 Stackmap Symbolization P1b (2026-06-11)

대상: A90 native boot `0.9.261 (v2189-security-p0-stage-fix)`.

목적: V2195에서 회수한 stackmap raw kernel IP를 `symbol + offset`으로 변환하기
위해 현재 boot와 맞는 symbol map을 확보·검증한다.

범위: host-side symbol map build/analysis + live read-only timer tracepoint anchor
수집. Wi-Fi, credential, DHCP, external ping, 커널/펌웨어/파티션 쓰기,
`probe_write_user` 실행, cgroup attach 없음.

---

## 1. 결론

P1b는 **정확 심볼화까지는 미완료**다.

```text
decision: v2196-p1b-symbolization-blocked-no-matching-stock-map
```

이번 run에서 확인한 것은 다음이다.

- OSRC 커널 소스는 다시 빌드되어 `vmlinux`와 `System.map`을 생성했다.
- 그러나 live boot image 안의 stock kernel blob SHA와 새 빌드 `Image` SHA가 다르다.
- 따라서 새 `System.map`은 V2195 raw IP의 **정확한** symbol map으로 사용할 수 없다.
- live timer tracepoint에서 `function` runtime pointer anchor는 수집됐다.
- 이 anchor와 V2195 stack IP는 모두 raw kernel VA지만, matching stock map 없이
  단일 slide를 확정하면 과적합이 된다.

즉 V2196의 결과는 “stackmap symbolization capability 실패”가 아니라
**artifact gap**이다. BPF 쪽 raw IP/anchor 회수는 동작하고, 남은 조건은 현재
stock kernel과 일치하는 `System.map`/unstripped `vmlinux`/stock kallsyms 복구다.

보정: V2195에서 세운 “slide anchor + static build면 후처리” 프레이밍은
**bit-exact map이 있을 때만** 성립한다. 같은 소스 재빌드라도 toolchain,
post-link RKP/CFP 변환, vendor patch layout 차이 때문에 함수 상대 배치가
비균일하게 어긋날 수 있다. 따라서 runtime pointer 하나로 단일 slide를 잡아도
candidate `System.map`이 live kernel과 SHA/레이아웃으로 검증되지 않으면 정확
심볼화를 주장하면 안 된다. V2196에서 “그럴듯한 slide 후보”를 버린 것이
의도한 안전장치다.

---

## 2. 산출물

| 항목 | 값 |
| --- | --- |
| Host symbolizer | `workspace/public/src/scripts/revalidation/a90_kernel_stack_symbolize.py` |
| OSRC build evidence | `workspace/private/runs/kernel/v2196-symbol-map-build-3` |
| Generated vmlinux | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/vmlinux` |
| Generated System.map | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/System.map` |
| Generated Image | `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/out/arch/arm64/boot/Image` |
| P1b evidence | `workspace/private/runs/kernel/v2196-p1b-symbolization` |
| Symbolization JSON | `workspace/private/runs/kernel/v2196-p1b-symbolization/symbolization.json` |
| Symbolization summary | `workspace/private/runs/kernel/v2196-p1b-symbolization/symbolization.md` |

검증:

```sh
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_kernel_stack_symbolize.py
```

---

## 3. Symbol Map Build

V769 계열 RKP/CFP Python3 repair build path를 workspace 마이그레이션 후 경로로
재실행했다. 첫 run은 `.config`가 없어 막혔고, `r3q_kor_single_defconfig`를
재생성한 뒤 build를 재실행했다.

최종 build 결과:

```text
decision: v769-rkp-cfp-python3-repair-image-pass
pass: True
reason: RKP_CFP Python3 repair completed and final Image exists in disposable source tree
kernel_build_executed: True
boot_image_write_executed: False
device_commands_executed: False
```

생성 파일:

```text
vmlinux:    ELF 64-bit LSB pie executable, ARM aarch64, with debug_info, not stripped
System.map: ASCII text
Image:      Linux kernel ARM64 boot executable Image, little-endian, 4K pages
```

대표 static symbols:

```text
ffffff80080e2aac t trace_event_raw_event_sched_switch
ffffff80080e2c2c t perf_trace_sched_switch
ffffff80080edcec t finish_task_switch
ffffff80081c2524 T trace_call_bpf
ffffff80081e72f4 T bpf_get_stackid
ffffff80099c41c4 t __schedule
ffffff80099c4e94 T schedule
```

---

## 4. Hash Mismatch

현재 promoted boot image에서 kernel blob을 unpack했다.

```text
boot image: workspace/private/inputs/boot_images/boot_linux_v2189_security_p0_stage_fix.img
kernel_size: 49827613
```

SHA 비교:

```text
live boot kernel:
9f4fc72c15ce9f96694023cf8f3f0340651d073acd584853941764cf9756b85a

generated OSRC Image:
823b816036edc991f8e2a88ba88de62d35d86610de505b51afdc34c1c6f8d787
```

판정:

- `hash_match=false`
- 새 `System.map`은 source/layout 참고용으로는 쓸 수 있지만, live V2195 stack IP를
  정확히 심볼화하는 authority는 아니다.

---

## 5. Live Timer Function Anchor

`timer:timer_start` tracepoint format은 디바이스에서 다음처럼 확인됐다.

```text
field:void * timer;     offset:8;  size:8;
field:void * function;  offset:16; size:8;
field:unsigned long expires; offset:24; size:8;
```

V2192 extractor로 2초 bounded read-only freq capture를 수행했다.

```sh
/cache/bin/a90_bpf_trace_extract \
  --event timer:timer_start \
  --field function \
  --mode freq \
  --duration-sec 2 \
  --top 32 \
  --allow-attach
```

결과:

```text
value=18446743524096601436 count=1
value=18446743524089378004 count=1
value=18446743524098566276 count=1
value=18446743524089336004 count=31
value=18446743524110532284 count=1
value=18446743524089903140 count=31
value=18446743524091169020 count=348
value=18446743524096978420 count=1
distinct_printed=8
result=extract-pass
```

hex 변환:

```text
0xffffff800883ed5c count=1
0xffffff800815b4d4 count=1
0xffffff8008a1e884 count=1
0xffffff80081510c4 count=31
0xffffff8009587ebc count=1
0xffffff80081db824 count=31
0xffffff80083108fc count=348
0xffffff800889adf4 count=1
```

의미:

- AP는 timer callback pointer를 raw kernel VA로 회수할 수 있다.
- 이 값은 향후 exact stock map이 있으면 KASLR slide anchor로 사용할 수 있다.
- 현재 generated `System.map`과는 hash가 맞지 않으므로 이 값을 억지로 이름에
  매핑하지 않는다.

---

## 6. V2195 Stack IP 재확인

V2195 raw stack IP:

```text
0xffffff8009a42334
0xffffff8009a42334
0xffffff8009a429d8
0xffffff800819ad8c
0xffffff800819adf0
0xffffff80081131f4
```

generated `System.map`으로 slide 후보를 만들면 `__schedule`, `perf_trace_sched_switch`
등으로 맞는 후보가 나오지만, hash mismatch 때문에 이는 authoritative result가 아니다.
특히 여러 slide 후보가 stack 일부를 그럴듯하게 맞추므로, 현재 단계에서 “symbolized”로
승격하면 과적합이다.

이 과적합 위험은 실제 output에서 확인됐다. candidate map 기준으로는 stack 6/6,
timer 415/415를 동시에 만족하는 slide 후보가 여러 개 나오지만, 일부 후보는
`build_sched_domains`, `copy_siginfo_from_user32`, cfg80211 trace output 같은
문맥상 sched_switch stack과 맞지 않는 이름을 낸다. 이는 “matching map 없이
점수만으로 이름을 붙이면 거짓 symbolization이 가능하다”는 직접 증거다.

---

## 7. Stock Kallsyms Recovery 상태

동일 stock kernel blob은 여러 legacy evidence에 남아 있다.

```text
workspace/private/runs/kernel/v2196-boot-kernel-compare/unpack/kernel
tmp/wifi/v1331-esoc-disasm/Image.decompressed
tmp/wifi/v1915-stock-kernel-service74-static-xref/stock/kernel
```

동일 SHA:

```text
9f4fc72c15ce9f96694023cf8f3f0340651d073acd584853941764cf9756b85a
```

하지만 현재 archive parser `workspace/public/archive/scripts/analysis/esoc_final.py`
는 남아 있는 blob에서 token table을 다시 찾지 못했다.

```text
RuntimeError: no token_table
```

추가 확인:

- `tmp/wifi/v1331-esoc-disasm/vmlinux.raw`는 ELF/vmlinux가 아니라 kernel
  `.config` 텍스트다. symbol authority로 사용할 수 없다.
- `bootunpack/kernel`과 `Image.decompressed`는 같은 SHA의 `UNCOMPRESSED_IMG`
  wrapper blob이다.
- 과거 성공 evidence는 wrapper를 제거한 raw arm64 Image 경로(`Image.stripped` /
  `Image.for-kallsyms`)에서 kallsyms를 찾았다고 기록한다. 이 raw Image는 wrapper
  blob과 SHA가 다른 것이 정상이다.
- 과거 `DISASM_FINDING.md`는 `token_table @ 0x167b6c8`, `token_index @ 0x167b9bf`,
  `relative_base 0xffffff8008080000`, `num_syms = 131833`, `names @ 0x1619310`,
  “Decode is PERFECT”를 기록한다.
- 같은 legacy tree에는 다른 실패 로그(`token_table@0x1948bf0`,
  `num_syms/names anchor not found`)도 공존한다. 즉 데이터가 없다는 뜻이 아니라,
  parser 입력 정규화와 layout 탐색 로직이 drift된 상태다.

따라서 exact P1b의 남은 경로는 둘 중 하나다.

1. stock kernel image의 kallsyms parser를 복구·재검증해 stock `System.map`을 생성한다.
   우선순위는 `UNCOMPRESSED_IMG` wrapper 제거 → raw arm64 Image kallsyms table
   탐색 → 131833개 record decode 재현 → `System.map` 출력이다.
2. vendor/OEM matching `System.map` 또는 unstripped `vmlinux`를 확보한다.

대안으로 BPF/tracefs `%pS` 경로를 쓰는 방법도 가능하지만, trace buffer 출력/formatting
경로를 건드리는 별도 관측 설계가 필요하므로 이번 P1b에는 포함하지 않았다. 이 경로는
빠른 교차검증 후보이지, stock map 복구를 대체하는 영구 artifact는 아니다.

---

## 8. Safety

- OSRC kernel build: host-only.
- boot image write/flash/reboot: 없음.
- live device command: bounded BPF tracepoint read-only capture만 수행.
- `probe_write_user`: 실행 안 함.
- cgroup attach: 실행 안 함.
- Wi-Fi scan/connect, credential, DHCP/routes, external ping: 없음.
- selftest:

```text
selftest: pass=11 warn=1 fail=0 duration=51ms entries=12
```

---

## 9. Next

P1b exact를 닫으려면 **stock System.map 복구**가 우선이다.

권장 순서:

1. `a90_kernel_stack_symbolize.py`는 유지한다. exact map이 생기면 즉시 재사용 가능하다.
2. stock `UNCOMPRESSED_IMG` wrapper를 raw arm64 Image로 정규화하는 단계를 먼저 고정한다.
3. raw Image kallsyms parser를 별도 host-only unit으로 복구한다.
4. parser가 `trace_call_bpf`, `bpf_get_stackid`, `__schedule`, `timer` callback symbols를
   포함하는 stock map을 만들면 V2196 symbolization을 재실행한다.
5. 후보 map 검증은 V2195 stack IP와 V2196 timer function anchors 둘 다로 한다.
6. 그 다음에 WLAN/cfg80211 tracepoint stack/object-chain에 적용한다.
---

## 10. V2197 Update

V2197 recovered the stock embedded kallsyms map from the same live stock kernel
wrapper blob and reran stack symbolization. The V2196 artifact gap is closed for
stock map authority. Stack IP naming is still provisional because multiple
full-stack slides remain. Timer function anchors remain useful raw evidence but
are not yet independent slide authority because multiple slides can map them into
text.

See `docs/reports/NATIVE_INIT_V2197_STOCK_KALLSYMS_SYMBOLIZATION_2026-06-11.md`.
