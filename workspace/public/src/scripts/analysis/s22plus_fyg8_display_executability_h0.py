"""Source-bounded display DT prerequisites; host-only, never live authority.

Reuse the retained kernel's fw_devlink parser, while adding the display
component, named-regulator, indexed-RPMh and device-creation relationships.
Unknown device mappings/creators reject rather than becoming empty closures.
Runtime binding and successful DRM creation remain separate witnesses.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'workspace/public/src/scripts/revalidation'))
import s22plus_fyg8_p317_executability_fixed_point as fixed

KERNEL = ROOT / fixed.claims.DEFAULT_KERNEL_ROOT
DISPLAY = ROOT / 'workspace/private/outputs/s22-display-build-h0/display-drivers'
PROVIDERS = ROOT / 'workspace/private/outputs/s22-display-provider-h0'
MASTER = '/soc/qcom,mdss_mdp@ae00000'
PRIMARY = '/soc/qcom,dsi-display-primary'
SECONDARY = '/soc/qcom,dsi-display-secondary'
PANEL = MASTER + '/ss_dsi_panel_S6E3FAC_AMB655AY01_FHD'
BUS = '/i2c@50'
PMIC = BUS + '/s2dos05_pmic@60'
SCHEMA = 's22plus-fyg8-display-executability-h0-v1'

# These tables qualify only the named input sources, not arbitrary drivers.
SOURCE_MODULES = {
    'samsung,s2dos05pmic': ('s2dos05-regulator.ko', 'drivers/regulator/s2dos05/s2dos05.c'),
    'qcom,gdsc': ('gdsc-regulator.ko', 'drivers/clk/qcom/gdsc-regulator.c'),
    'qcom,rpmh-vrm-regulator': ('rpmh-regulator.ko', 'drivers/regulator/rpmh-regulator.c'),
    'qcom,rpmh-arc-regulator': ('rpmh-regulator.ko', 'drivers/regulator/rpmh-regulator.c'),
    'qcom,qsmmuv500-tbu': ('arm_smmu.ko', 'drivers/iommu/arm/arm-smmu/arm-smmu-qcom.c'),
}
DISPLAY_MODULES = {
    'qcom,dsi-display': 'msm/dsi/dsi_display.c',
    'qcom,dsi-ctrl-hw-v2.6': 'msm/dsi/dsi_ctrl.c',
    'qcom,dsi-phy-v4.3': 'msm/dsi/dsi_phy.c',
    'qcom,sde-kms': 'msm/msm_drv.c',
    'qcom,sde-rsc': 'msm/sde_rsc.c',
    'qcom,sde-rsc-rpmh': 'msm/sde_rsc.c',
    'qcom,smmu_sde_sec': 'msm/msm_smmu.c',
    'qcom,smmu_sde_unsec': 'msm/msm_smmu.c',
    'qcom,wb-display': 'msm/sde/sde_wb.c',
}


class ClosureError(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise ClosureError(reason)


def identity(path):
    return fixed.receipt(fixed.stable_read(Path(path), 'closure input', 64 << 20))


def strings(node, key):
    return fixed._strings(node.properties[key], node.path + ':' + key)


def references(tree, node, key):
    require(key in node.properties, 'missing driver reference: ' + node.path + ':' + key)
    values = fixed._cells(node.properties[key], node.path + ':' + key)
    require(all(v in tree.phandles for v in values), 'unresolved driver reference: ' + key)
    return [tree.phandles[v] for v in values]


def creator(node):
    parent = node.parent
    if 'qcom,cmd-db' in node.compatible:
        require(parent.path == '/reserved-memory', 'command DB moved')
        return 'builtin:of_platform_default_populate', 'reserved_mem_matches/qcom,cmd-db'
    if node.path == BUS:
        require(parent.path == '/' and 'reg' not in node.properties, 'display GPIO bus naming changed')
        return 'builtin:of_platform_default_populate', 'root_platform_device'
    if node.path == PMIC:
        require(parent.path == BUS, 'display PMIC moved')
        return parent.path, 'i2c_add_adapter/of_i2c_register_devices'
    if parent and 'qcom,rpmh-rsc' in parent.compatible:
        return parent.path, 'rpmh_rsc/devm_of_platform_populate'
    if parent and 'qcom,qsmmu-v500' in parent.compatible:
        require('qcom,qsmmuv500-tbu' in node.compatible, 'unknown SMMU child')
        return parent.path, 'qsmmuv500_create/of_platform_populate'
    rows = fixed.instantiation_edges(None, node)
    require(len(rows) == 1, 'ambiguous device creator')
    return rows[0]['instantiator'], rows[0]['mechanism']


def mapping(node, metadata, config, source_texts):
    if node.path == BUS:
        return {'module': 'i2c-gpio.ko', 'kind': 'reviewed_exact_platform_id_i2c@50'}
    for compatible in node.compatible:
        if compatible in DISPLAY_MODULES:
            path = DISPLAY / DISPLAY_MODULES[compatible]
            require('"' + compatible + '"' in source_texts[path], 'display match source drift')
            return {'module': 'msm_drm.ko', 'kind': 'source_bound_internal_driver', 'source': str(path.relative_to(ROOT))}
        if compatible in SOURCE_MODULES:
            module, relative = SOURCE_MODULES[compatible]
            path = KERNEL / 'msm-kernel' / relative
            require('"' + compatible + '"' in source_texts[path], 'provider match source drift')
            return {'module': module, 'kind': 'source_bound_driver', 'source': str(path.relative_to(ROOT))}
    return fixed._module_for_node(node, metadata, config)


def derive(tree, rows, rules, metadata, config, source_texts, module_names):
    roots = (MASTER, PRIMARY, SECONDARY, BUS, PMIC)
    require(all(p in tree.nodes for p in (*roots, PANEL)), 'exact display roots missing')
    bus = tree.nodes[BUS]
    require(bus.compatible == ('i2c-gpio',), 'display bus driver type changed')
    gpio = fixed._cells(bus.properties['gpios'], 'display I2C GPIOs')
    require(len(gpio) == 6 and gpio[0] == gpio[3] and gpio[1:3] == (20, 0)
            and gpio[4:6] == (21, 0) and gpio[0] in tree.phandles
            and 'qcom,waipio-pinctrl' in tree.phandles[gpio[0]].compatible,
            'display I2C pin scope changed')
    require(fixed._cells(bus.properties['cell-index'], 'display bus index') == (50,), 'display bus index changed')
    children = [n.path for n in tree.nodes.values() if n.parent is bus and n.available]
    require(children == [PMIC], 'display I2C child scope changed')
    pmic = tree.nodes[PMIC]
    require(pmic.compatible == ('samsung,s2dos05pmic',)
            and fixed._cells(pmic.properties['reg'], 'PMIC address') == (0x60,)
            and fixed._cells(pmic.properties['adc_mode'], 'PMIC ADC mode') == (0,)
            and fixed._cells(pmic.properties['adc_sync_mode'], 'PMIC ADC sync') == (2,)
            and 'ocl_elvss' not in pmic.properties, 'display PMIC init scope changed')
    require('qcom,dsi-default-panel' not in tree.nodes[SECONDARY].properties,
            'secondary panel changes required scope')
    edges, skipped, evaluated = [], [], []
    seen, frontier = set(), set(roots)

    def edge(consumer, supplier, family, mechanism, **extra):
        edges.append(dict(consumer=consumer, supplier=supplier, family=family, mechanism=mechanism, **extra))
        if supplier.startswith('/') and supplier not in seen:
            require(supplier in tree.nodes, 'dependency escaped exact tree')
            frontier.add(supplier)

    # Panel descriptors are data consumed by the primary driver's named lookup;
    # they are not independently probed platform devices.
    panel_data = [n for n in tree.nodes.values() if n.path == PANEL or n.path.startswith(PANEL + '/')]
    named = []
    for n in panel_data:
        for key in ('qcom,supply-name', 'reg,name'):
            if key not in n.properties:
                continue
            name, = strings(n, key)
            providers = [p for p in tree.nodes.values() if p.properties.get('regulator-name') == (name + '\0').encode()]
            require(len(providers) == 1 and providers[0].path.startswith(PMIC + '/regulators/'), 'named regulator resolution differs: ' + name)
            named.append(name)
            edge(PRIMARY, PMIC, 'driver', 'named_regulator_lookup', name=name, consumer_data=n.path, supplier_data=providers[0].path)
    require(set(named) == {'panel_vdd3', 'panel_vddr', 'panel_vci', 'panel_aee_fd', 'panel_elvss'}, 'panel regulator consumer set changed')
    for n in panel_data:
        for e in fixed.fw_edges(tree, n, rows, rules, tuple(rules)):
            if e['owner']:
                edge(PRIMARY, e['owner'], 'fw', e['parser'], property=e['property'], consumer_data=n.path)

    while frontier:
        path = min(frontier)
        frontier.remove(path)
        if path in seen:
            continue
        seen.add(path)
        node = tree.nodes[path]
        require(node.available, 'required node disabled: ' + path)
        for e in fixed.fw_edges(tree, node, rows, rules, tuple(rules)):
            if e['owner']:
                edge(path, e['owner'], 'fw', e['parser'], property=e['property'])
            else:
                skipped.append(e)
        owner, mechanism = creator(node)
        edge(path, owner, 'creator', mechanism)

        if path == MASTER:
            for target in references(tree, node, 'connectors'):
                if target.path.rsplit('/', 1)[-1].startswith('qcom,dp_display'):
                    skipped.append({'consumer': path, 'supplier': target.path, 'reason': 'CONFIG_SECDP disabled in bound build'})
                else:
                    edge(path, target.path, 'driver', 'component_match_add/connectors')
        if path in (PRIMARY, SECONDARY):
            for key in ('qcom,mdp', 'qcom,dsi-ctrl', 'qcom,dsi-phy'):
                for target in references(tree, node, key):
                    edge(path, target.path, 'driver', 'dsi_display resource validation', property=key)
        if 'qcom,sde-rsc' in node.compatible:
            candidates = [n for n in tree.nodes.values() if n.available and 'qcom,sde-rsc-rpmh' in n.compatible]
            # Source uses SDE_RSC_INDEX + a registration counter, not this node's
            # DT cell-index. Exactly one active instance makes that index zero.
            active_rsc = [n for n in tree.nodes.values() if n.available and 'qcom,sde-rsc' in n.compatible]
            require(len(active_rsc) == 1 and len(candidates) == 1, 'indexed RSC scope changed')
            require(fixed._cells(candidates[0].properties['cell-index'], 'RSC index') == (0,), 'RSC RPMh index differs')
            edge(path, candidates[0].path, 'driver', 'rpmh_dev[SDE_RSC_INDEX + counter]')
        if 'qcom,qsmmu-v500' in node.compatible:
            for child in tree.nodes.values():
                if child.parent is node and child.available and child.compatible:
                    edge(path, child.path, 'driver', 'device_for_each_child/qsmmuv500_tbu_register')
        if 'qcom,bcm-voters' in node.properties:
            for target in references(tree, node, 'qcom,bcm-voters'):
                require('qcom,bcm-voter' in target.compatible, 'BCM voter type differs')
                edge(path, target.path, 'driver', 'of_bcm_voter_get')
        if ('qcom,rpmh-rsc' in node.compatible or 'qcom,waipio-rpmh-clk' in node.compatible
                or 'qcom,bcm-voters' in node.properties):
            providers = [n for n in tree.nodes.values() if n.available and 'qcom,cmd-db' in n.compatible]
            require(len(providers) == 1, 'command DB provider unavailable or ambiguous')
            edge(path, providers[0].path, 'driver', 'global cmd_db_ready/read_addr provider')
        if 'qcom,gdsc' in node.compatible:
            require(not {'sw-reset', 'qcom,clk-ctrl', 'qcom,collapse-vote'} & node.properties.keys(),
                    'unreviewed optional GDSC phandle family')
        if path == PMIC:
            suppliers = fixed._parse_generic_phandles(tree, node, 's2dos05,s2dos05_int', {'cells_property': '#gpio-cells'})
            require(len(suppliers) == 1, 'PMIC IRQ provider differs')
            edge(path, suppliers[0].path, 'driver', 'of_get_named_gpio/s2dos05_int')
        mapped = mapping(node, metadata, config, source_texts)
        require(mapped.get('module') is None or mapped['module'] in module_names, 'missing required module: ' + str(mapped))
        evaluated.append(dict(path=path, compatible=node.compatible, mapping=mapped,
                              families=['fw', 'creator', 'driver']))
    return dict(nodes=sorted(evaluated, key=lambda n: n['path']), edges=edges,
                skipped=skipped, named_regulators=sorted(named), converged=True)


def source_inputs():
    paths = {DISPLAY / p for p in DISPLAY_MODULES.values()}
    paths.update(KERNEL / 'msm-kernel' / p for _, p in SOURCE_MODULES.values())
    paths.update(KERNEL / p for p in (
        'common/drivers/of/property.c', 'common/drivers/of/platform.c',
        'common/drivers/of/base.c', 'common/drivers/of/irq.c', 'common/drivers/base/core.c',
        'common/drivers/i2c/i2c-core-of.c', 'common/drivers/i2c/i2c-core-base.c',
        'msm-kernel/drivers/interconnect/qcom/bcm-voter.c',
        'msm-kernel/drivers/interconnect/qcom/icc-rpmh.c',
        'msm-kernel/drivers/soc/qcom/cmd-db.c',
        'msm-kernel/drivers/clk/qcom/clk-rpmh.c',
        'msm-kernel/drivers/soc/qcom/rpmh-rsc.c',
        'msm-kernel/drivers/mfd/qcom-spmi-pmic.c', 'common/drivers/spmi/spmi.c',
    ))
    paths.update(DISPLAY / p for p in ('msm/dsi/dsi_pwr.c', 'msm/dsi/dsi_panel.c',
        'msm/samsung/ss_dsi_panel_common.c', 'include/linux/sde_rsc.h',
        'config/gki_waipiodispconf.h', 'config/gki_waipiodisp.conf',
        'msm/samsung/panel_common_conf.h', 'msm/Kbuild', 'msm/.msm_drv.o.cmd'))
    paths.update(Path(m.__file__).resolve() for m in (fixed, fixed.fw, fixed.module_plan, fixed.stock_dt))
    return {p: fixed.stable_read(p, 'source input', 16 << 20).decode() for p in sorted(paths)}


def check_dp_disabled(texts, vendor_config):
    for relative in ('config/gki_waipiodispconf.h', 'msm/samsung/panel_common_conf.h'):
        require(re.search(r'^\s*#\s*define\s+CONFIG_SECDP(?:\s|$)', texts[DISPLAY / relative], re.M) is None,
                'DP compile definition changed: ' + relative)
    require(re.search(r'^CONFIG_SECDP(?:_MODULE)?=[ym]$', vendor_config, re.M) is None,
            'DP kernel configuration changed')
    require('-DCONFIG_SECDP' not in texts[DISPLAY / 'msm/.msm_drv.o.cmd'], 'DP compiler flag changed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    extractor = identity(Path(__file__))
    texts = source_inputs()
    config = (ROOT / fixed.DEFAULT_CONFIG).read_text()
    fixed.require_sha(config.encode(), fixed.CONFIG_SHA256, 'fixed Image configuration')
    vendor_config = ROOT / 'workspace/private/outputs/s22-display-build-h0/vendor-kernel-out/.config'
    require(hashlib.sha256(vendor_config.read_bytes()).hexdigest() == '2736604721dd2fc613f04fbe00f1d0da613905f15ba5815dd3b11c69ee61fea8', 'display config drift')
    check_dp_disabled(texts, vendor_config.read_text())
    require('#define SDE_RSC_INDEX\t\t0' in texts[DISPLAY / 'include/linux/sde_rsc.h'], 'RSC index changed')
    linkage = json.loads((PROVIDERS / 'scoped-linkage.json').read_text())
    for name, expected in linkage['modules'].items():
        path = PROVIDERS / 'modules' / name if name in ('pmic_class.ko', 's2dos05-regulator.ko') else DISPLAY.parent / 'union-modules-final' / name
        if name == 'i2c-gpio.ko':
            path = PROVIDERS / 'i2c-display-only/i2c-gpio.ko'
        require(identity(path) == expected, 'actual module identity differs: ' + name)
    require(linkage['modules']['i2c-gpio.ko']['sha256'] == '591962b082222ced903e7d8901bda637ff3a3c0dc3e156a89ee9c6253349f82a', 'reviewed bus scope differs')
    metadata = fixed.module_plan.load_metadata(ROOT / fixed.DEFAULT_METADATA)
    rows, rules, effective, core = fixed.audit_sources(
        texts[KERNEL / 'common/drivers/of/property.c'], texts[KERNEL / 'common/drivers/base/core.c'],
        texts[KERNEL / 'common/drivers/of/base.c'], texts[KERNEL / 'common/drivers/of/irq.c'],
        texts[KERNEL / 'msm-kernel/drivers/soc/qcom/rpmh-rsc.c'],
        texts[KERNEL / 'msm-kernel/drivers/regulator/rpmh-regulator.c'], config)
    require(set(effective) == set(rules), 'fw parser coverage differs')
    dtbo = (ROOT / fixed.DEFAULT_DTBO).read_bytes()
    vendor = (ROOT / fixed.DEFAULT_VENDOR_DTB).read_bytes()
    fixed.require_sha(dtbo, fixed.p225.INPUT_PINS[fixed.DEFAULT_DTBO], 'stock DTBO')
    fixed.require_sha(vendor, fixed.p225.INPUT_PINS[fixed.DEFAULT_VENDOR_DTB], 'stock vendor DTB')
    _, entries = fixed.stock_dt.parse_dt_table(dtbo)
    bases = [b for b in fixed.iter_fdt_blobs(vendor) if b.index in fixed.APPLICABLE_BASES]
    require(len(entries) == 11 and len(bases) == len(fixed.APPLICABLE_BASES), 'DT selection coverage differs')
    tool_inputs = {}
    for relative in (fixed.DEFAULT_FDTOVERLAY, fixed.DEFAULT_LIBFDT):
        path = (ROOT / relative).resolve()
        raw = fixed.stable_read(path, 'DT tool', 4 << 20)
        fixed.require_sha(raw, fixed.p225.INPUT_PINS[relative], 'DT tool pin')
        tool_inputs[str(path)] = fixed.receipt(raw)
    results = []
    with tempfile.TemporaryDirectory(prefix='display-closure-') as folder:
        folder = Path(folder)
        (folder / 'libfdt.so.1').symlink_to((ROOT / fixed.DEFAULT_LIBFDT).resolve())
        env = dict(os.environ, LD_LIBRARY_PATH=str(folder))
        for b in bases:
            fixed.require_sha(b.data, fixed.APPLICABLE_BASES[b.index][1], 'vendor base')
            (folder / 'base.dtb').write_bytes(b.data)
            for index, entry in enumerate(entries):
                overlay = fixed.stock_dt.entry_blob(dtbo, entry)
                (folder / 'overlay.dtb').write_bytes(overlay)
                subprocess.run([str(ROOT / fixed.DEFAULT_FDTOVERLAY), '-i', str(folder / 'base.dtb'),
                                '-o', str(folder / 'merged.dtb'), str(folder / 'overlay.dtb')],
                               env=env, check=True, capture_output=True, timeout=45)
                blob = (folder / 'merged.dtb').read_bytes()
                closure = derive(fixed.parse_tree(blob), rows, rules, metadata, config, texts, linkage['modules'])
                results.append(dict(base=b.index, overlay=index, merged=fixed.receipt(blob), closure=closure))
    inputs = {str(p.relative_to(ROOT)): fixed.receipt(text.encode()) for p, text in texts.items()}
    require(all(identity(ROOT / p) == v for p, v in inputs.items()), 'analyzed source changed')
    require(identity(Path(__file__)) == extractor, 'extractor changed while running')
    require(all(identity(p) == v for p, v in tool_inputs.items()), 'DT tool changed while running')
    out = dict(schema=SCHEMA, status='H0_STATIC_DERIVED_REVIEW_REQUIRED', runtime_qualified=False,
               device_contact=False, inputs=inputs, tool_inputs=tool_inputs,
               dtbo=fixed.receipt(dtbo), vendor_dtb=fixed.receipt(vendor), modules=linkage['modules'],
               image_config=identity(ROOT / fixed.DEFAULT_CONFIG), display_config=identity(vendor_config),
               metadata=metadata.metadata_hashes, fw_policy=core,
               extractor=extractor, results=results)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as stream:
        json.dump(out, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'status': out['status'], 'trees': len(results),
                      'node_counts': sorted({len(r['closure']['nodes']) for r in results})}))


if __name__ == '__main__':
    main()
