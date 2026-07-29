# S22+ FYG8 P2.84 Full-LTO candidate closure and connected preparation

Date: 2026-07-29 KST

Scope: H0, connected D0, and one freshly approved D1 normal Android reboot.
No F1 approval, Download transition, Odin session, candidate transfer,
rollback transfer, or partition write occurred.

## Verdict

`READY_FOR_FRESH_EXACT_F1_APPROVAL`

P2.84 run `023060c8dd0ab036f8547a816624356f` completed the ordinary candidate
closure and connected preparation sequence:

`20/20 pre-LTO -> Full-LTO A/B -> linked audit -> package A/B -> static
closure -> Process v2 promotion -> ready manifest -> D0 -> D1 baseline
rotation -> clean D0`

The private prepared run reopens under the unchanged common runner. Its
`f1_authorized` and `live_authorized` fields remain false. Only a fresh exact
operator approval of its private binding can authorize F1.

## Frozen source identity

- source contract:
  `s22plus-fyg8-p284-sysfs-ingestion-correction-v1`;
- candidate run ID: `023060c8dd0ab036f8547a816624356f`;
- intent SHA256:
  `7a21c6d9c3db0700a64f33813b3b67689c3c63939584a8fd68cd4956cea62997`;
- patch SHA256:
  `cd47f84e6c9b62bc0cbdf03e4bd4a80895966cc295c4372e912f959708ca9aa1`;
- pre-LTO qualification SHA256:
  `273882feaaf70257dcad2bbd2f6a7b1110d69b8a227e5d6373d267d3cd8b7114`;
- qualification verdict:
  `PASS_P284_PRE_FULL_LTO_QUALIFICATION_HOST_ONLY`;
- gates: `20/20`, with `build_allowed=true`.

All 60 source-contract entries remained exact before build, after Build A,
after Build B, and through final candidate-contract reopening. Downstream
verifier, ready-manifest, report, and state files are not source keys.

## Full-LTO A/B

Two clean builds ran on the qualified build host:

| Build | Elapsed | Max RSS | Swap | Exit |
|---|---:|---:|---:|---:|
| A | `42:41.45` | `24,254,352 KiB` | `0` | `0` |
| B | `42:41.21` | `24,253,332 KiB` | `0` | `0` |

All six retained linked artifacts are byte-identical:

| Artifact | Size | SHA256 |
|---|---:|---|
| `.config` | 185,508 | `c385765c8ec84fe82637ba88a600aff6a96066a986cc35d1bbae0c2aef797a39` |
| `Image` | 41,490,944 | `71c76b298bfa01cb5277d5a9e631548abc9d292da67dec01c51f451290a53075` |
| `System.map` | 5,073,954 | `1c34c1adb48b9e4a5f57131c609be51b34f76b27805b1166f93f773f12c57f20` |
| `abi.xml` | 12,787,205 | `3660c592e1884ab323816c09a3abd197744c8b2f78aed890b02c3e69dbc1c55c` |
| `vmlinux` | 476,984,960 | `31059db0469188af9f7c212a182ebdaf8083679bdc81e71ed598b6181bb2d0fd` |
| `vmlinux.symvers` | 439,646 | `fd75413401617a427ddf6c264d0ae4f5452b46cde02b4575b9af09f19601ca19` |

The canonical GNU 2.46 linked audit passes. The portable audit differs only
by the already-established absolute qualification-path normalization; raw
build artifacts are unchanged. Its SHA256 is:

`e20a188b426c218c505a49ef05ff4260fa5a328e4d7a27066811b466a4717db2`

## Package and static closure

Candidate A and B match byte-for-byte:

| Artifact | Size | SHA256 |
|---|---:|---|
| `boot.img` | 100,663,296 | `9ec763718e023ad76565958b86c4d784a5611901b48d3b43880e0b7dcf54f2b7` |
| `boot.img.lz4` | 27,086,048 | `c010ec938ebfb8f0dca139feb823d61bb0854f8d0525990c1bc5882298aa6d9c` |
| `AP.tar.md5` | 27,095,081 | `f0362df50d105ec2cd198572ff87c4f7c194e92ab8cea9279bd802ed04541682` |

Each AP contains exactly one regular deterministic member named
`boot.img.lz4`. The independent static closure is 47,901 bytes with SHA256:

`4000a658241c8680b4f2408f71eeed91b9f584cabadd58c6f8ad5cdb8d52817a`

Its verdict is:

`PASS_P234_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY`

## Downstream verifier corrections

Two downstream adapters were corrected without changing any candidate source
key or built artifact:

1. the P2.84 linked audit now includes the inherited P2.82 validator function
   set; and
2. Process v2 generic-rootfs replay now follows the exact
   `P2.84 -> P2.82 -> P2.80 -> P2.57 -> P2.53` 60-to-59-row adapter chain.

The first Process v2 promotion attempt failed before output because the second
adapter was absent. Its failure log is preserved privately. After the focused
positive and missing-adapter tests passed, the same immutable candidate
promoted successfully without rebuilding or repackaging.

Promotion artifacts are:

| Artifact | Size | SHA256 |
|---|---:|---|
| `candidate-static.json` | 47,901 | `4000a658241c8680b4f2408f71eeed91b9f584cabadd58c6f8ad5cdb8d52817a` |
| `run-manifest.json` | 774 | `f7f5bbbbd1b7a18b5c3e162a10117918c1acf9852eb31a0454e7ecf19c3edd9f` |
| `static-check-result.json` | 1,684 | `262c40e10ad5e0ab36a21b127e3cbb78803779fd1d2ef7cdb706b052d9be60be` |

The promotion verdict is:

`PASS_P234_PROCESS_V2_OFFLINE_EVIDENCE_PROMOTION`

## Immutable ready bundle

The tracked manifest is:

`workspace/public/src/device-action/manifests/s22plus_fyg8_p284_process_v2_ready_1.json`

It binds terminal stage `0x93`, the P2.84 source contract, exact run-bound
CDC-ACM observer, 300-second observation window, candidate AP, proven Magisk
rollback AP, and all three promoted contracts.

- manifest SHA256:
  `2500f977a2fdbe90d060e5a35ab4b6583d2857328b66206fc3ec700fca99fdd9`;
- validated bundle SHA256:
  `c3a670ba0477723380e2b685525a19db92880bc52d53ccae36dd342c2f598eaf`;
- execution-closure SHA256:
  `2513f750247ace7d83484980cfec2dbcd486e6afbf816148189f409621dcc3c2`;
- host verdict:
  `PASS_DEVICE_ACTION_F1_LIVE_V2_HOST_READY`.

The exact rollback AP remains 23,367,721 bytes with SHA256:

`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`

## Connected baseline and D1 rotation

The first connected D0 verified one unique healthy FYG8 Android/root target,
then stopped before `prepared.json` because `/proc/last_kmsg` contained one
related-family record. Offline decoding proves that sole record is the exact
consumed P2.82 terminal failure `stage=0x8e/detail=0xc10`; exact P2.84 count is
zero.

The operator then freshly approved exactly one normal Android `adb reboot`.
That D1:

- invoked the reboot command exactly once;
- observed ADB disconnect and the same private target return;
- proved the boot ID changed;
- restored `sys.boot_completed=1`, stopped boot animation, and root;
- preserved exact boot, vendor_boot, DTBO, and recovery identities; and
- invoked no Download transition, Odin, payload transfer, or partition write.

Its result verdict is `PASS_D1_EXACT_NORMAL_REBOOT_RETURN_HEALTH`, with SHA256:

`28265341882f5feeae2bbe18a6c5a19966a135bd4c820fecb092fbcc9ed50b95`

## Clean D0 and approval handoff

Repeated D0 against the unchanged manifest passes:

- baseline family count: `0`;
- exact P2.84 record count: `0`;
- D0 result: 2,968 bytes, SHA256
  `1e0a86c4d87e1823dce52bc0068998402ee3f5c15e5cfbcee60877ad67bf1e33`;
- prepared result: 7,969 bytes, SHA256
  `06d4241cc2ad0733a64e80feea0d426e2d7661530cf6437083f913c1e5ce4253`;
- approval-binding SHA256:
  `454bcb68449ec863b0bbb106a27858fd94872cc0e3ec6130d4b233e1833528d6`.

The common loader reopens the private prepared run and proves:

`device_writes=false`, `reboot_requested=false`, `odin_invoked=false`,
`partition_transfer=false`, `f1_authorized=false`, and
`live_authorized=false`.

The next action is the operator's fresh exact F1 approval of that binding.
Until it is returned, no Download request, Odin call, candidate transfer, or
rollback transfer is authorized.
