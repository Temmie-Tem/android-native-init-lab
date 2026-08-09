#!/usr/bin/env python3
"""Exact fixed-module callsite contract for the P3.11 early clock observer."""

from __future__ import annotations

import s22plus_fyg8_p303_telemetry_spec as p303


MODULE_PATH = p303.MODULE_PATH
MODULE_SHA256 = p303.MODULE_SHA256
MODULE_BUILD_ID = p303.MODULE_BUILD_ID
MODULE_RUNTIME_NAME = p303.MODULE_RUNTIME_NAME

# name, clock, operation, post-BL symbol offset, immediate w0 consumer
PROBE_CALLSITES = (
    ("probe_ref_src_prepare", "ref_clk_src", "prepare", 0x9B8, "cbnz"),
    ("probe_ref_src_enable", "ref_clk_src", "enable", 0x9C4, "cbz"),
    ("probe_ref_prepare", "ref_clk", "prepare", 0x9E0, "cbnz"),
    ("probe_ref_enable", "ref_clk", "enable", 0x9EC, "cbz"),
    ("probe_cfg_prepare", "cfg_ahb_clk", "prepare", 0xA08, "cbnz"),
    ("probe_cfg_enable", "cfg_ahb_clk", "enable", 0xA14, "cbz"),
)

SET_SUSPEND_CALLSITES = (
    ("suspend_ref_src_prepare", "ref_clk_src", "prepare", 0x198, "cbnz"),
    ("suspend_ref_src_enable", "ref_clk_src", "enable", 0x1A4, "cbz"),
    ("suspend_ref_prepare", "ref_clk", "prepare", 0x1C0, "cbnz"),
    ("suspend_ref_enable", "ref_clk", "enable", 0x1CC, "cbz"),
    ("suspend_cfg_prepare", "cfg_ahb_clk", "prepare", 0x1E8, "cbnz"),
    ("suspend_cfg_enable", "cfg_ahb_clk", "enable", 0x1F4, "cbz"),
)

INIT_CALLSITES = tuple(
    (name, clock, operation, offset, consumer)
    for name, _branch, clock, operation, offset, consumer in p303.CALLSITES
)

CALLER_SPECS = (
    (
        "probe",
        "msm_hsphy_probe",
        0x260,
        2616,
        "msm_hsphy_probe.cfi_jt",
        0x3290,
        PROBE_CALLSITES,
    ),
    (
        "init",
        "msm_hsphy_init",
        p303.CALLSITE_SYMBOL_VALUE,
        1992,
        "msm_hsphy_init.cfi_jt",
        0x32A0,
        INIT_CALLSITES,
    ),
    (
        "set_suspend",
        "msm_hsphy_set_suspend",
        0x19D4,
        760,
        "msm_hsphy_set_suspend.cfi_jt",
        0x32A8,
        SET_SUSPEND_CALLSITES,
    ),
)

CALLSITE_COUNT = sum(len(value[-1]) for value in CALLER_SPECS)

if CALLSITE_COUNT != 24:
    raise RuntimeError("P3.11 exact callsite count must remain 24")
