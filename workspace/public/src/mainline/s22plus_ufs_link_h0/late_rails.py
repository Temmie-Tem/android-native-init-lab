"""Build the four missing PM8350 regulator registrations from the pinned kernel driver."""
import argparse
import json
import os
from pathlib import Path
import re
from cold_phy_tables import PRIVATE, digest, require

SOURCE_SHA = "bd7f9cd8dcdb065ae38bc13c0ef6acc887a5bd796758c99c915819ec3fc2e596"
SELECTED = ("ldo6", "ldo7", "ldo9", "smps12")


def generate(source, output):
    require(source.resolve().is_relative_to(PRIVATE.resolve()) and
            output.resolve().is_relative_to(PRIVATE.resolve()), "private inputs and output required")
    require(digest(source) == SOURCE_SHA, "ML028 RPMh source differs")
    output.mkdir(mode=0o700)
    text = source.read_text()
    # Reuse the stock mainline resource lookup, regulator ops and connected
    # RPMh device. The existing USB L5 registration is never duplicated.
    prefix = text.split("static const struct rpmh_vreg_init_data pm8998_vreg_data[]", 1)[0]
    signature = "static int rpmh_regulator_send_request("
    require(prefix.count(signature) == 1, "RPMh register write boundary differs")
    prefix = prefix.replace(signature, "static bool rail_requests_open;\n\n" + signature)
    start = prefix.index(signature)
    marker = "\n\tif (wait_for_ack || vreg->always_wait_for_ack)"
    require(prefix[start:].count(marker) == 1, "RPMh send implementation differs")
    prefix = prefix[:start] + prefix[start:].replace(
        marker, "\n\tif (!READ_ONCE(rail_requests_open))\n\t\treturn -EPERM;\n" + marker)
    lookup = "\tvreg->addr = cmd_db_read_addr(rpmh_resource_name);"
    require(prefix.count(lookup) == 1, "VRM lookup differs")
    prefix = prefix.replace(lookup, "\tif (cmd_db_read_slave_id(rpmh_resource_name) != CMD_DB_HW_VRM)\n"
                            "\t\treturn -ENODEV;\n" + lookup)
    data = text.split("static const struct rpmh_vreg_init_data pm8350_vreg_data[] = {", 1)[1].split("};", 1)[0]
    rows = []
    for name in SELECTED:
        line, = [row for row in data.splitlines() if f'RPMH_VREG("{name}",' in row]
        # On FYG8 these four resources have no Linux parent phandle. The AOP
        # retains its own associations. Do not synthesize an upstream LDO supply.
        line, count = re.subn(r',\s*"vdd-[^"]+"\),$', ', NULL),', line)
        require(count == 1, "expected one parent name in the PM8350 descriptor")
        rows.append(line)
    probe = text.split("static int rpmh_regulator_probe(", 1)[1].split(
        "static const struct of_device_id __maybe_unused rpmh_regulator_match_table", 1)[0]
    result = prefix + "\nstatic const struct rpmh_vreg_init_data late_pm8350[] = {\n"
    result += "\n".join(rows) + "\n\t{}\n};\n"
    result += "static int rpmh_regulator_probe(" + probe
    result += """
static const struct of_device_id late_matches[] = {
    { .compatible = "samsung,g0q-ml030-ufs-rails", .data = late_pm8350 },
    {}
};

static struct platform_driver late_driver = {
    .driver = {
        .name = "g0q-ml030-rails",
        .of_match_table = late_matches,
        .probe_type = PROBE_FORCE_SYNCHRONOUS,
        .suppress_bind_attrs = true,
    },
};

int ml030_register_rails(void);
void ml030_open_rail_requests(void);
void ml030_open_rail_requests(void)
{
    WRITE_ONCE(rail_requests_open, true);
}

int ml030_register_rails(void)
{
    return platform_driver_probe(&late_driver, rpmh_regulator_probe);
}
"""
    (output / "rails.c").write_text(result)
    (output / "result.json").write_text(json.dumps(dict(status="H0_LATE_RAIL_SOURCE",
        source_sha256=SOURCE_SHA, selected=list(SELECTED), output_sha256=digest(output/"rails.c"),
        device_actions=0), indent=2)+"\n")


if __name__ == "__main__":
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    generate(args.source, args.output)
