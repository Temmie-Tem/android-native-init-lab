# SM-S906N FYG1 모뎀 서명과 복구 근거

운영자 소유 S22+의 FYG8 배포본에는 FYG1 모뎀 펌웨어가 들어 있다. 순정 드라이버와 메인라인 Linux 7.2.11의 SM8450 드라이버 모두 모뎀 기동을 보안 영역의 인증 결과에 의존한다. **서명된 실행 코드를 바꾸고 기존 서명을 유지한 CP는 이 검증을 통과할 수 없다.** 실제 단말에서 수정 CP를 시도해 얻은 거부 기록은 없다. 이번 조사는 보관 파일과 과거 실기 기록만 사용했다.

## 순정 서명과 부팅 기록

- 정식 배포 ZIP 안의 CP와 별도로 보관한 CP 아카이브가 바이트 해시로 일치한다. 아카이브의 유일한 멤버인 `modem.bin.lz4`를 호스트에서 풀어 대조했다. 내부 FAT16에서 읽은 모뎀 메타데이터·서명 세그먼트와 파일 데이터가 있는 ELF 항목 28개(ELF 헤더 포함)가 모두 보관 사본과 일치했다. 각 항목의 SHA-384 값도 서명된 해시표와 일치했다. [순정 배포본의 기준 해시](../operations/S22PLUS_FYG8_STOCK_FIRMWARE_EVIDENCE_POLICY_2026-07-08.md)
- 해시표·메타데이터를 포함한 서명 대상에 대해 내장된 Samsung Electronics 인증서 공개키로 ECDSA P-384/SHA-384 서명을 검증했다. 서명용 인증서에서 중간 인증서, 자체 서명 루트까지 인증서 서명도 검증했다. 비교용 다이제스트에서 한 비트만 다르게 주자 기존 서명의 검증이 실패했다. 장치에 고정된 신뢰 루트 값은 독립적으로 읽지 않았다. Qualcomm은 서명된 해시 세그먼트로 개별 ELF 세그먼트를 인증하는 구조를 설명한다. [Qualcomm 이미지 인증 설명](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/secure-boot-and-image-authentication.pdf)
- 순정 기기 트리의 모뎀과 순정 `qcom_q6v5_pas.ko`의 기기 매칭 정보를 대조했다. 모듈의 로드 함수는 MDT 로더를 호출하고, 시작 함수는 `qcom_scm_pas_auth_and_reset`의 결과를 검사한다. 원본 캡처 해시를 대조한 7월 13일 실기 bugreport에는 이 드라이버가 모뎀에 연결되어 `modem.mdt`를 기동하고 모뎀이 준비된 기록이 있다. 같은 기록의 베이스밴드는 `S906NKSS7FYG1`이고 Android 부트로더는 잠금 해제·`orange` 상태였다. 이 조합이 증명하는 범위는 **AP 잠금이 해제된 단말에서 순정 FYG1이 기동했다**는 것이다. [순정 모듈 인벤토리](../module-map/s22plus-fyg8-super/inventory.tsv) · [삼성의 부트 신뢰 체인 설명](https://docs.samsungknox.com/admin/fundamentals/whitepaper/samsung-knox-mobile-security/system-security/trusted-boot/)

## 메인라인 커널과 비교

| 대상 | 모뎀 기동 경로와 판정 |
| --- | --- |
| 순정 FYG8 커널 5.10.226 | 실기에서 순정 FYG1 기동을 확인했다. AP에서 수정한 부트 이미지를 실행할 수 있다는 사실은 모뎀의 서명 수락 여부까지 입증하지 않는다. |
| 업스트림 Linux 7.2.11 | SM8450 MPSS용 PAS 드라이버는 `modem.mdt`를 대상으로 한다. 펌웨어 로드 후 보안 영역에 인증·리셋 해제를 요청하며, 실패하면 오류 경로로 빠진다. 성공한 경로에서만 모뎀 기동을 기다린다. 커널을 교체해도 이 드라이버가 CP 서명에 대한 새 신뢰 권한을 제공하지 않는다. [사용한 업스트림 소스 버전·해시](../../workspace/public/src/mainline/s22plus_canary_h0/sources.json) |
| S22+에서 사용한 ML050 빌드 | 실제 로더 입력의 Image·DTB와 빌드 설정을 준비 기록의 해시로 대조했다. `7.2.11-g0q-ram-h0`는 `CONFIG_REMOTEPROC`가 꺼져 있고, 컴파일된 DTB의 MPSS 노드도 `disabled`다. **이 빌드에는 순정·수정 CP 어느 쪽이든 새로 기동하는 해당 드라이버 경로가 없다.** [g0q 기기 트리](../../workspace/public/src/mainline/s22plus_canary_h0/g0q.dtsi) |

## 순정 CP로 돌아올 수 있는가

**복구 파일을 확보했다.** CP 아카이브는 68,833,389바이트이고 SHA-256은 `08495982043835aa233061c70dfc42b327684e93cf7c7e02d89278a5ea3ec445`이다. 전체 배포 ZIP의 SHA-256도 기준값과 일치한다. 순정 이미지의 서명과 FYG1의 과거 정상 기동은 복구에 사용할 파일의 원본성과 대상 적합성을 뒷받침한다.

**수정 CP에서 순정 CP로 돌아오는 실기 복구는 미입증이다.** ML050 원복의 실행 영수증·실제 전송 아카이브·Odin 출력·최종 건강 기록을 대조했다. 전송한 멤버는 `boot.img.lz4` 하나였고, 종료 상태는 `ANDROID_CLOSED_HEALTHY`였다. 이 실행에서 모뎀 파티션은 재전송이나 해시 대조 대상에 들어 있지 않았다. S22+로 식별되는 보관 `runs`와 `outputs`의 멤버 명시형 실행 영수증에서도 CP 전송 뒤 FYG1 재기동까지 연결되는 사례를 찾지 못했다. 앞선 계획 문서의 전체 펌웨어 복구 예상은 실기 영수증을 대신할 수 없다. [ML050 복구 보고서](S22PLUS_MAINLINE_ML050_UDC_AUTO_RETURN_RUN_2026-11-11.md)

비공개 검증 결과는 `workspace/private/analysis/s22plus-fyg8-cp-static.zjrEXG/cp-trust.E0NEMg/`의 `evidence.json`과 `mainline.json`에 있다. USB 연결, 펌웨어 변경, 전송 및 재부팅 없이 검증했다.
