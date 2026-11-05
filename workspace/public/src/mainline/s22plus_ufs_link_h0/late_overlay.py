"""Produce a private, late-only g0q rail and link-consumer overlay for H0 checks."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts/analysis"))
import s22plus_mainline_ufs_h0 as study

RSC = "/soc@0/rsc@17a00000"
BANK = RSC + "/ml030-ufs-rails"
CONSUMER = "/soc@0/ml030-link@1d84000"
RAILS = {
    "ldo6": ("pm8350_l6", 1200000, 1200000, 1200000),
    "ldo7": ("pm8350_l7", 2504000, 2504000, 2504000),
    "ldo9": ("pm8350_l9", 1200000, 1200000, 1200000),
    "smps12": ("pm8350_s12", 1224000, 1400000, 1256000),
}


def references(main, raw, kind):
    providers = study.providers(main)
    symbols = {v.decode().rstrip("\0"): k for k, v in main["/__symbols__"].items()}
    parts = []
    values = study.cells(raw)
    while values:
        path = providers[values[0]]
        count = study.cells(main[path][f"#{kind}-cells"])[0] if kind else 0
        study.require(len(values) >= 1 + count and path in symbols, "unresolved provider")
        parts.append("<&" + symbols[path] + "".join(f" {v}" for v in values[1:1+count]) + ">")
        values = values[1+count:]
    return ", ".join(parts)


def build(output):
    study.require(output.resolve().is_relative_to(study.PRIVATE.resolve()), "private output required")
    live, baseline, _, _, _ = study.inputs()
    stock, main = study.nodes(live), study.nodes(baseline)
    output.mkdir(mode=0o700, exist_ok=False)
    host = main[study.MAIN["host"]]
    phy = main[study.MAIN["phy"]]
    stock_id = study.providers(stock)
    bank_nodes = []
    for name, (symbol, low, high, initial) in RAILS.items():
        ref = stock["/__symbols__"][symbol].decode().rstrip("\0")
        props = stock[ref]
        study.require([study.cells(props[k])[0] for k in ("regulator-min-microvolt",
                      "regulator-max-microvolt", "qcom,init-voltage")] == [low, high, initial]
                      and study.cells(props["qcom,set"]) == [3], "FYG8 rail declaration differs")
        resource = stock[ref.rsplit("/", 1)[0]]
        expected_resource = ("ldob" + name[3:]) if name.startswith("ldo") else "smpb12"
        study.require(study.texts(resource["qcom,resource-name"]) == [expected_resource]
                      and study.RPMH + "/" + name not in main, "duplicate or wrong RPMh resource")
        mode = ('regulator-allow-set-load; '
                'regulator-allowed-modes = <1 3>;' if name.startswith("ldo") else "")
        bank_nodes.append(f"""
                rail_{name}: {name} {{
                    regulator-name = "ml030-{symbol}";
                    regulator-min-microvolt = <{low}>;
                    regulator-max-microvolt = <{high}>;
                    {mode}
                    qcom,always-wait-for-ack;
                }};
        """)
    original_l5 = main[study.RPMH + "/ldo5"]
    usb = main["/soc@0/phy@88e3000"]
    study.require(original_l5["phandle"] == usb["vdda-pll-supply"]
                  and study.cells(original_l5["regulator-initial-mode"]) == [3],
                  "shared USB L5 binding or mode differs")
    study.require(study.texts(host["status"]) == study.texts(phy["status"]) == ["disabled"]
                  and host["power-domains"] == phy["power-domains"]
                  and study.cells(stock[study.STOCK["host"]]["vdd-hba-supply"]) and
                  stock_id[study.cells(stock[study.STOCK["host"]]["vdd-hba-supply"])[0]] ==
                  "/soc/qcom,gdsc@187004", "host power domain differs")
    # Firmware may have populated a live controller before Linux. This node is
    # created only from a separate overlay; its pre-dwell platform probe is impossible.
    names = study.texts(host["clock-names"]) + ["phy-" + s for s in study.texts(phy["clock-names"])]
    names += ["rx0-mux", "rx1-mux", "tx0-mux"]
    # These three GCC selector IDs are from the pinned SM8450 clock binding.
    clocks = references(main, host["clocks"] + phy["clocks"], "clock")
    clocks += ", <&gcc 161>, <&gcc 163>, <&gcc 165>"
    properties = "\n".join([
        "clock-names = " + ", ".join(json.dumps(s) for s in names) + ";",
        "clocks = " + clocks + ";",
        "power-domains = " + references(main, host["power-domains"], "power-domain") + ";",
        "resets = " + references(main, host["resets"], "reset") + ";",
        'reset-names = "rst";',
        "interconnects = " + references(main, host["interconnects"], "interconnect") + ";",
        'interconnect-names = "ufs-ddr", "cpu-ufs";',
        "vdda-phy-supply = " + references(main, original_l5["phandle"], None) + ";",
    ])
    fragment = """/dts-v1/;
/plugin/;
/ {
    fragment@0 {
        target-path = "%s";
        __overlay__ {
            ml030-ufs-rails {
                compatible = "samsung,g0q-ml030-ufs-rails";
                qcom,pmic-id = "b";
                %s
            };
        };
    };
    fragment@1 {
        target-path = "/soc@0";
        __overlay__ {
            #address-cells = <2>;
            #size-cells = <2>;
            ml030-link@1d84000 {
                compatible = "samsung,g0q-ml030-link";
                reg = <0 0x1d84000 0 0x1000>, <0 0x1d87000 0 0xe10>,
                      <0 0x0f1de000 0 8>;
                reg-names = "hci", "phy", "reset-pin";
                %s
                vdda-pll-supply = <&rail_ldo6>;
                vcc-supply = <&rail_ldo7>;
                vccq-supply = <&rail_ldo9>;
                ref-pad-supply = <&rail_ldo9>;
                parent-supply = <&rail_smps12>;
            };
        };
    };
    fragment@2 {
        target-path = "/soc@0/phy@1d87000";
        __overlay__ {
            compatible = "samsung,g0q-ml030-symbol-clocks";
            status = "okay";
        };
    };
};
""" % (RSC, "".join(bank_nodes), properties)
    dts = output / "late.dts"
    dts.write_text(fragment)
    overlay, applied = output / "late.dtbo", output / "applied.dtb"
    subprocess.run(["dtc", "-@", "-I", "dts", "-O", "dtb", "-o", overlay, dts], check=True)
    subprocess.run(["fdtoverlay", "-i", baseline, "-o", applied, overlay], check=True)
    staged = study.nodes(applied)
    # GCC resolves the three existing references only on an available node.
    # Its late clock-only compatible has no matching QMP/platform driver.
    symbol_node = study.MAIN["phy"]
    study.require(staged[symbol_node] == dict(main[symbol_node],
                  compatible=b"samsung,g0q-ml030-symbol-clocks\0", status=b"okay\0"),
                  "unexpected symbol-provider changes")
    study.require(all(staged[k] == v for k, v in main.items() if k not in ("/__symbols__", symbol_node)),
                  "overlay changed a preexisting device")
    study.require(set(staged) - set(main) <= {"/__symbols__", BANK, CONSUMER,
                  *(BANK + "/" + n for n in RAILS)}, "unexpected staged device")
    wired = study.providers(staged)
    expected = {"vdda-phy":study.RPMH + "/ldo5", "vdda-pll":BANK+"/ldo6", "vcc":BANK+"/ldo7",
                "vccq":BANK+"/ldo9", "ref-pad":BANK+"/ldo9", "parent":BANK+"/smps12"}
    for k, path in expected.items():
        study.require(wired[study.cells(staged[CONSUMER][k+"-supply"])[0]] == path, "rail handle differs")
    result = dict(status="PASS_H0_G0Q_LATE_DT_BINDINGS", baseline_sha256=study.sha(baseline),
                  overlay_sha256=study.sha(overlay), applied_sha256=study.sha(applied),
                  late_symbol_provider=symbol_node, device_actions=0, physical_registration=False)
    (output/"result.json").write_text(json.dumps(result, indent=2)+"\n")
    return result


if __name__ == "__main__":
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(build(parser.parse_args().output)["status"])
