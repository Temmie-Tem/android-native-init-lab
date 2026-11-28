"""Roadmap step 4a: the late overlay that hands g0q UFS to the upstream drivers.

Applied after the permit by the stage module; nothing in the boot DT changes. It follows the upstream
SM8450 QRD/HDK wiring, which matches every rail the fixed module measured on g0q:
  - one more ordinary PM8350 ("b") rpmh-regulator device under apps RSC with only smps12, ldo6, ldo7,
    ldo9; fixed voltages (min = max), so the regulator core refuses any other voltage from any context;
    S12B is the parent of L6B/L9B (vdd-l6-l9-l10) at the stock initial 1.256 V; L7B gets no Linux parent,
    so no vote reaches the shared BOB rail;
  - the existing ufshc@1d84000 and phy@1d87000 nodes set "okay" with the QRD supplies and loads;
    vdda-phy stays the existing USB-held L5B node (0.88 V range, unchanged).
No reset-gpios: the route DT keeps TLMM disabled, so ufs-qcom runs without a device reset (its
-EOPNOTSUPP path) instead of enabling the generic pinctrl driver. qcom,ice stays in the dtsi node, but
the gated build has SCSI_UFS_CRYPTO=n and no ICE driver, so it is never used.

usage: python3 -I upstream_overlay.py <output dir> [<baseline dtb>]
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts/analysis"))
import s22plus_mainline_ufs_h0 as study  # noqa: E402

ROOT = HERE.parents[4]
ROUTE_DTB = ROOT / "workspace/private/analysis/s22plus-max77705-observe-h0.2QtaVD7S/g0q-ml053-i2c5.dtb"
ROUTE_DTB_SHA256 = "51b58a406d00297bf5b91537864f8768ed8ac14825f328032c4406cd1a118235"
RSC = "/soc@0/rsc@17a00000"
BANK = RSC + "/regulators-9"   # binding: ^regulators(-[0-9])?$; route DT uses -0 and -1
HOST, PHY = study.MAIN["host"], study.MAIN["phy"]
L5 = study.RPMH + "/ldo5"
# name: (label, microvolts, ldo?)  -- values = stock FYG8 declarations / module-measured votes
RAILS = {"smps12": ("g0q_ufs_s12b", 1256000, False), "ldo6": ("g0q_ufs_l6b", 1200000, True),
         "ldo7": ("g0q_ufs_l7b", 2504000, True), "ldo9": ("g0q_ufs_l9b", 1200000, True)}
HOST_PROPS = {"vcc-supply": "ldo7", "vccq-supply": "ldo9", "vdd-hba-supply": "ldo9"}
LOADS = {"vcc-max-microamp": 1100000, "vccq-max-microamp": 1200000}


def source():
    rails = []
    for name, (label, uv, ldo) in RAILS.items():
        extra = ("regulator-initial-mode = <3>;\n\t\t\t\tregulator-allowed-modes = <1 3>;\n"
                 "\t\t\t\tregulator-allow-set-load;\n" if ldo else "")
        rails.append(f"""
			{label}: {name} {{
				regulator-name = "{label}";
				regulator-min-microvolt = <{uv}>;
				regulator-max-microvolt = <{uv}>;
				{extra}			}};""")
    host = "\n".join(f"\t\t\t{k} = <&{RAILS[v][0]}>;" for k, v in HOST_PROPS.items())
    loads = "\n".join(f"\t\t\t{k} = <{v}>;" for k, v in LOADS.items())
    return f"""/dts-v1/;
/plugin/;
/ {{
	fragment@0 {{
		target-path = "{RSC}";
		__overlay__ {{
			regulators-9 {{
				compatible = "qcom,pm8350-rpmh-regulators";
				qcom,pmic-id = "b";
				vdd-s12-supply = <&vph_pwr>;
				vdd-l6-l9-l10-supply = <&g0q_ufs_s12b>;
{"".join(rails)}
			}};
		}};
	}};
	fragment@1 {{
		target-path = "{PHY}";
		__overlay__ {{
			status = "okay";
			vdda-phy-supply = <&vreg_l5b_0p88>;
			vdda-pll-supply = <&g0q_ufs_l6b>;
		}};
	}};
	fragment@2 {{
		target-path = "{HOST}";
		__overlay__ {{
			status = "okay";
{host}
{loads}
		}};
	}};
}};
"""


def build(output, baseline=ROUTE_DTB):
    study.require(study.sha(baseline) == ROUTE_DTB_SHA256, "baseline is not the route DT 51b58a40")
    main = study.nodes(baseline)
    study.require(study.texts(main[HOST]["status"]) == study.texts(main[PHY]["status"]) == ["disabled"]
                  and study.texts(main["/soc@0/pinctrl@f100000"]["status"]) == ["disabled"]
                  and BANK not in main and "reset-gpios" not in main[HOST], "baseline UFS/TLMM state differs")
    symbols = {k: v.decode().rstrip("\0") for k, v in main["/__symbols__"].items()}
    study.require(symbols["vreg_l5b_0p88"] == L5 and symbols["vph_pwr"] == "/regulator-vph-pwr"
                  and study.texts(main[study.RPMH]["qcom,pmic-id"]) == ["b"], "provider symbols differ")
    output.mkdir(mode=0o700)
    dts, overlay, applied = output / "upstream.dts", output / "upstream.dtbo", output / "applied.dtb"
    dts.write_text(source())
    subprocess.run(["dtc", "-@", "-q", "-I", "dts", "-O", "dtb", "-o", overlay, dts], check=True)
    subprocess.run(["fdtoverlay", "-i", baseline, "-o", applied, overlay], check=True)
    staged = study.nodes(applied)
    added = {k for k in set(staged) - set(main) if k != "/__symbols__"}
    study.require(added == {BANK, *(BANK + "/" + n for n in RAILS)}, f"unexpected nodes {added}")
    for path, props in main.items():   # only the two UFS nodes change, and only by additions + status
        if path in ("/__symbols__", HOST, PHY):
            continue
        study.require(staged[path] == props, "overlay changed " + path)
    for path in (HOST, PHY):
        for k, v in main[path].items():
            study.require(k == "status" or staged[path][k] == v, f"{path} {k} changed")
        study.require(study.texts(staged[path]["status"]) == ["okay"], path + " not enabled")
    wired = study.providers(staged)
    supplies = {f"{HOST}:{k}": BANK + "/" + v for k, v in HOST_PROPS.items()}
    supplies.update({f"{PHY}:vdda-phy-supply": L5, f"{PHY}:vdda-pll-supply": BANK + "/ldo6",
                     f"{BANK}:vdd-l6-l9-l10-supply": BANK + "/smps12",
                     f"{BANK}:vdd-s12-supply": "/regulator-vph-pwr"})
    for key, want in supplies.items():
        node, prop = key.split(":")
        study.require(wired[study.cells(staged[node][prop])[0]] == want, key + " wired wrong")
    for name, (label, uv, ldo) in RAILS.items():
        props = staged[BANK + "/" + name]
        study.require(study.cells(props["regulator-min-microvolt"]) == study.cells(
            props["regulator-max-microvolt"]) == [uv], name + " voltage not fixed")
    study.require("vdd-l2-l7-supply" not in staged[BANK], "BOB parent must not be wired")
    study.require(not any(k.startswith("reset") and k != "resets" and k != "reset-names"
                          for k in staged[HOST]), "device reset GPIO must stay absent")
    result = dict(status="PASS_H0_G0Q_UPSTREAM_UFS_OVERLAY", baseline_sha256=study.sha(baseline),
                  overlay_sha256=study.sha(overlay), applied_sha256=study.sha(applied),
                  dts_sha256=study.sha(dts), rails={k: v[1] for k, v in RAILS.items()},
                  host_supplies=HOST_PROPS, loads=LOADS, reset_gpio=False, device_actions=0)
    (output / "result.json").write_text(json.dumps(result, indent=1) + "\n")
    return result


if __name__ == "__main__":
    os.umask(0o077)
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    cli.add_argument("baseline", type=Path, nargs="?", default=ROUTE_DTB)
    a = cli.parse_args()
    print(json.dumps(build(a.output, a.baseline), indent=1))
