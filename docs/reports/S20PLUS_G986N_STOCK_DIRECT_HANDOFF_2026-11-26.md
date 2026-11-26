# S20+ 유니로더 직접 기록과 원본 Magisk 커널 인계 대조

대상은 SM-G986N/y2q/G986NKSS8IYC2다. 앞선 물리 실험에서 순정 printk 표식은 원복 후 1건 회수됐고, 메인라인 후보의 두 조기 표식은 모두 0건이었다. 이번 대조는 메인라인 후보의 로더 쪽 기록기를 유지하고, 이후 실행할 커널을 정상 Android의 원본 삼성 커널로 바꾼다. Magisk 부트에서 추출한 원본 커널 51,959,820바이트와 램디스크 890,444바이트를 사용한다.

## 같은 부팅임을 확인하는 방법

초기 코드는 직전 후보와 동일한 128바이트 prebranch 기록기를 쓴다. 새 식별값으로 기록하되 Linux primary_entry 쪽 기록기는 넣지 않는다. 입력 FDT에 있는 순정 부팅 인수와 예약 영역은 보존한다. 별도 RAM에 복사한 순정 트리에는 `/chosen/codex,y2q-stock-direct-v1` 속성 한 개를 추가한다. 초기값은 이 후보의 nonce와 `:U`다. 완전한 프레임과 헤더를 다시 읽어 확인한 직후에만 마지막 상태 바이트를 `C`로 바꾼다. 그 트리를 원본 커널로 넘긴다.

| 후보 Android의 현재 FDT | 같은 부팅에서 읽은 이전 커널 로그 | 판정 |
| --- | --- | --- |
| 새 nonce와 C | prebranch 1건, primary_entry 0건 | 로더 기록과 읽기 확인, 원본 커널 인계, Android에서의 회수를 함께 입증 |
| 새 nonce와 C | prebranch 0건 또는 판독 실패 | 해당 부팅의 로더 기록 확인까지 입증. 스냅샷 회수는 미입증 |
| 새 nonce와 U | 개수 별도 기록 | 인계는 확인됐고 로더의 전체 기록 확인은 성립하지 않음 |
| 현재 속성 없음·다른 값 또는 Android 미관측 | 개수와 별도 | 후보 Android 귀속 미확인. 물리 Download 원복 경로 사용 |

후보 AP는 `ad9caa48da7c58854b177d29e6552abc81eb7487b32d944a4df7c4f9baa7e696`이다. 원본 AP는 `1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2`다. 두 AP에서 각각 유일한 멤버 `boot.img.lz4`를 풀어 64 MiB 부트 이미지와 대조했다.

## 호스트 검증

IYC2의 모델 적재 위치 64개에서 펌웨어 산출값과 로더의 FDT·initrd 위치가 일치했다. QEMU에 실제 후보 바이트를 넣은 여섯 대조에서 원본 삼성 Image 전체와 Magisk 램디스크를 비교하고, 삼성 커널 첫 명령을 실행했다. 순정 입력 트리와 출력 트리의 모든 노드·속성·예약 항목은 새 속성 하나를 제거한 뒤 정규화해 비교했다. 링 래핑과 페이지 경계 등 정상 세 경우에는 C와 prebranch 한 건, 허용 정보 누락·다른 로그 magic·커서 255에서는 U와 0건을 확인했다. 별도로 순정 스냅샷 모형에 이 RAM을 넣고 IYC2 Android Toybox와 Magisk BusyBox 판독기로 256바이트와 2,097,136바이트의 양성, 255바이트의 음성을 검증했다.

정확한 부트 쌍과 호스트 근거는 비공개 `workspace/private/analysis/s20plus-y2q-stock-direct-20261126/`의 `packaged3/pair.json`, `qualification/final3/results.json`, `stock-reader.json`에 있다. 체인 안의 두 아키텍처 진입 상태는 EL1 및 EL2에서 검사했다. QEMU의 성공 조건은 실기 Android가 뜰 것이라는 보장을 제공하지 않는다.

## 실기 범위

[전용 실행기](../../workspace/public/src/scripts/revalidation/s20plus_g986n_stock_direct_f1.py)는 한 번의 입회 승인으로 후보를 전송하고 현재 FDT·로그·Magisk 루팅을 측정한다. 인증된 후보 Android에서 원본 AP로 되돌아갈 때는 같은 부팅과 포트, FDT 값을 다시 확인하고 ADB로 Download에 진입한다. 후보 Android가 인증되지 않으면 물리 Download로 원복한다. 두 경로는 원본 AP 한 번만 공유하며, 원복 후 루팅과 후보 전용 속성의 부재를 확인한다. [S20+ 전용 범위](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md#s20-stock-magisk-direct-loader-marker-under-one-attended-approval)

## 실기 결과

후보 전송 후 관측 시간 안에 같은 기기의 정상 루팅 Android를 식별하지 못했다. 후보 부팅에서 FDT 속성과 로그 표식을 판독하는 단계까지 도달하지 않아 표식 개수는 미측정이다. 물리 Download로 원본 AP를 복구했고, 처음 관측한 원복 부팅과 같은 부팅에서 Magisk 30.7(30700), UID 0, SELinux Enforcing, PID 1 `/system/bin/init` 및 후보 전용 FDT 속성의 부재를 확인했다.

| 한국 시각 | 관측 |
| --- | --- |
| 21:57:03 | 원본 Android의 이전 로그 2,097,136바이트에서 새 표식 0건. 후보 FDT 속성 없음 |
| 21:57:41 | 대조 후보 AP 1회 전송 완료 |
| 22:00:43 | 후보 Android 관측 종료. 후보 시점의 태그·로그 판독 기록 없음 |
| 22:01:27–35 | 같은 USB 포트에서 물리 Download 확인, 원본 Magisk AP 1회 전송 완료 |
| 22:02:15 | 첫 복귀 Android 부팅 ID 확인 |
| 22:04:41–42 | 같은 부팅에서 원본 건강과 후보 태그 부재 확인, 종료 및 공유 잠금 해제 |

초기 원복 관측 프로세스가 첫 부팅 ID를 기록한 뒤 최종 건강 결과를 남기기 전에 종료했다. 이어진 건강 확인은 공용 세션 잠금이 사용 중이어서 대기한 뒤 완료했다. 추가 AP 전송은 0회였다. 종료 판정은 `NO_PROOF_STOCK_DIRECT_MARKER_ORIGINAL_MAGISK_RESTORED`다. 이 결과만으로 로더 표식 쓰기, 원본 커널 분기 실행 및 그 후 어느 단계에서 진행이 멈췄는지를 가를 수 없다. 복구된 원본의 FDT 속성 부재는 후보 시점의 측정을 대신하지 않는다.

비공개 실행은 `s20plus-g986n-stock-direct-f1/run-1795697759773921837`, 검토된 소스 커밋은 `29221b0837`, 종료 기록 SHA-256은 `e0118d4fcc77d6aa17b5656b771db30a5bb7261476dfdee71e0bd702eb42dde7`이다.

## 원복 첫 부팅의 별도 판독과 원인 대조

11월 26일 22:29 KST에 종료된 실험과 별개의 읽기 전용 판독을 마쳤다. 판독 전후의 기기·포트·부팅 ID가 22:02에 처음 관측한 원복 Android와 일치했다. Magisk 30.7(30700), UID 0, Enforcing, PID 1 `/system/bin/init`도 양쪽에서 일치했다. 기기 안에서 `/proc/last_kmsg`의 공시 길이 전체를 검사했다. 이번 후보의 완전한 `prebranch` 프레임은 발견되지 않았다. 원본 삼성 커널에는 `primary_entry` 기록기를 넣지 않았으므로 그 표식의 부재로 커널 진입을 판정할 수 없다. 판독에는 현재 저장소 공통 규약을 적용했다. 독립 검토 입력 `b7bbea7f…`에 대해 지적 0건으로 통과했고 부팅 변경·재실행 방지를 포함한 테스트 5건이 통과했다. [판독 범위](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md#s20-first-return-stock-direct-marker-readback-d0)

| 한국 시각 | 호스트 커널에서 확인한 같은 USB 포트의 이벤트 |
| --- | --- |
| 21:57:41.804 | 후보 전송을 마친 Download 연결 해제 |
| 22:00:43.676 | 후보 관측 종료까지 USB 열거, 장치 설명자 오류, 포트 재설정 기록 없음 |
| 22:01:23.245 | 연결 해제 221.441초 뒤 물리 Download 장치 열거 |
| 22:01:35.949 → 22:02:14.162 | 원본 전송 뒤 연결 해제, 38.213초 뒤 Android 장치 열거 |

Odin의 두 성공 영수증이 지목한 AP를 다시 열고 TAR 멤버·MD5와 디코딩한 부트 이미지를 검증했다. 후보는 원본 삼성 커널 51,959,820바이트 앞에 로더 3,203,072바이트를 추가했다. 커널은 마지막 바이트까지 일치했고, Magisk 램디스크와 부트 이미지 속 삼성 DTB, Android 헤더의 커널 명령줄도 동일했다. Android v2 첫 헤더 페이지에서 달라진 필드는 커널 크기와 이미지 ID였다. 두 이미지의 내장 vbmeta는 같았고 avbtool은 양쪽 모두 boot 해시 불일치를 보고했다. 이 값으로 후보만 실패한 이유를 가릴 수 없다. 펌웨어가 후보를 실행했는지는 USB 전송 완료만으로 알 수 없다.

추가 EL1 QEMU 대조에서는 같은 FDT 입력을 두고 원본 삼성 커널에 직접 진입한 경우와 실제 후보 바이트를 통해 진입한 경우를 비교했다. 각 경로에서 삼성 코드가 FDT 인수를 보관하고 초기 페이지 테이블을 만든 뒤 같은 가상 주소로 분기해 첫 명령을 실행했다. 특정 배치에서 로더의 복사와 위치 이동을 거친 커널도 이 지점에 도달한다.

실기에서 아직 검사하지 않은 구간도 특정했다. 이전 원본 Android의 FDT 관측은 4.5 MiB 메인라인 목적지를 검사했다. 이번 로더는 약 67.25 MiB인 삼성 커널의 **전체 런타임**이 한 RAM 뱅크 안에 있어야 복사를 시작한다. 후보가 사용할 범위와 기존 목적지가 겹치는 부분은 4 MiB다. 동일 RAM을 물리적으로 연속된 두 뱅크로 기술해 이 넓은 구간만 경계를 넘게 만든 QEMU 대조에서, 기존 두 구간은 한 뱅크에 들어갔고 이번 후보는 목적지 검사에서 `reject_range`로 가서 표식 전에 멈췄다. 실기 FDT에 같은 경계가 있는지는 미측정이다. 입력 FDT의 정확한 위치·형태, 표식 기록 허용 조건, 원복 중 덮어쓰기 역시 구별되지 않았다. 과거 순정 printk 대조에서 같은 물리 복구 경로로 기록을 회수한 적은 있다.

별도 판독은 `workspace/private/runs/s20plus-g986n-stock-direct-readback-d0/observation/`에, USB·이미지 대조와 두 VM 실험은 `workspace/private/analysis/s20plus-y2q-stock-direct-20261126/postclosure/`에 보존했다. 원래 실기 종료 기록은 그대로이며 후속 판독의 AP 전송과 재부팅은 0회다.

## 11월 27일 원본 FDT의 삼성 커널 전체 목적지 판독

11월 26일의 두 응답 중단은 대화의 종료 기록과 완료된 명령으로 구분했다. 22:23:08 KST 첫 중단 전에 원복 부팅 건강 확인(22:13:42), 같은 포트의 USB 이력 대조(22:15:57), 판독기 초안 테스트 4건(22:22:11)이 끝났다. 당시 원복 부팅의 표식은 아직 미측정이었다. 22:29:32 두 번째 중단 전에는 부팅 변경 검사를 수정하고 테스트 5건과 독립 검토를 통과했다. 전송 AP 대조는 22:28:50, 첫 원복 부팅의 표식 판독과 결과 저장은 22:29:10에 끝났다. 직접 진입·유니로더 경유의 가상 주소 전환 대조와 분할 뱅크 실험은 이후 호스트에서 수행했다.

11월 27일 01:00:59 KST, 첫 원복 Android와 기기·USB 경로·부팅 ID가 일치하는 상태에서 원본 커널이 공개한 FDT를 읽었다. 단일 RAM 구간은 올라온 메모리 노드 안의 `reg` 항목 하나로 판정했다. 후보에 내장된 배치 정의에서 시작점과 런타임 크기를 가져왔다. [실기 판독 범위](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md#s20-original-magisk-vendor-runtime-fdt-geometry-d0)

| 원본 Magisk 부팅에서 측정한 항목 | 결과 |
| --- | --- |
| 삼성 커널 목적지 | `[0xa4880000, 0xa8bbf000)`, 총 70,512,640바이트(67.2461 MiB). 단일 RAM 뱅크에 전부 포함 |
| 목적지와 FDT의 고정 예약 또는 initrd 중첩 | 두 항목 모두 없음 |
| 원본 FDT | 931,599바이트. RAM 구간 3개, 헤더·노드의 고정 예약 30개, 동적 풀 선언 13개 |
| 판독 전후 | 같은 기기·포트·부팅 ID, Magisk 30.7(30700), UID 0, Enforcing, PID 1 `/system/bin/init` |

이 원본 FDT에서 목적지가 RAM 뱅크 경계를 넘는다는 가설은 배제된다. 동적 풀의 실제 할당 주소, 후보 때 펌웨어가 넘긴 FDT 포인터와 initrd 위치, 후보의 실제 정지 지점은 이 판독으로 정해지지 않는다. 이번 조회는 기기에서 FDT를 집계해 43바이트를 반환했다. 원시 트리는 기기에 두었고, 표식 재판독·재부팅·AP 전송은 없었다. 새 판독 테스트 3건과 기존 회귀 테스트 12건이 통과했다. 별도로 실제 Magisk ARM64 BusyBox를 사용한 호스트 대조에서 정확한 끝 경계, 연속된 두 뱅크, 1바이트 부족, 1바이트 예약 중첩을 구분했다.

비공개 측정 결과는 `workspace/private/runs/s20plus-g986n-vendor-runtime-layout-d0/d0-46cbcbc3a71d44848c24f09f2a4b2447/result.json`에 있다. SHA-256은 `293ab6a502aeae7b31596fbee82687edd69c92de4dd2cc992bbc725b0a67c50c`이다.

## 11월 27일 initrd와 입력 FDT 조건 대조

소모된 후보의 원본 배치 정의를 기준으로 initrd 예상 구간은 `[0xaff25000, 0xafffe64c)`(890,444바이트), 입력 FDT의 예상 물리 주소는 `0xafd24000`이다. 두 AP를 다시 디코딩해 실제 Image와 램디스크 크기를 IYC2 펌웨어의 기존 배치 모델에 넣었다. 원본과 후보 각각 64개 적재 위치에서 모델은 같은 initrd 시작·끝과 FDT 주소를 산출했다. 모델은 해당 EFI 메모리 영역 조회가 성공한 경로를 전제로 한다.

같은 후보 바이트와 원본 보드 트리로 QEMU에서 다음 세 경로를 대조했다. 중단점으로 `y2q_shape` 진입과 반환값을 읽고 이후 실행한 분기를 확인했다.

| 호스트 대조 입력 | 후보에서 직접 관측한 경로 |
| --- | --- |
| 기존 정상 입력 | FDT 형태 검사 성공, 스택 설정 지점과 `prebranch` 도달 |
| FDT 내용은 그대로 유지하고 입력 포인터와 트리의 물리 위치를 4 KiB 낮춤 | FDT 형태 검사에서 0 반환, `reject_fdt` 도달 |
| FDT 포인터 고정, chosen의 initrd 시작·끝만 각각 4 KiB 낮춤 | FDT 형태 검사 통과, 첫 구간 검사에서 `reject_range` 도달 |

원본 Android용 [입력 비교 판독](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md#s20-restored-magisk-fdt-input-comparisons-d0)은 같은 복귀 부팅의 원시 FDT를 기기 안에서 해석한다. initrd 시작·끝·크기와 루트 compatible을 독립적으로 분류한다. 선택된 노드 상태, 예약 reg 길이, 예상 입력 FDT와 예상 initrd의 단일 뱅크 포함·고정 예약 중첩도 함께 확인한다. 이 판독은 실제 펌웨어 x0, 부팅 순간의 initrd 내용 또는 이후 동적 할당 주소를 읽지 않는다. 호스트 대조 원본은 비공개 `postclosure/input-boundary-results.json`에 있다.

01:51:39 KST의 실기 판독에서 기기·포트·부팅 ID와 Magisk 건강 상태가 첫 원복 기록과 일치했다. initrd의 시작, 끝, 크기는 모두 후보 예상값과 일치했다. 931,599바이트 FDT의 chosen 상태와 검사한 예약 reg 크기 조건을 통과했다. 예상 위치의 입력 트리와 예상 initrd는 각각 단일 RAM 뱅크에 들어갔고 고정 예약과 겹치지 않았다. 반면 루트 compatible은 존재했지만 후보가 요구하는 정확한 10바이트 `qcom,kona\0`와 달랐다. 이 첫 판독은 실제 문자열이나 목록 형식을 수집하지 않았다. 결과 SHA-256은 `b7ed6b6b56545aee09aab99b0e24dda426cdb9109b2f40927a6a565ba2a27505`다.

후보와 원본의 동일한 DTB 묶음에는 트리 네 개가 있었다. 셋은 루트 compatible이 그 10바이트였고 하나에는 해당 속성이 없었다. 기존 VM 보드 입력 여섯 개는 모두 10바이트였다. 정상 입력에서 루트 compatible만 바꾼 세 QEMU 대조(다른 단일 값, `qcom,kona`를 포함한 목록, 끝에 NUL을 하나 더 붙인 값)에서는 모두 형태 검사 통과 후 첫 `y2q_interval`에서 `reject_range`로 분기했다. 정상 대조는 같은 후보에서 `prebranch`에 도달했다. 당시 실기도 원본 복귀 부팅과 같은 루트 값을 받았다면 이 검사만으로 기존 무표식 결과를 설명할 수 있다. 후보 부팅 당시 입력이나 실행 PC는 미측정이다.

같은 기기·포트·첫 원복 부팅에서 01:56:46 KST에 루트 compatible 형식을 좁혔다. 정상 NUL 구분 문자열 목록이며 완전한 `qcom,kona` 항목과 그 밖의 항목이 함께 있다. 다른 항목의 원문은 수집하지 않았다. initrd 및 예약 영역 판정은 첫 판독과 일치했다. 두 판독의 Magisk 30.7, UID 0, SELinux Enforcing도 일치했다. 두 번째 결과 SHA-256은 `421e27c7e09e413e28a657d081a818e0f7a5e5c6e760b7a9304be8e6eda8d9f9`이다.

호스트 전용 복사본에서 `y2q_interval`의 루트 검사만 바꿨다. 전체 속성이 정상 종료된 비어 있지 않은 문자열 목록이고, 그 안에 완전한 `qcom,kona` 항목이 있으면 통과한다. 원본을 다시 빌드한 대조의 바이트는 실제 전송했던 후보와 일치했다. 수정본은 링커 검사와 ARM64 스택 설정 전 명령 검사를 통과했다. 11개 QEMU 대조 중 기존 단일 값과 대상 항목이 목록의 처음·중간·끝에 위치한 4건이 `prebranch`를 지나 원본 삼성 커널 첫 명령을 실행했다. 4건 모두 FDT의 확인 문자 C와 기준 시드에서 기대한 표식을 포함한 링 전체 바이트가 일치했다. 나머지 7건(다른 값, 부분 문자열, 추가 빈 항목, 종료 누락, 비정상 문자, 항목 수 초과, initrd 위치 불일치)은 표식 전에 거부됐다.

수정본과 재현 자료는 비공개 `workspace/private/analysis/s20plus-y2q-stock-direct-20261126/postclosure/root-list-h0/`의 `guard-list.diff`, `build.json`, `results.json`에 있다. 통제된 비교를 위해 이전 VM의 식별값을 재사용했다. 원복 부팅에서는 읽기만 수행했고, 이 복사본으로 기기용 후보 AP를 만들거나 전송하지 않았다. 물리 후보의 다음 판별점은 고유 표식을 가진 목록 지원 로더가 원본 삼성 커널을 거쳐 Android에서 관측되는지다.

## 11월 27일 문자열 목록을 지원하는 실기 후보 준비

새 후보는 정상 NUL 구분 목록에서 완전한 `qcom,kona` 항목을 확인한다. 첫 실행의 호스트 전용 식별값은 재사용하지 않았다. 이번 128바이트 `prebranch` 프레임과 `/chosen/codex,y2q-stock-list-v1` 속성은 새 식별값을 공유한다. 속성은 U에서 시작해 기록을 다시 읽어 일치할 때 C로 바뀐다. 단일 boot 전송에 사용하는 후보 AP의 SHA-256은 `6d2ba177d6447fc166580d07e9bc34a4d771f4c97aabc272f9e7756a26463f25`이며 원복 AP는 `1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2`다. 두 AP를 각각 풀어 boot.img.lz4 단일 멤버, 64 MiB 디코딩 이미지, 원본 삼성 커널·Magisk 램디스크·삼성 DTB를 대조했다.

실제 후보 바이트로 QEMU 여섯 경우를 시험했다. 쓰기 조건을 충족한 세 경우에는 새 표식을 읽은 뒤 원본 커널로 진입했고, 허용 인수 누락·잘못된 로그 헤더·짧은 커서에서는 표식 없이 원본 커널로 진입했다. 세 경우의 스냅샷을 순정 Android 도구로 판독해 256바이트와 2,097,136바이트 양성 및 255바이트 음성을 확인했다. 독립 대조에서도 목록 중간에 정확한 항목이 있는 입력은 삼성 커널 첫 명령을 실행했다. 잘못된 호환성 목록 또는 이동된 initrd를 준 여덟 경우는 첫 스택 설정 전에 거부됐다. 이 증거는 호스트 검증이다.

[전용 실행기](../../workspace/public/src/scripts/revalidation/s20plus_g986n_stock_list_f1.py)는 승인 한 번에 후보 AP 1회와 원본 AP 1회를 묶는다. 같은 포트에서 후보의 새 Android 부팅, Magisk 루팅, 이번 FDT 태그와 이전 로그의 표식을 대조한다. C와 정확한 prebranch 1건, primary_entry 0건이어야 기록 회수를 확정한다. 인증된 후보는 ADB로 원복하며, 후보를 인증할 수 없으면 실행기의 안내에 따라 물리 Download로 진입한다. 원복 성공 판정에는 원래 기기의 새 Android 부팅, Magisk 루팅 및 후보 전용 속성 부재가 필요하다. [입회 및 원복 범위](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md#s20-stock-kernel-compatible-list-control-under-one-attended-approval)

호스트 자격 자료는 비공개 `workspace/private/analysis/s20plus-y2q-stock-list-20261127/qualification.json`, 독립 후보 검증은 같은 위치의 `independent/result.json`에 있다. 두 SHA-256은 각각 `125d68324a6bdcb7192e9b26c0726032c45b8bf19c4abe628eea6e6900327d84`, `99cdd7204b8ab5dc0d94bcc3d7f963b7fbb85b535ba9eb5179ed7df7e05cb81e`다.

실행기 독립 검토 입력은 `e6838028f32296f2436477e07700f0e0a6e841bbe9e4be39d467940a1d279085`였고 미해결 지적은 0건이었다. 검토한 활성 소스와 호스트 검증을 확인한 뒤 02:15:35 KST에 SM-G986N의 이전 원복 첫 부팅 ID, 같은 포트, Magisk 30.7(30700), UID 0, Enforcing, PID 1 `/system/bin/init`을 확인해 15분 승인 토큰을 발급했다. 발급 시점에 수락 기록과 전송 실행 디렉터리는 없었다.
