"""Reconstruct the ML028 UFS wiring and probe order from retained files, on the host."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[5]
PRIVATE = ROOT / "workspace/private"
CANARY = ROOT / "workspace/public/src/mainline/s22plus_canary_h0"
sys.path.insert(0, str(CANARY))
from prepare import config_values, nodes

ML028 = PRIVATE / "outputs/s22plus-mainline-ml028-rc-ssh-cycle-h0-20261105-1"
D0 = PRIVATE / "outputs/s22plus-abl-dt-d0-20261027-1"
STUDY = PRIVATE / "outputs/s22plus-mainline-ml029-ufs-host-study-20261105-1"
TASK_SHA = "58c9fd3adb3b37a9c722eeec6abe248183d70d2b79bcffd092c940631d09bd51"
VENDOR_BOARD = (PRIVATE / "inputs/s22plus_kernel_source/S906NKSS7FYG8_osrc/Kernel"
                / "kernel_platform/msm-kernel/arch/arm64/boot/dts/samsung/rainbow/g0q/g0q_kor_singlex_w00_r12.dts")

# FYG8 overlay target, property, regulator, voltage range (uV), load limit (uA).
RAILS = (
    ("phy", "vdda-phy", "l5", 880000, 912000, 173000),
    ("phy", "vdda-pll", "l6", 1200000, 1200000, 24900),
    ("host", "vcc", "l7", 2504000, 2504000, 1100000),
    ("host", "vccq", "l9", 1200000, 1200000, 1200000),
    ("host", "qcom,vddp-ref-clk", "l9", 1200000, 1200000, 100),
    ("host", "qcom,vccq-parent", "s12", 1224000, 1400000, 210000),
)
STOCK = {"host": "/soc/ufshc@1d84000", "phy": "/soc/ufsphy_mem@1d87000"}
MAIN = {"host": "/soc@0/ufshc@1d84000", "phy": "/soc@0/phy@1d87000"}
RPMH = "/soc@0/rsc@17a00000/regulators-0"
ML_TLMM = "/soc@0/pinctrl@f100000"
CORE = "drivers/ufs/core/ufshcd.c"
SOURCES = (CORE, "drivers/ufs/host/ufshcd-pltfrm.c", "drivers/ufs/host/ufs-qcom.c",
           "drivers/phy/qualcomm/phy-qcom-qmp-ufs.c", "drivers/regulator/qcom-rpmh-regulator.c",
           "drivers/pinctrl/qcom/pinctrl-sm8450.c", "arch/arm64/boot/dts/qcom/sm8450.dtsi",
           "arch/arm64/boot/dts/qcom/sm8450-samsung-r0q.dts", "block/partitions/efi.c", "drivers/soc/qcom/ice.c", "drivers/scsi/scsi_scan.c")


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def record(path):
    return json.loads(path.read_bytes())


def verified(ref):
    path = Path(ref["path"])
    require(path.resolve().is_relative_to(PRIVATE.resolve()) and sha(path) == ref["sha256"],
            "retained file identity differs: " + path.name)
    if "size" in ref:
        require(path.stat().st_size == ref["size"], "retained file size differs")
    return path


def texts(value):
    require(value.endswith(b"\0"), "unterminated DT string")
    return value[:-1].decode("ascii").split("\0")


def cells(value):
    require(len(value) % 4 == 0, "invalid DT cells")
    return list(struct.unpack(f">{len(value) // 4}I", value))


def providers(tree):
    result = {}
    for name, props in tree.items():
        if "phandle" in props:
            key, = cells(props["phandle"])
            require(0 < key < 0xffffffff and key not in result, "invalid or duplicate phandle")
            result[key] = name
    return result


def inputs():
    closed = record(ML028 / "task-1/closed.json")
    task = record(verified(closed["task"]))
    require(closed["task"]["sha256"] == TASK_SHA and closed["terminal_state"] == "ANDROID_CLOSED_HEALTHY"
            and closed["scientific_status"] == "PASS_DEBIAN_RC_SSH_CYCLE_RAM", "ML028 closure differs")
    image = task["N"]
    qualification = record(verified(image["qualification"]))
    manifest = record(verified(qualification["init_manifest"]))
    dt = verified(image["runtime_sources"]["dtb"])
    require(dt == verified(manifest["dtb"]) and manifest["vm"] is False, "physical DT join differs")
    config_ref, = [v for v in manifest["inputs"] if v["path"].endswith("/kernel-build/.config")]
    config = verified(config_ref)
    prep = record(dt.parent / "prepared.json")
    lock = CANARY / "sources.json"
    require(prep["dtb_sha256"] == sha(dt) and prep["config_sha256"] == sha(config)
            and prep["source_lock_sha256"] == sha(lock), "source preparation join differs")
    live = verified(prep["live_fdt"])
    capture = record(D0 / "receipt.json")
    require(live == D0 / "live.fdt" and capture["target"] == "SM-S906N/g0q/S906NKSS7FYG8"
            and capture["same_boot"] is True and capture["files_sha256"]["live.fdt"] == sha(live),
            "FYG8 capture join differs")
    return live, dt, config, Path(prep["kernel"]), record(lock)["kernel"]


def clock_ranges(props):
    names = texts(props["clock-names"])
    data = cells(props["freq-table-hz"])
    require(len(set(names)) == len(names) and len(data) == 2 * len(names), "clock/name cardinality differs")
    return dict(zip(names, zip(data[::2], data[1::2])))


def topology(stock, main, fixups):
    ids = providers(stock)
    m_ids = providers(main)
    require(texts(main["/"]["compatible"]) == ["samsung,g0q", "qcom,sm8450"] and
            texts(stock["/"]["model"]) == ["Samsung G0Q PROJECT (board-id,12)"], "board identity differs")
    phy, host = stock[STOCK["phy"]], stock[STOCK["host"]]
    require(texts(phy["compatible"]) == ["qcom,ufs-phy-qmp-v4-waipio"] and
            texts(host["compatible"]) == ["qcom,ufshc"], "stock compatible differs")
    require(ids[cells(host["phys"])[0]] == STOCK["phy"] and
            m_ids[cells(main[MAIN["host"]]["phys"])[0]] == MAIN["phy"] and
            texts(main[MAIN["phy"]]["compatible"]) == ["qcom,sm8450-qmp-ufs-phy"] and
            texts(main[MAIN["host"]]["compatible"])[0] == "qcom,sm8450-ufshc", "PHY/host join differs")
    for role in MAIN:
        require(texts(stock[STOCK[role]]["status"]) in (["ok"], ["okay"]) and
                texts(main[MAIN[role]]["status"]) == ["disabled"] and
                cells(stock[STOCK[role]]["lanes-per-direction"]) == [2], "status or lane count differs")
    require(cells(main[MAIN["host"]]["lanes-per-direction"]) == [2], "mainline host lane count differs")
    gpio, line, polarity = cells(host["reset-gpios"])
    require(ids[gpio] == "/soc/pinctrl@f000000" and (line, polarity) == (210, 1)
            and texts(main[ML_TLMM]["status"]) == ["disabled"] and
            cells(main[ML_TLMM]["gpio-reserved-ranges"]) == [36, 4, 50, 1, 93, 1]
            and "reset-gpios" not in main[MAIN["host"]], "reset or protected TLMM differs")
    require(texts(fixups["ufsphy_mem"]) == ["/fragment@16:target:0"] and
            "/fragment@17:target:0" in texts(fixups["ufshc_mem"]), "OSRC overlay targets differ")
    rows = []
    for role, consumer, rail, low, high, load in RAILS:
        prop = consumer + "-supply"
        ph, = cells(stock[STOCK[role]][prop])
        provider = ids[ph]
        regulator = stock[provider]
        symbol = "pm8350_" + rail
        fragment = "/fragment@" + ("16" if role == "phy" else "17") + "/__overlay__:" + prop + ":0"
        resource = texts(stock[provider.rsplit("/", 1)[0]]["qcom,resource-name"])
        expected_resource = ("ldob" if rail.startswith("l") else "smpb") + rail[1:]
        require(fragment in texts(fixups[symbol]) and texts(regulator["regulator-name"]) == [symbol]
                and resource == [expected_resource] and cells(regulator["regulator-min-microvolt"]) == [low]
                and cells(regulator["regulator-max-microvolt"]) == [high]
                and cells(stock[STOCK[role]][consumer + "-max-microamp"]) == [load]
                and prop not in main[MAIN[role]], "board regulator identity, voltage or load differs: " + consumer)
        rows.append(dict(consumer=consumer, regulator=symbol, rpmh_resource=resource[0], voltage_uV=[low, high],
                         load_uA=load, mainline_provider_declared=(RPMH + "/" +
                         ("ldo" if rail[0]=="l" else "smps") + rail[1:]) in main))
    usb = main[texts(main["/__symbols__"]["usb_1_hsphy"])[0]]
    l5 = RPMH + "/ldo5"
    require(m_ids[cells(usb["vdda-pll-supply"])[0]] == l5 and
            ids[cells(stock["/soc/hsphy@88e3000"]["vdd-supply"])[0]] ==
            ids[cells(phy["vdda-phy-supply"])[0]] and
            [cells(main[l5][k])[0] for k in ("regulator-min-microvolt", "regulator-max-microvolt")] ==
            [880000, 888000], "existing USB shared L5 differs")
    require([v["mainline_provider_declared"] for v in rows] == [True, False, False, False, False, False]
            and "vdd-l6-l9-l10-supply" not in main[RPMH], "baseline regulator providers differ")
    ice = m_ids[cells(main[MAIN["host"]]["qcom,ice"])[0]]
    require(cells(host["reg"]) == [0x1d84000,0x3000,0x1d88000,0x8000,0x1d90000,0x9000] and
            cells(phy["reg"]) == [0x1d87000,0xe10] and cells(main[ice]["reg"]) == [0,0x1d88000,0,0x18000]
            and cells(main[MAIN["host"]]["reg"]) == [0,0x1d84000,0,0x3000] and
            cells(main[MAIN["phy"]]["reg"]) == [0,0x1d87000,0,0x1000], "MMIO extents differ")
    require(texts(host["reg-names"]) == ["ufs_mem","ufs_ice","ufs_ice_hwkm"] and
            texts(host["interconnect-names"]) == texts(main[MAIN["host"]]["interconnect-names"]) ==
            ["ufs-ddr","cpu-ufs"], "host resources differ")
    stock_rates, main_rates = clock_ranges(host), clock_ranges(main[MAIN["host"]])
    require(set(stock_rates)-set(main_rates) == {"core_clk_ice"} and set(main_rates) <= set(stock_rates)
            and {k for k in main_rates if main_rates[k] != stock_rates[k]} == {"ref_clk"}
            and stock_rates["core_clk_ice"] == main_rates["ref_clk"] == (75000000, 300000000)
            and stock_rates["ref_clk"] == (0, 0), "per-name reference clock evidence differs")
    return dict(stock_clock_ranges=stock_rates, mainline_clock_ranges=main_rates, rails=rows, reset=dict(line=line, flags=polarity, stock_controller=ids[gpio],
                mainline_controller=ML_TLMM, mainline_gpio_ranges=cells(main[ML_TLMM]["gpio-ranges"])[1:]),
                blocks={role:dict(stock_reg=cells(stock[STOCK[role]]["reg"]),
                mainline_reg=cells(main[MAIN[role]]["reg"]), stock_clocks=texts(stock[STOCK[role]]["clock-names"]),
                mainline_clocks=texts(main[MAIN[role]]["clock-names"])) for role in MAIN},
                stock_host_regions=texts(host["reg-names"]), stock_ref_clk_enum=cells(host["dev-ref-clk-freq"]),
                mainline_ice=dict(path=ice,reg=cells(main[ice]["reg"])),
                host_resources={k:dict(provider=m_ids[cells(main[MAIN["host"]][k])[0]],
                        cells=cells(main[MAIN["host"]][k])[1:]) for k in ("phys","resets","power-domains","iommus")},
                stock_interconnects=texts(host["interconnect-names"]),
                mainline_interconnects=texts(main[MAIN["host"]]["interconnect-names"]))


def source_members(kernel, locked):
    archive = PRIVATE / "outputs/s22plus-mainline-canary-h0-20261027-1" / ("linux-" + locked["version"] + ".tar.xz")
    require(sha(archive) == locked["sha256"], "upstream kernel archive differs")
    wanted = {"linux-" + locked["version"] + "/" + s: s for s in SOURCES}
    result = {}
    with tarfile.open(archive, "r|xz") as stream:
        for member in stream:
            if member.name in wanted:
                rel = wanted[member.name]
                require(member.isfile() and rel not in result and member.size <= 2**21, "unexpected source member")
                data = stream.extractfile(member).read()
                require((kernel / rel).read_bytes() == data, "selected source differs from archive: " + rel)
                result[rel] = hashlib.sha256(data).hexdigest()
    require(result.keys() == set(SOURCES), "missing archived sources")
    return result


def vendor_reset(stock, main, kernel):
    # The FYG8 package is a differential release. Keep the base source
    # comparison explicit instead of assigning it a shipped-binary identity.
    vendor = PRIVATE / "inputs/s22plus_kernel_source"
    base = vendor / "SM-S906N_15_base_osrc/Kernel.tar.gz"
    delta = vendor / "S906NKSS7FYG8_osrc/S906NKSS7FYG8_kernel.tar.gz"
    prefix = "kernel_platform/msm-kernel/"
    header = prefix + "drivers/pinctrl/qcom/pinctrl-waipio.h"
    variant = prefix + "drivers/scsi/ufs/ufs-qcom.c"
    board_member = "Kernel/" + prefix + "arch/arm64/boot/dts/samsung/rainbow/g0q/g0q_kor_singlex_w00_r12.dts"
    base_digest, delta_digest = sha(base), sha(delta)
    require(base_digest == "86e2f73412c65fadff0b15bbf0eac9140610f70250514ac0bddbf3b53fb5f7bf"
            and delta_digest == "23ef2b27de8843e271d41405b3c0b1a71bfa668615c8f0f12a1e5c4395ec851a",
            "Samsung base or FYG8 differential archive differs")
    with tarfile.open(delta, "r:gz") as tf:
        names = {m.name.removeprefix("./") for m in tf}
        require(not any(n.endswith((header, variant, "drivers/pinctrl/qcom/pinctrl-waipio.c")) for n in names)
                and tf.extractfile(board_member).read() == VENDOR_BOARD.read_bytes(), "FYG8 differential differs")
    files = {}
    with tarfile.open(base, "r|gz") as stream:
        for member in stream:
            name = member.name.removeprefix("./")
            if name in (header, variant):
                require(member.isfile() and name not in files and member.size < 2**21, "unexpected base source")
                files[name] = stream.extractfile(member).read()
    require(set(files) == {header, variant}, "missing base vendor sources")
    sources = [files[header].decode(), (kernel / "drivers/pinctrl/qcom/pinctrl-sm8450.c").read_text()]
    bases = [cells(stock["/soc/pinctrl@f000000"]["reg"]), cells(main[ML_TLMM]["reg"])]
    bases[1] = [(bases[1][0] << 32) + bases[1][1], (bases[1][2] << 32) + bases[1][3]]
    addresses = []
    for src, (address, size) in zip(sources, bases):
        row = re.search(r"\[210\]\s*=\s*UFS_RESET\(ufs_reset,\s*(0x[0-9a-fA-F]+)\)",src)
        macro = re.search(r"#define UFS_RESET\(pg_name, offset\)(.*?)(?=\n\s*\n)",src,re.S)
        require(row and macro and all(re.search(pattern,macro[1]) for pattern in
                (r"\.ctl_reg\s*=\s*offset,",r"\.io_reg\s*=\s*offset\s*\+\s*0x4,",
                 r"\.out_bit\s*=\s*0,")), "GPIO210 special reset layout differs")
        offset = int(row[1],16)
        require(offset+8 <= size, "reset register outside controller window")
        addresses.append([address+offset, address+offset+4])
    require(addresses[0] == addresses[1] == [0xf1de000,0xf1de004], "GPIO210 reset addresses differ")
    aux = files[variant].decode()
    require('"qcom,vddp-ref-clk"' in aux and '"qcom,vccq-parent"' in aux, "vendor auxiliary vote names differ")
    return dict(stock_and_mainline_ctl_io=addresses, output_bit=0,
                samsung_base_archive_sha256=base_digest, fyg8_delta_sha256=delta_digest,
                base_member_sha256={n:hashlib.sha256(v).hexdigest() for n,v in files.items()})


def ordered(source, function, tokens):
    # Fixed upstream definitions use a column-zero closing brace. Ignore comments,
    # prototypes and diagnostic strings when identifying call sites.
    clean = re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',
                   lambda m: "\n"*m[0].count("\n")+" ", source, flags=re.S)
    match = re.search(r"^\w[^;{}]*?\b" + re.escape(function) + r"\s*\([^;{}]*?\)\s*\{", clean, re.M)
    require(match is not None, "missing function " + function)
    end = clean.index("\n}", match.end())
    body = clean[match.end():end]
    position = 0
    locations = []
    for token in tokens:
        idx = body.find(token, position)
        require(idx >= 0, function + " missing ordered witness " + token)
        locations.append({"token":token, "line":clean.count("\n", 0, match.end()+idx) + 1})
        position = idx + len(token)
    return locations


def effects(kernel):
    src = (kernel / CORE).read_text()
    witnesses = {
        "ufshcd_init": ("ufshcd_hba_init(", "ufshcd_device_reset(", "ufshcd_init_crypto(", "ufshcd_hba_enable(", "ufshcd_add_scsi_host(",
                        "ufshcd_link_startup(", "UFSHCD_QUIRK_SKIP_PH_CONFIGURATION", "goto initialized",
                        "ufshcd_verify_dev_init(", "ufshcd_complete_dev_init(", "ufshcd_device_params_init(",
                        "ufshcd_post_device_init(", "initialized:", "async_schedule(ufshcd_async_scan"),
        "ufshcd_hba_init": ("ufshcd_init_clocks(", "ufshcd_variant_hba_init("),
        "ufshcd_init_clocks": ("ufshcd_parse_dev_ref_clk_freq(", "clk_set_rate("),
        "ufshcd_complete_dev_init": ("UPIU_QUERY_OPCODE_SET_FLAG", "QUERY_FLAG_IDN_FDEVICEINIT",
                                     "UPIU_QUERY_OPCODE_READ_FLAG", "QUERY_FLAG_IDN_FDEVICEINIT"),
        "ufshcd_post_device_init": ("ufshcd_force_reset_auto_bkops(", "ufshcd_set_timestamp_attr(",
                                    "ufshcd_set_dev_ref_clk(", "ufshcd_config_pwr_mode("),
        "ufshcd_async_scan": ("ufshcd_probe_hba(", "ufshcd_add_lus("),
        "ufshcd_probe_hba": ("UFSHCD_QUIRK_REINIT_AFTER_MAX_GEAR_SWITCH", "ufshcd_device_reset(",
                             "ufshcd_device_init(", "ufshcd_set_active_icc_lvl(", "ufshcd_configure_wb(",
                             "ufshcd_write_ee_control("),
        "ufshcd_set_active_icc_lvl": ("UPIU_QUERY_OPCODE_WRITE_ATTR", "QUERY_ATTR_IDN_ACTIVE_ICC_LVL"),
        "ufshcd_add_lus": ("ufshcd_scsi_add_wlus(", "schedule_delayed_work(", "scsi_scan_host("),
    }
    result = {name:ordered(src, name, tokens) for name,tokens in witnesses.items()}
    host = (kernel / "drivers/ufs/host/ufs-qcom.c").read_text()
    result["ufs_qcom_init"] = ordered(host, "ufs_qcom_init", ("devm_gpiod_get_optional(", "GPIOD_OUT_HIGH", "ufs_qcom_ice_init("))
    result["ufshcd_set_dev_ref_clk"] = ordered(src, "ufshcd_set_dev_ref_clk",
                                              ("UPIU_QUERY_OPCODE_READ_ATTR", "UPIU_QUERY_OPCODE_WRITE_ATTR"))
    result["efi_partition"] = ordered((kernel / "block/partitions/efi.c").read_text(), "efi_partition", ("find_valid_gpt(",))
    return result


def run(output):
    output = output.resolve()
    require(output.parent == STUDY and STUDY.resolve() == STUDY, "new ML029 study output required")
    STUDY.mkdir(mode=0o700, exist_ok=True)
    output.mkdir(mode=0o700, exist_ok=False)
    live, dt, config, kernel, locked = inputs()
    stock, main = nodes(live), nodes(dt)
    board = output / "vendor-r12.dtbo"
    def compile_or_run(name, args):
        with (output / (name + ".log")).open("xb") as log:
            subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=True)
    compile_or_run("vendor-dtc", ["dtc", "-I", "dts", "-O", "dtb", "-o", board, VENDOR_BOARD])
    wiring = topology(stock, main, nodes(board)["/__fixups__"])
    configs = config_values(config.read_text())
    selected = {k:configs.get(k,"absent") for k in ("CONFIG_SCSI_UFSHCD","CONFIG_SCSI_UFS_QCOM",
                "CONFIG_PHY_QCOM_QMP_UFS","CONFIG_PINCTRL_SM8450","CONFIG_REGULATOR_QCOM_RPMH",
                "CONFIG_BLK_DEV_SD","CONFIG_SCSI_SCAN_ASYNC","CONFIG_EFI_PARTITION")}
    require(selected["CONFIG_SCSI_UFSHCD"] == selected["CONFIG_PHY_QCOM_QMP_UFS"] == "n" and
            selected["CONFIG_EFI_PARTITION"] == "y", "ML028 discovery config differs")
    source_pins = source_members(kernel, locked)
    order = effects(kernel)
    reset = vendor_reset(stock, main, kernel)
    rehearsal(stock, main, dt, output, compile_or_run)
    report = dict(status="PASS_H0_DISABLED_UFS_DT_REHEARSAL", task_sha256=TASK_SHA, device_actions=0,
                  checker_sha256=sha(__file__), live_fdt_sha256=sha(live), ml028_dtb_sha256=sha(dt), config_sha256=sha(config),
                  vendor_board_sha256=sha(VENDOR_BOARD), upstream_archive_sha256=locked["sha256"],
                  sources=source_pins, source_lines=order, topology=wiring, reset_source_comparison=reset, config=selected,
                  changed_properties=["host/reset-gpios", "phy/vdda-phy-supply", "host/freq-table-hz (ref_clk only)"], study_dtb_sha256=sha(output/"study.dtb"),
                  live_probe_admitted=False, physical_link_observed=False, device_or_media_io_observed=False,
                  unresolved=["PM8350 L6/L9 upstream input and vendor auxiliary vote semantics",
                              "active pinctrl and PHY/controller behavior on g0q", "bounded pre-media driver effects"])
    (output/"result.json").write_text(json.dumps(report,indent=2)+"\n")
    return report


def rehearsal(stock, main, dt, output, invoke):
    # No provider is created. Both consumers and the TLMM controller stay disabled.
    source = output / "disabled-ufs.dts"
    rates = clock_ranges(stock[STOCK["host"]])
    names = texts(main[MAIN["host"]]["clock-names"])
    translated = [n for name in names for n in rates[name]]
    pairs = " ".join(str(n) for n in translated)
    source.write_text("/dts-v1/;\n/plugin/;\n"
                      f"&ufs_mem_hc {{ reset-gpios = <&tlmm 210 1>; freq-table-hz = <{pairs}>; }};\n"
                      "&ufs_mem_phy { vdda-phy-supply = <&vreg_l5b_0p88>; };\n")
    overlay, study = output/"disabled-ufs.dtbo", output/"study.dtb"
    invoke("overlay-dtc", ["dtc","-@","-I","dts","-O","dtb","-o",overlay,source])
    invoke("overlay-apply", ["fdtoverlay","-i",dt,"-o",study,overlay])
    patched = nodes(study)
    expected = {path:dict(props) for path,props in main.items()}
    expected[MAIN["host"]]["reset-gpios"] = main[ML_TLMM]["phandle"] + struct.pack(">II",210,1)
    expected[MAIN["phy"]]["vdda-phy-supply"] = main[RPMH+"/ldo5"]["phandle"]
    expected[MAIN["host"]]["freq-table-hz"] = struct.pack(f">{len(translated)}I", *translated)
    require(patched == expected, "study changed more than the three selected properties")
    restored = output/"changes-removed.dtb"
    restored.write_bytes(study.read_bytes())
    for role, prop in (("host","reset-gpios"),("phy","vdda-phy-supply")):
        invoke("remove-"+role,["fdtput","-d",restored,MAIN[role],prop])
    original = cells(main[MAIN["host"]]["freq-table-hz"])
    invoke("restore-clock-rates",["fdtput","-t","u",restored,MAIN["host"],"freq-table-hz",*map(str,original)])
    for label,path in (("baseline",dt),("restored",restored)):
        invoke("canonical-"+label,["dtc","-s","-I","dtb","-O","dtb","-o",output/(label+".canonical"),path])
    require((output/"baseline.canonical").read_bytes() == (output/"restored.canonical").read_bytes(),
            "canonical DT or reserve map changed after removing study edges")


if __name__ == "__main__":
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    print(run(parser.parse_args().output)["status"])
