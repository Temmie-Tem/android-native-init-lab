# Host Validation Resource Guardrails

Date: `2026-05-24`

이 문서는 host-side 검증이 작업 범위보다 과도하게 넓어져 OOM, editor/terminal 종료,
세션 손실을 일으키지 않도록 하는 운영 규칙이다.

## Incident Basis

`2026-05-24 00:34 KST`에 host OOM killer가 Python 검증 프로세스를 종료했다.
직접 원인은 secret scan 목적의 임시 Python 코드가 repository 전체 파일을 순회하며
`read_bytes()`로 파일 전체를 메모리에 올린 것이다.

이 repository에는 firmware tar, AP tar.md5, USERDATA tar.md5, boot/recovery image처럼
수십 MiB에서 수 GiB 단위의 산출물이 포함된다. secret scan의 실제 목적은 변경된
코드/문서에 credential이 섞였는지 확인하는 것이므로, 이런 binary artifact를 전부
읽는 것은 목적에도 맞지 않고 위험하다.

## Rule

Host validation must be scoped to the evidence question.

- 검증 목적이 “변경 파일에 secret이 들어갔는가”라면 변경 파일만 검사한다.
- 검증 목적이 “문서/스크립트 diff가 깨끗한가”라면 `git diff --check`와 대상 파일 검증만 한다.
- repository 전체 raw file scan은 기본 금지다.
- 대형 artifact 디렉터리와 image/archive 파일은 기본 제외한다.
- 파일 내용을 검사해야 할 때는 전체 `read_bytes()`가 아니라 chunk 기반 streaming을 쓴다.
- Codex/session/journal log 검색은 시간대, 파일, 패턴을 좁힌 뒤 실행한다.

## Default Exclude Set

다음 경로와 파일군은 일반적인 secret/document/static 검증에서 제외한다.

- `.git/`
- `tmp/`
- `firmware/`
- `backups/`
- `workspace/private/inputs/boot_images/*.img`
- `*.tar`
- `*.tar.md5`
- `*.img`
- `*.bin`
- `*.sqlite`
- `*.sqlite-wal`
- `*.log` unless the log file itself is the evidence target

예외적으로 binary artifact 자체가 검증 대상이면 파일 크기, SHA256, 목적을 먼저 확인하고
단일 파일만 대상으로 삼는다.

## Safe Secret Scan Pattern

기본 secret scan은 staged/modified/untracked 파일로 제한한다.

```bash
git ls-files -m -o --exclude-standard
```

이 목록에서 default exclude set을 적용한 뒤 검사한다.

권장 Python 형태:

```python
from pathlib import Path
import subprocess

NEEDLES = [
    b"example-secret-pattern",
]
EXCLUDED_DIRS = {".git", "tmp", "firmware", "backups"}
EXCLUDED_SUFFIXES = {
    ".img",
    ".bin",
    ".tar",
    ".md5",
    ".sqlite",
    ".sqlite-wal",
    ".log",
}
MAX_FILE_BYTES = 8 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024

files = subprocess.check_output(
    ["git", "ls-files", "-m", "-o", "--exclude-standard"],
    text=True,
).splitlines()

hits = []
for name in files:
    path = Path(name)
    if not path.is_file():
        continue
    if any(part in EXCLUDED_DIRS for part in path.parts):
        continue
    if path.suffix in EXCLUDED_SUFFIXES:
        continue
    if path.stat().st_size > MAX_FILE_BYTES:
        raise SystemExit(f"refusing large secret-scan file: {path}")

    previous_tail = b""
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK_BYTES)
            if not chunk:
                break
            window = previous_tail + chunk
            if any(needle in window for needle in NEEDLES):
                hits.append(name)
                break
            longest = max((len(needle) for needle in NEEDLES), default=1)
            previous_tail = window[-max(longest - 1, 0):]

if hits:
    print("secret-scan-fail")
    for hit in hits:
        print(hit)
    raise SystemExit(1)

print("secret-scan-pass")
```

## Prohibited Patterns

다음 형태는 금지한다.

```python
for path in Path(".").glob("**/*"):
    data = path.read_bytes()
```

```bash
rg "secret" .
```

```bash
find . -type f -exec cat {} +
```

위 패턴은 firmware/archive/image/log/session 파일까지 읽을 수 있고, 검증 목적과 무관한
대형 파일 때문에 OOM을 유발할 수 있다.

## Large Log Handling

Codex session log, TUI log, journal output은 빠르게 커질 수 있다.

- 먼저 시간대와 파일을 좁힌다.
- `tail`, `journalctl --since/--until`, `rg -m`, `rg --max-filesize`를 사용한다.
- base64 image payload나 huge JSONL을 터미널에 직접 크게 출력하지 않는다.
- 필요한 경우 JSONL은 parser로 `function_call`/`event_msg` 같은 필요한 record만 추출한다.

예시:

```bash
journalctl --since '2026-05-24 00:25:00' --until '2026-05-24 00:50:00' \
  -k --no-pager | rg -i 'oom|killed process|out of memory'
```

```bash
rg --max-filesize 16M -n 'v665|secret-scan|OOM' ~/.codex/log/codex-tui.log
```

## Pre-Run Checklist

넓은 검증 명령을 실행하기 전에 확인한다.

1. 검증 질문이 무엇인지 한 문장으로 말할 수 있는가?
2. 입력 파일 목록이 `git ls-files` 또는 명시 경로로 제한되는가?
3. `firmware/`, `backups/`, `tmp/`, image/archive/log가 제외되는가?
4. 단일 파일이 8 MiB를 넘으면 skip 또는 explicit target으로 처리하는가?
5. content scan이 chunk 기반인가?
6. 출력이 터미널/세션 로그를 폭증시키지 않는가?

하나라도 아니면 명령을 좁힌 뒤 실행한다.

## Development Loop Integration

이 문서는 `DEVELOPMENT_LOOP_STANDARD.md`의 정적 검증, 커밋 전 secret 확인,
로그 조사 단계에 적용된다. 특히 Wi-Fi bring-up 작업에서는 credential이 등장할 수 있으므로
secret scan은 더 자주 필요하지만, 그만큼 검사 범위를 변경 파일과 문서/스크립트로 제한해야 한다.
