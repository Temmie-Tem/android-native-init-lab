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
