# SM-S906N FYG1 모뎀 서명과 복구 근거

운영자 소유 S22+의 FYG8 배포본에는 FYG1 모뎀 펌웨어가 들어 있다. 순정 드라이버와 메인라인 Linux 7.2.11의 SM8450 드라이버 모두 모뎀 기동을 보안 영역의 인증 결과에 의존한다. **서명된 실행 코드를 바꾸고 기존 서명을 유지한 CP는 이 검증을 통과할 수 없다.** 실제 단말에서 수정 CP를 시도해 얻은 거부 기록은 없다. 이번 조사는 보관 파일과 과거 실기 기록만 사용했다.

## 11월 19일 현재 확인 범위

| 질문 | 판정과 근거 |
| --- | --- |
| 순정 FYG1의 서명과 기동을 확인했는가? | **확인.** 호스트에서 서명과 세그먼트 해시를 검증했다. 보관된 FYG8 실기 로그에서 순정 FYG1의 기동 완료도 확인했다. [서명과 부팅 기록](#순정-서명과-부팅-기록) |
| PAS가 오류를 반환해도 순정 커널이 기동을 계속하는가? | **기동 절차 중단.** 순정 드라이버 실행 코드는 PAS의 오류를 전달하고 오류 반환 또는 커널 패닉 경로로 간다. [순정 커널의 오류 처리](#fyg8-보안-펌웨어의-인증-실패-처리) |
| 서명 실패 시 모뎀 리셋을 해제하기 전에 종료하는가? | **FYG8에서의 선후 관계는 미확인.** Qualcomm은 인증 후 리셋을 해제하는 정상 순서를 설명한다. 확인한 SM8450 공개 자료에는 모뎀 서명 실패 시 리셋을 계속 유지한다는 보장이 없다. 두 보안 이미지에서 그 실패 경로를 직접 추적하지 않았다. [공개 자료의 적용 범위](#qualcomm-공개-자료가-설명하는-리셋-순서) · [FYG8 판정 근거](#모뎀-리셋-상태를-판별할-수-있는가) |
| 현재 ML050에서 기동하거나 순정 CP로 원복한 실적이 있는가? | **현재 ML050은 모뎀 기동에 필요한 구성이 빠져 있다.** 순정 CP 복구 파일은 배포본과 일치한다. 실기에서 복구까지 확인한 전송 대상은 부트 이미지였다. [ML050 구성 대조](#메인라인-커널과-비교) · [CP 복구 근거](#순정-cp로-돌아올-수-있는가) |

## 순정 서명과 부팅 기록

- 정식 배포 ZIP 안의 CP와 별도로 보관한 CP 아카이브가 바이트 해시로 일치한다. 아카이브의 유일한 멤버인 `modem.bin.lz4`를 호스트에서 풀어 대조했다. 내부 FAT16에서 읽은 모뎀 메타데이터·서명 세그먼트와 파일 데이터가 있는 ELF 항목 28개(ELF 헤더 포함)가 모두 보관 사본과 일치했다. 각 항목의 SHA-384 값도 서명된 해시표와 일치했다. [순정 배포본의 기준 해시](../operations/S22PLUS_FYG8_STOCK_FIRMWARE_EVIDENCE_POLICY_2026-07-08.md)
- 해시표·메타데이터를 포함한 서명 대상에 대해 내장된 Samsung Electronics 인증서 공개키로 ECDSA P-384/SHA-384 서명을 검증했다. 서명용 인증서에서 중간 인증서, 자체 서명 루트까지 인증서 서명도 검증했다. 비교용 다이제스트에서 한 비트만 다르게 주자 기존 서명의 검증이 실패했다. 장치에 고정된 신뢰 루트 값은 독립적으로 읽지 않았다. Qualcomm은 서명된 해시 세그먼트로 개별 ELF 세그먼트를 인증하는 구조를 설명한다. [Qualcomm 이미지 인증 설명](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/secure-boot-and-image-authentication.pdf)
- 순정 기기 트리의 모뎀과 순정 `qcom_q6v5_pas.ko`의 기기 매칭 정보를 대조했다. 모듈의 로드 함수는 MDT 로더를 호출하고, 시작 함수는 `qcom_scm_pas_auth_and_reset`의 결과를 검사한다. 원본 캡처 해시를 대조한 7월 13일 실기 bugreport에는 이 드라이버가 모뎀에 연결되어 `modem.mdt`를 기동하고 모뎀이 준비된 기록이 있다. 같은 기록의 베이스밴드는 `S906NKSS7FYG1`이고 Android 부트로더는 잠금 해제·`orange` 상태였다. 이 조합이 증명하는 범위는 **AP 잠금이 해제된 단말에서 순정 FYG1이 기동했다**는 것이다. [순정 모듈 인벤토리](../module-map/s22plus-fyg8-super/inventory.tsv) · [삼성의 부트 신뢰 체인 설명](https://docs.samsungknox.com/admin/fundamentals/whitepaper/samsung-knox-mobile-security/system-security/trusted-boot/)

### FYG8 보안 펌웨어의 인증 실패 처리

**PAS가 오류를 반환하면 FYG8 순정 커널은 모뎀 기동을 성공 처리하지 않는다.** 보안 펌웨어 안에도 서명 실패를 나타내는 근거가 있다. 다만 FYG1의 서명 실패를 입력으로 받아 보안 영역이 이 모뎀의 리셋을 끝까지 유지하는 인과관계는 이번 H0 분석에서 입증하지 못했다.

- **보안 이미지.** 전체 배포 ZIP에서 꺼낸 BL의 크기와 SHA-256을 저장소 기준값과 대조했다. 그 안에서 압축을 푼 `tz.mbn`, `hypvm.mbn`, `XblRamdump.elf`가 각각 기존 보관본과 바이트 단위로 일치했다. `XblRamdump.elf`의 PIL(주변장치 이미지 로더) 진단표에는 서명 실패와 메타데이터 인증 전에 세그먼트 검증을 요청한 경우가 구분돼 있다. `tz.mbn`의 실행 세그먼트에서 같은 릴리스의 서명 실패, 세그먼트 검증 상태 오류, 상태 전이 오류, 기동 실패 진단값을 구성하는 명령 쌍을 확인했다. `hypvm.mbn`에는 인증·리셋 요청을 TZ로 전달하는 경로를 지칭하는 문자열과 TZ가 바쁠 때의 진단이 있다. 진단값만으로는 대상 주변장치, 해당 경로의 실제 실행, 실패 이후의 리셋 상태를 특정할 수 없다. [순정 BL 기준값](../operations/S22PLUS_FYG8_STOCK_FIRMWARE_EVIDENCE_POLICY_2026-07-08.md)
- **순정 커널의 오류 처리.** `mdt_loader.ko`는 PAS 이미지 초기화가 실패하면 로드 오류 경로로 간다. 이후 인증·리셋 요청에서 `qcom-scm.ko`는 보안 호출 자체가 성공해도 서비스가 반환한 오류를 호출자에게 전달한다. FYG8 모뎀에 연결된 `qcom_q6v5_pas.ko`에서 이 오류는 정리 후 오류 반환 또는 커널 패닉으로 이어진다. 두 경로 모두 정상 기동 완료로 이어지지 않는다. 보안 영역의 서명 검사가 정확히 어느 호출에서 실패하는지는 별도 문제다.
- **실기 기록.** 7월 13일 보관한 bugreport 두 개의 스트림 해시를 확인하고 각 `dumpstate.txt`와 보존된 복구 커널 로그를 조회했다. 두 본문에서 FYG1과 모뎀 기동 완료가 확인됐다. 두 본문에 나타난 서명 실패 메시지는 직전 이미지 이름과 발신자가 각각 `vbmeta.img`와 ABL이었다. 조회한 기록에서 FYG1 서명 거부와 모뎀 기동 차단이 연결된 사례는 찾지 못했다. 두 캡처 중 앞선 예행의 스트림은 해시와 EOF가 맞지만 캡처 전체 판정은 실패여서 보조 자료로만 사용했다.

비공개 근거는 기존 증거 디렉터리의 `fyg8-pas-enforcement.json`에 있다. 이미지·모듈 해시, 진단값 대조 방식과 두 캡처의 판정을 기록했다. 이번 분석은 보관 자료만 읽었다.

#### 모뎀 리셋 상태를 판별할 수 있는가

같은 BL에서 검증한 세 파일의 SHA-256을 다시 대조하고, 이번에는 두 보안 이미지의 모뎀·리셋 관련 진단과 `XblRamdump.elf` 진단표의 **필드 의미**를 확인했다. `tz.mbn`에는 PIL 서명 실패 진단값이 있지만 이 값 자체에는 모뎀 식별자나 리셋 상태가 없다. `hypvm.mbn`의 인증·리셋 요청 오류 문구 중 하나는 TZ가 바쁜 경우를 명시한다. 따라서 요청 오류만으로 실패 원인을 서명으로 특정할 수도 없다.

같은 배포본의 `PIL_SUBSYS_ERROR_STATE` 포맷에 담기는 값은 **요청한 하위 시스템 상태**와 **PIL 처리 결과**다. 클럭·리셋 처리 오류 항목 `PIL_SUBSYS_ERROR_CLK_RESET_PROC`의 포맷에는 상태값 필드가 없다. 이 진단들로는 FYG1 서명 판정 전후의 모뎀 리셋 변화를 읽을 수 없다. 두 이미지에서 확인한 정적 근거로는 실패 경로가 리셋 해제를 건너뛰는지, 이미 해제된 리셋을 다시 거는지 판별되지 않는다. 후자를 관측했다는 뜻도 아니다.

#### Qualcomm 공개 자료가 설명하는 리셋 순서

**SM8450을 명시한 문구.** Qualcomm의 *SPU260 Security Target Lite* §9.1.2.1(62쪽) 5단계는 콜드 부트 중 TME가 플랫폼 구성요소를 인증하고 “taking them out of reset in case of successful authentication”이라고 설명한다. 같은 절에서 7단계의 리셋 해제 대상은 보안 프로세서(SP-CPU)이고, 10단계에서 서명 실패 시 실행을 중단하는 대상은 그 프로세서가 검사하는 MCP 이미지다. 이 절에서 SM8450 모뎀(MPSS)의 런타임 PAS 실패 동작까지 명시하지는 않는다. [Qualcomm 보안 목표서 62쪽](https://www.commoncriteriaportal.org/files/epfiles/NSCIB-CC-0436062-STLite_revAC.pdf#page=62)

**`80-PV345-14` Rev. AE 원문 확인 결과.** Qualcomm 보안 목표서 §3.2.6은 고객에게 제공하는 Agile 데이터베이스에서 표 3-1의 안내서를 내려받을 수 있다고 설명한다. 표에는 *SM8450/SM8475 Secure Boot Enablement*의 문서 번호·Rev. AE·PDF 형식이 기재돼 있다. 인증 보고서 §2.5도 같은 리비전을 제품과 함께 고객에게 제공하는 문서로 열거한다. [배포 경로 22쪽](https://www.commoncriteriaportal.org/files/epfiles/NSCIB-CC-0436062-STLite_revAC.pdf#page=22) · [문서 목록 24쪽](https://www.commoncriteriaportal.org/files/epfiles/NSCIB-CC-0436062-STLite_revAC.pdf#page=24) · [인증 보고서 14쪽](https://www.commoncriteriaportal.org/nfs/ccpfiles/files/epfiles/NSCIB-CC-0436062-CR%20v1.0.pdf#page=14)

2026-11-19에 Qualcomm 비로그인 검색에서 정확한 문서 번호를 조회한 결과는 0건이었다. 공개 웹에서 제목과 번호로 찾은 인증 PDF 두 개에는 내장 첨부파일이 없었고, 해당 목록 페이지에도 원문 링크가 없었다. **Rev. AE 본문을 확보하지 못했으므로, 이 안내서에 MPSS 서명 실패 시 리셋 해제 여부를 명시한 대목이 있는지는 미확인이다.** [Qualcomm 검색 접근 범위 안내](https://www.qualcomm.com/support/product-faqs#urls)

**모뎀에 적용할 수 있는 근거.** Qualcomm의 Mukesh Ojha는 기존 QHEE 시스템에서 하이퍼바이저가 보안 영역(TZ)에 인증을 요청하고, 인증 완료 후 주소 변환을 설정한 다음 원격 프로세서의 리셋을 해제한다고 설명한다. 해당 패치의 시험 플랫폼은 SA8775P다. 별도로 SM8450 MPSS를 지원하는 공개 커널 드라이버는 `modem.mdt`를 사용하고, PAS 인증·리셋 호출이 오류를 반환하면 모뎀 준비 신호를 기다리는 단계에 들어가지 않는다. [Qualcomm 엔지니어의 PAS 설계 설명](https://lists.openwall.net/linux-kernel/2025/10/13/510) · [SM8450 모뎀 드라이버 설정](https://android.googlesource.com/kernel/common/+/88d92fb1c034922572bab93482ac9cc61d4ba43c/drivers/remoteproc/qcom_q6v5_pas.c#1164) · [같은 드라이버의 오류 처리](https://android.googlesource.com/kernel/common/+/88d92fb1c034922572bab93482ac9cc61d4ba43c/drivers/remoteproc/qcom_q6v5_pas.c#314)

**FYG8 판정.** 이 자료들은 인증 성공을 정상 기동의 선행 조건으로 해석할 근거가 된다. FYG8 순정 드라이버에서도 PAS 오류 시 기동 중단을 확인했다. 다만 오류가 반환되기 전까지 물리 리셋이 한 번도 해제되지 않았다는 SM8450 모뎀 명세나 FYG1 실패 관측은 확보하지 못했다. [FYG8 순정 드라이버와 보관 로그](#fyg8-보안-펌웨어의-인증-실패-처리)

## 메인라인 커널과 비교

| 대상 | 모뎀 기동 경로와 판정 |
| --- | --- |
| 순정 FYG8 커널 5.10.226 | 실기에서 순정 FYG1 기동을 확인했다. AP에서 수정한 부트 이미지를 실행할 수 있다는 사실은 모뎀의 서명 수락 여부까지 입증하지 않는다. |
| 업스트림 Linux 7.2.11 | SM8450 MPSS용 PAS 드라이버는 `modem.mdt`를 대상으로 한다. 펌웨어 로드 후 보안 영역에 인증·리셋 해제를 요청하며, 실패하면 오류 경로로 빠진다. 성공한 경로에서만 모뎀 기동을 기다린다. 커널을 교체해도 이 드라이버가 CP 서명에 대한 새 신뢰 권한을 제공하지 않는다. [사용한 업스트림 소스 버전·해시](../../workspace/public/src/mainline/s22plus_canary_h0/sources.json) |
| S22+에서 사용한 ML050 빌드 | 실제 로더 입력의 Image·DTB와 빌드 설정을 준비 기록의 해시로 대조했다. `7.2.11-g0q-ram-h0`는 `CONFIG_REMOTEPROC`가 꺼져 있고, 컴파일된 DTB의 MPSS 노드도 `disabled`다. **이 빌드에는 순정·수정 CP 어느 쪽이든 새로 기동하는 해당 드라이버 경로가 없다.** [g0q 기기 트리](../../workspace/public/src/mainline/s22plus_canary_h0/g0q.dtsi) |

### ML050에 서명된 순정 FYG1을 그대로 공급할 수 있는가

현재 ML050으로는 기동할 수 없다. FYG8 부트 이미지의 내장 설정, 보관한 FYG8 Android의 실제 기기 트리와 7월 13일 부팅 기록을 ML050 로더에 넣은 Image·DTB·ramdisk 및 해당 빌드 설정과 대조했다.

| 항목 | 순정 FYG8 | ML050 |
| --- | --- | --- |
| 커널과 드라이버 | 커널에 `CONFIG_REMOTEPROC=y`가 있고 vendor 모듈에 `qcom_q6v5_pas.ko`와 `mdt_loader.ko`가 있다. 실기 기록에 PAS 드라이버가 모뎀에 연결됐다. | `CONFIG_FW_LOADER=y`, `CONFIG_QCOM_SCM=y`, SMEM·SMP2P 지원은 있다. 그러나 `CONFIG_REMOTEPROC`가 꺼져 있어 SM8450 모뎀을 기동할 `QCOM_Q6V5_PAS` 드라이버가 빠졌다. ramdisk에도 커널 모듈이 없다. |
| 모뎀 기기 트리 | `qcom,waipio-modem-pas` 노드가 `ok`다. XO 클럭, CX/MX 공급, 인터커넥트, 모뎀 인터럽트와 공유 메모리 연결을 선언한다. | 드라이버가 인식하는 `qcom,sm8450-mpss-pas` 노드는 있으나 `disabled`다. 업스트림은 XO와 `cx`·`mss` 전원 도메인을 쓴다. 두 트리에서 모뎀용 SMP2P의 공유 메모리 항목과 상대 프로세서 번호가 일치한다. 전원 공급과 준비 신호가 이 보드에서 실제로 동작하는지는 열려 있다. |
| 펌웨어 공급 | Android `ueventd`가 `/vendor/firmware-modem/image/modem.mdt`와 분할 파일을 찾아 제공했다. 이어서 커널이 5,584바이트 MDT를 받아 모뎀 기동 완료를 기록했다. | `CONFIG_EXTRA_FIRMWARE=""`이고 로더에 포함된 초기 파일시스템에 MDT, 분할 파일, `ueventd`가 없다. UFS 컨트롤러와 PHY도 꺼져 있어 순정의 VFAT 마운트로 파일을 공급하는 경로가 없다. [순정 마운트 구성](S22PLUS_FYG8_DEVICE_LOCAL_STORAGE_PATH_SURVEY_H0_2026-08-10.md) · [Linux 펌웨어 검색 경로](https://docs.kernel.org/driver-api/firmware/fw_search_path.html) |
| 기동 요청 | 순정 커널 로그에서 펌웨어 요청과 같은 모뎀의 기동 완료를 순서대로 확인했다. | 업스트림 SM8450 MPSS 설정은 `auto_boot = false`다. ML050의 SysV init은 RAM 관측기를 실행하며 이 경로에 모뎀 시작 요청이 없다. 드라이버와 노드를 활성화하고 파일을 공급한 구성에도 기동을 요청할 주체가 필요하다. |

**순정 파일의 형식과 주 예약 메모리는 맞는다.** FYG1의 ELF 프로그램 헤더 32개를 7.2.11 MDT 로더의 판정 조건과 대조했다. MDT에는 로더가 사용하는 ELF 헤더와 서명·해시 세그먼트가 연속해 들어 있다. 메모리에 올리는 세그먼트 30개 중 파일 데이터가 있는 27개의 분할 파일이 모두 예상 이름과 길이로 존재한다. 나머지 세 개는 파일 데이터 길이가 0이다. 이 30개의 처음부터 끝까지 범위는 두 기기 트리가 모뎀에 할당한 주 예약 영역과 정확히 같은 306 MiB다. 순정 노드가 두 번째로 참조하는 영역은 기본 CMA 풀이다. 이 업스트림 SM8450 항목에는 별도 DTB용 PAS ID가 없어 주 영역 하나를 사용한다.

따라서 서명된 CP를 고치거나 주 예약 메모리를 늘려야 한다는 근거는 없다. 파생 빌드에서 보드 전원과 클럭을 올리고 PAS 인증·리셋 해제를 마친 뒤 실제 모뎀 준비 신호까지 받는지는 미검증이다. 그다음 GLINK·QRTR 통신과 모뎀의 저장소 서비스 사용 가능성도 각각 별도 결과다. 비공개 대조 결과는 기존 증거 디렉터리의 `ml050-stock-cp-comparison.json`에 기록했다. [ML050 기기 트리](../../workspace/public/src/mainline/s22plus_canary_h0/g0q.dtsi) · [ML050 실기 관측 범위](S22PLUS_MAINLINE_ML050_UDC_AUTO_RETURN_RUN_2026-11-11.md)

## 순정 CP로 돌아올 수 있는가

**복구 파일을 확보했다.** CP 아카이브는 68,833,389바이트이고 SHA-256은 `08495982043835aa233061c70dfc42b327684e93cf7c7e02d89278a5ea3ec445`이다. 전체 배포 ZIP의 SHA-256도 기준값과 일치한다. 순정 이미지의 서명과 FYG1의 과거 정상 기동은 복구에 사용할 파일의 원본성과 대상 적합성을 뒷받침한다.

**수정 CP에서 순정 CP로 돌아오는 실기 복구는 미입증이다.** ML050 원복의 실행 영수증·실제 전송 아카이브·Odin 출력·최종 건강 기록을 대조했다. 전송한 멤버는 `boot.img.lz4` 하나였고, 종료 상태는 `ANDROID_CLOSED_HEALTHY`였다. 이 실행에서 모뎀 파티션은 재전송이나 해시 대조 대상에 들어 있지 않았다. S22+로 식별되는 보관 `runs`와 `outputs`의 멤버 명시형 실행 영수증에서도 CP 전송 뒤 FYG1 재기동까지 연결되는 사례를 찾지 못했다. 앞선 계획 문서의 전체 펌웨어 복구 예상은 실기 영수증을 대신할 수 없다. [ML050 복구 보고서](S22PLUS_MAINLINE_ML050_UDC_AUTO_RETURN_RUN_2026-11-11.md)

비공개 검증 결과는 `workspace/private/analysis/s22plus-fyg8-cp-static.zjrEXG/cp-trust.E0NEMg/`의 `evidence.json`과 `mainline.json`에 있다. USB 연결, 펌웨어 변경, 전송 및 재부팅 없이 검증했다.
