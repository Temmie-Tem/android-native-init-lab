"""Reproduce the FYG8 Waipio PHY register tables before using a cold link profile."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
from elftools.elf.elffile import ELFFile

TABLES = {
    "phy_cal_table_rate_A": 80,
    "phy_cal_table_2nd_lane": 48,
    "phy_cal_table_rate_A_no_g4": 85,
    "phy_cal_table_2nd_lane_no_g4": 47,
    "phy_cal_table_rate_B": 1,
}
PRIVATE = Path(__file__).resolve().parents[5] / "workspace/private"
MODULE_SHA = "cfc078b154b8741146556d64dae3459dd0f8b6b2056efcc6ce0b37ade3af18c0"
HEADER_SHA = "8a3431035c768867706c5af387ca45f8681690d08723f12041e0fadb274685d7"
MODULE = PRIVATE / "outputs/s22plus-debian-integrated-p425-h0-20261013-1/build-2/tree/lab/modules/phy-qcom-ufs-qmp-v4-waipio.ko"
PHY_WINDOW = 0xe10


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_tables(path):
    result = {}
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        require(elf.little_endian and elf["e_machine"] == "EM_AARCH64"
                and elf["e_type"] == "ET_REL", "expected a relocatable ARM64 ELF")
        symbols = elf.get_section_by_name(".symtab")
        for name, count in TABLES.items():
            sym, = symbols.get_symbol_by_name(name)
            section = elf.get_section(sym["st_shndx"])
            start = sym["st_value"]
            size = sym["st_size"]
            require(sym["st_info"]["type"] == "STT_OBJECT" and size == count * 8,
                    f"unexpected {name} object")
            require(section["sh_type"] == "SHT_PROGBITS" and start + size <= section.data_size,
                    f"invalid section for {name}")
            for reloc in elf.iter_sections():
                if reloc["sh_type"] in ("SHT_REL", "SHT_RELA") and reloc["sh_info"] == sym["st_shndx"]:
                    require(all(not start <= r["r_offset"] < start + size for r in reloc.iter_relocations()),
                            f"{name} contains a relocation")
            result[name] = section.data()[start:start + size]
    return result


def validate(header, output):
    require(header.resolve().is_relative_to(PRIVATE.resolve()) and
            output.resolve().is_relative_to(PRIVATE.resolve()), "private paths required")
    require(digest(header) == HEADER_SHA and digest(MODULE) == MODULE_SHA, "PHY input identity")
    output.mkdir(mode=0o700, exist_ok=False)
    # Compile the original table declarations; the shim supplies just their data types.
    (output / header.name).write_bytes(header.read_bytes())
    (output / "phy-qcom-ufs-i.h").write_text(
        "struct ufs_qcom_phy { unsigned int unused; };\n"
        "struct ufs_qcom_phy_calibration { unsigned int reg_offset, cfg_value; };\n"
        "#define UFS_QCOM_PHY_CAL_ENTRY(r,v) { .reg_offset=(r), .cfg_value=(v) }\n"
    )
    src = output / "tables.c"
    src.write_text('#include "phy-qcom-ufs-qmp-v4-waipio.h"\n')
    obj = output / "tables.o"
    cmd = ["aarch64-linux-gnu-gcc", "-std=c11", "-O0", "-c", src, "-o", obj]
    subprocess.run(cmd, check=True)
    info = subprocess.check_output(["file", obj], text=True)
    require("ARM aarch64" in info, "table object is not ARM64")
    (output / "file.log").write_text(info)
    stock = read_tables(MODULE)
    rebuilt = read_tables(obj)
    require(rebuilt == stock, "stock register data differs from rebuilt base source")
    rows = {}
    for name, raw in stock.items():
        pairs = list(struct.iter_unpack("<II", raw))
        require(all(not offset % 4 and offset + 4 <= PHY_WINDOW and value <= 0xff
                    for offset, value in pairs), "table writes outside the fixed PHY window")
        rows[name] = dict(entries=len(pairs), maximum_offset=max(p[0] for p in pairs),
                          sha256=hashlib.sha256(raw).hexdigest())
    receipt = dict(status="PASS_H0_FYG8_PHY_TABLE_PARITY", stock_module_sha256=MODULE_SHA,
                   header_sha256=HEADER_SHA, object_sha256=digest(obj),
                   table_data=rows, physical_phy_ready=False, device_actions=0)
    (output / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    os.umask(0o077)
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("header", type=Path)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    print(validate(args.header, args.output)["status"])
