#!/usr/bin/env python3
"""Generate a compact Bad Apple beat/onset timestamp table for the native Player HUD.

Input is the private V2903 48 kHz stereo S16LE audio render. Output is a small
public C header containing only millisecond timestamps, not audio samples.
"""

from __future__ import annotations

import argparse
from array import array
from pathlib import Path
from statistics import mean, pstdev

from _workspace_bootstrap import repo_root

REPO_ROOT = repo_root()
DEFAULT_AUDIO = REPO_ROOT / "workspace/private/demo-assets/video/v2903-badapple-480x360-full/audio/audio.s16le"
DEFAULT_HEADER = REPO_ROOT / "workspace/public/src/native-init/v319/a90_badapple_beat_table.h"
AUDIO_SHA256 = "b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75"
SOURCE_ID = "badapple-v2903-energy-onsets-v2941"
SAMPLE_RATE = 48000
CHANNELS = 2
WINDOW_FRAMES = 1024
MIN_GAP_MS = 160
MAX_EVENTS = 720


def read_window_energies(path: Path) -> list[float]:
    energies: list[float] = []
    samples_per_window = WINDOW_FRAMES * CHANNELS
    bytes_per_window = samples_per_window * 2
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(bytes_per_window)
            if not chunk:
                break
            values = array("h")
            values.frombytes(chunk)
            if len(values) < samples_per_window:
                break
            total = 0
            # Downmix by absolute stereo sample magnitude; this is deliberately
            # simple and deterministic for reproducible native HUD pulses.
            for sample in values:
                total += abs(int(sample))
            energies.append(total / float(samples_per_window))
    return energies


def smooth(values: list[float], radius: int) -> list[float]:
    out: list[float] = []
    for index in range(len(values)):
        start = max(0, index - radius)
        end = min(len(values), index + radius + 1)
        out.append(sum(values[start:end]) / float(end - start))
    return out


def extract_onsets(energies: list[float]) -> list[int]:
    if len(energies) < 8:
        return []
    baseline = smooth(energies, 8)
    flux = [max(0.0, energies[index] - baseline[index]) for index in range(len(energies))]
    positive = [value for value in flux if value > 0.0]
    if not positive:
        return []
    threshold = mean(positive) + 0.85 * pstdev(positive)
    min_gap_windows = max(1, int((MIN_GAP_MS * SAMPLE_RATE) / (1000 * WINDOW_FRAMES)))
    candidates: list[tuple[float, int]] = []
    for index in range(1, len(flux) - 1):
        score = flux[index]
        if score < threshold:
            continue
        if score < flux[index - 1] or score < flux[index + 1]:
            continue
        candidates.append((score, index))

    selected: list[tuple[int, float]] = []
    for score, index in sorted(candidates, reverse=True):
        if all(abs(index - other) >= min_gap_windows for other, _ in selected):
            selected.append((index, score))
            if len(selected) >= MAX_EVENTS:
                break
    selected.sort()
    return [round(index * WINDOW_FRAMES * 1000 / SAMPLE_RATE) for index, _ in selected]


def render_header(onsets: list[int]) -> str:
    wrapped: list[str] = []
    line: list[str] = []
    for value in onsets:
        item = f"{value}U"
        line.append(item)
        if len(line) >= 12:
            wrapped.append("    " + ", ".join(line) + ",")
            line = []
    if line:
        wrapped.append("    " + ", ".join(line) + ",")
    body = "\n".join(wrapped)
    return f"""#ifndef A90_BADAPPLE_BEAT_TABLE_H\n#define A90_BADAPPLE_BEAT_TABLE_H\n\n#include <stdint.h>\n\n#define A90_BADAPPLE_BEAT_SOURCE_ID \"{SOURCE_ID}\"\n#define A90_BADAPPLE_BEAT_AUDIO_SHA256 \"{AUDIO_SHA256}\"\n#define A90_BADAPPLE_BEAT_WINDOW_MS 70U\n\nstatic const uint32_t A90_BADAPPLE_BEAT_MS[] = {{\n{body}\n}};\n\n#define A90_BADAPPLE_BEAT_COUNT \\\n    ((uint32_t)(sizeof(A90_BADAPPLE_BEAT_MS) / sizeof(A90_BADAPPLE_BEAT_MS[0])))\n\n#endif /* A90_BADAPPLE_BEAT_TABLE_H */\n"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=Path, default=DEFAULT_AUDIO)
    parser.add_argument("--output", type=Path, default=DEFAULT_HEADER)
    args = parser.parse_args()
    energies = read_window_energies(args.audio)
    onsets = extract_onsets(energies)
    if len(onsets) < 32:
        raise SystemExit(f"too few onsets extracted: {len(onsets)}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_header(onsets))
    print({
        "source": str(args.audio),
        "output": str(args.output),
        "windows": len(energies),
        "beats": len(onsets),
        "first_ms": onsets[0],
        "last_ms": onsets[-1],
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
