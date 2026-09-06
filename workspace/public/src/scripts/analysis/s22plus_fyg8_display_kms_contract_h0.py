"""Source-informed nominal FYG8 mode producer; never claims runtime acceptance."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import s22plus_fyg8_display_executability_h0 as prerequisite
ROOT = prerequisite.ROOT
FIXTURE = ROOT / 'tests/fixtures/s22plus-display-kms-source-v3.json'
SELECTED = dict(clock=484051, hdisplay=1080, hsync_start=1172, hsync_end=1264, htotal=1356, hskew=0, vdisplay=2340, vsync_start=11730, vsync_end=11814, vtotal=11899, vscan=0, vrefresh=30, flags=0, name='1080x2340x30xcmdHS')

def nominal_modes(tree):
    """Model the reviewed cmd-panel conversion; type/preference is not selection."""
    fixed = prerequisite.fixed
    panel = tree.nodes[prerequisite.PANEL]
    if not prerequisite.strings(panel, 'qcom,mdss-dsi-panel-type') == ('dsi_cmd_mode',):
        raise ValueError('source-informed KMS contract differs')
    if not fixed._cells(panel.properties['qcom,dsi-ctrl-num'], 'controller count') == (0,):
        raise ValueError('source-informed KMS contract differs')
    prefix = prerequisite.PANEL + '/qcom,mdss-dsi-display-timings/'
    modes = []
    for path, node in sorted(tree.nodes.items()):
        if not path.startswith(prefix) or '/' in path[len(prefix):]:
            continue

        def cell(key):
            values = fixed._cells(node.properties['qcom,mdss-dsi-' + key], key)
            if not len(values) == 1:
                raise ValueError('source-informed KMS contract differs')
            return values[0]
        m = dict(hdisplay=cell('panel-width'), vdisplay=cell('panel-height'), vrefresh=cell('panel-framerate'), hskew=cell('h-sync-skew'), vscan=0, flags=0)
        m['hsync_start'] = m['hdisplay'] + cell('h-front-porch')
        m['hsync_end'] = m['hsync_start'] + cell('h-pulse-width')
        m['htotal'] = m['hsync_end'] + cell('h-back-porch')
        m['vsync_start'] = m['vdisplay'] + cell('v-front-porch')
        m['vsync_end'] = m['vsync_start'] + cell('v-pulse-width')
        m['vtotal'] = m['vsync_end'] + cell('v-back-porch')
        m['clock'] = m['htotal'] * m['vtotal'] * m['vrefresh'] // 1000
        hs = 'samsung,mdss-dsi-sot-hs-mode' in node.properties
        phs = 'samsung,mdss-dsi-phs-mode' in node.properties
        suffix = ('PHS' if phs else 'HS') if hs else 'NS'
        m['name'] = f"{m['hdisplay']}x{m['vdisplay']}x{m['vrefresh']}xcmd{suffix}"
        modes.append(m)
    if not modes.count(SELECTED) == 1:
        raise ValueError('exact 30HS nominal mode absent or duplicated')
    return modes

def derive():
    fixed = prerequisite.fixed
    producer_bytes = Path(__file__).read_bytes()
    fixture_bytes = FIXTURE.read_bytes()
    inputs = json.loads(fixture_bytes)['inputs']
    texts = {}
    for path, expected in inputs.items():
        raw = (ROOT / path).read_bytes()
        if not fixed.receipt(raw) == expected:
            raise ValueError('KMS source changed: ' + path)
        texts[path] = raw.decode()
    driver = texts[str((prerequisite.DISPLAY / 'msm/msm_drv.c').relative_to(ROOT))]
    body = driver.split('static struct drm_driver msm_driver = {', 1)[1].split('\n};', 1)[0]
    name = re.findall('\\.name\\s*=\\s*"([a-z_]+)"', body)
    if not name == ['msm_drm']:
        raise ValueError('source-informed KMS contract differs')
    dtbo = (ROOT / fixed.DEFAULT_DTBO).read_bytes()
    vendor = (ROOT / fixed.DEFAULT_VENDOR_DTB).read_bytes()
    for relative, raw in ((fixed.DEFAULT_DTBO, dtbo), (fixed.DEFAULT_VENDOR_DTB, vendor)):
        fixed.require_sha(raw, fixed.p225.INPUT_PINS[relative], 'stock DT')
    _, entries = fixed.stock_dt.parse_dt_table(dtbo)
    bases = [b for b in fixed.iter_fdt_blobs(vendor) if b.index in fixed.APPLICABLE_BASES]
    tools = {}
    for relative in (fixed.DEFAULT_FDTOVERLAY, fixed.DEFAULT_LIBFDT):
        raw = (ROOT / relative).read_bytes()
        fixed.require_sha(raw, fixed.p225.INPUT_PINS[relative], 'DT tool')
        tools[str(relative)] = fixed.receipt(raw)
    retained = ROOT / 'workspace/private/outputs/s22plus_fyg8_p351/h0-work/executability-final.json'
    raw = retained.read_bytes()
    if hashlib.sha256(raw).hexdigest() != '40eaaf46a7dbb2293cf647a3962f71e528dd2a9bfce207ebecc5e6d455bc0d8a':
        raise ValueError('reviewed prerequisite merge identities changed')
    expected = {(row['base'], row['overlay']): row['merged'] for row in json.loads(raw)['results']}
    cache = ROOT / 'workspace/private/outputs/s22plus_fyg8_p352/h0-work/kms-merged'
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    results = []
    with tempfile.TemporaryDirectory(prefix='display-kms-') as temporary:
        folder = Path(temporary)
        (folder / 'libfdt.so.1').symlink_to((ROOT / fixed.DEFAULT_LIBFDT).resolve())
        for base in bases:
            fixed.require_sha(base.data, fixed.APPLICABLE_BASES[base.index][1], 'base DT')
            (folder / 'base.dtb').write_bytes(base.data)
            for index, entry in enumerate(entries):
                (folder / 'overlay.dtb').write_bytes(fixed.stock_dt.entry_blob(dtbo, entry))
                cached = cache / f'{base.index}-{index}.dtb'
                if cached.exists():
                    blob = cached.read_bytes()
                else:
                    subprocess.run([str(ROOT / fixed.DEFAULT_FDTOVERLAY), '-i', str(folder / 'base.dtb'), '-o', str(folder / 'merged.dtb'), str(folder / 'overlay.dtb')], env=dict(os.environ, LD_LIBRARY_PATH=str(folder)), check=True, capture_output=True, timeout=45)
                    blob = (folder / 'merged.dtb').read_bytes()
                if fixed.receipt(blob) != expected[(base.index, index)]:
                    raise ValueError('stock merged DT identity differs')
                if not cached.exists():
                    with cached.open('xb') as stream:
                        stream.write(blob)
                    cached.chmod(0o400)
                results.append(dict(base=base.index, overlay=index, merged=fixed.receipt(blob), modes=nominal_modes(fixed.parse_tree(blob))))
    if not len(results) == 22:
        raise ValueError('source-informed KMS contract differs')
    for path, expected_input in {**inputs, **tools}.items():
        if fixed.receipt((ROOT / path).read_bytes()) != expected_input:
            raise ValueError('KMS source/tool changed during derivation')
    if Path(__file__).read_bytes() != producer_bytes or FIXTURE.read_bytes() != fixture_bytes:
        raise ValueError('KMS producer/fixture changed during derivation')
    for relative in (fixed.DEFAULT_DTBO, fixed.DEFAULT_VENDOR_DTB):
        fixed.require_sha((ROOT / relative).read_bytes(), fixed.p225.INPUT_PINS[relative], 'stock DT after derivation')
    if hashlib.sha256(retained.read_bytes()).hexdigest() != '40eaaf46a7dbb2293cf647a3962f71e528dd2a9bfce207ebecc5e6d455bc0d8a':
        raise ValueError('prerequisite receipt changed during derivation')
    return dict(driver_name=name[0], selected=SELECTED, results=results, inputs=inputs, tools=tools, fixture=fixed.receipt(fixture_bytes), extractor=fixed.receipt(producer_bytes), runtime_accepted_modes='UNPROVED', device_contact=False)
if __name__ == '__main__':
    print(json.dumps(derive(), indent=2, sort_keys=True))
