"""Priority-placed early/TLMM observations; static occurrence, not a boot trace."""
import hmac
from pathlib import Path
import re
import struct

try:
    from . import retained_probe as v9
except ImportError:
    import retained_probe as v9

BASE, REGION, SLOT, MAX_SLOTS = v9.BASE, v9.REGION, v9.SLOT, v9.MAX_SLOTS
MAGIC = b'S22PRBA!'
DOMAIN = b'S22PLUS-MAINLINE-DEFERRED-PROBE-V10\0'
SCHEMA = 's22plus-mainline-retained-deferred-probe-v10'
HERE = Path(__file__).resolve().parent
require, catalog = v9.require, v9.catalog
TLMM_PATH = '/soc@0/pinctrl@f100000'
FIXED = ('post-early-ioremap-init', 'post-setup-arch', 'kernel-init-freeable-enter') + v9.FIXED
TLMM_POINTS = (
    'probe-enter', 'post-resource-maps', 'pre-irq-lookup', 'post-irq-lookup',
    'pre-pinctrl-register', 'post-pinctrl-register',
    'post-pinfunctions-pre-pinctrl-enable', 'post-pinctrl-enable', 'gpio-enter',
    'post-wakeup-parent-branch', 'pre-gpiochip-add', 'post-gpiochip-add',
    'post-gpio-ranges-branch', 'post-gpio-init',
    'probe-return-zero', 'probe-return-defer', 'probe-return-other')
TLMM_GROUPS = ('pre-deferred-arm', 'phase-1', 'phase-2')
SPARSE_BASE = len(FIXED) + len(TLMM_POINTS) * len(TLMM_GROUPS)


def constant(name, prefix='S22_EV_'):
    return prefix + name.replace('-', '_').upper()


def stages(count, ordinals, paths):
    old = v9.stages(count, ordinals, paths)
    require(TLMM_PATH in paths, 'V10 requires its exact TLMM catalog entry')
    names = list(FIXED)
    names += [f'tlmm-{group}:{point}' for group in TLMM_GROUPS for point in TLMM_POINTS]
    names += list(old.values())[len(v9.FIXED):]
    require(len(names) <= MAX_SLOTS and len(names) == len(set(names)),
            'V10 event catalog exceeds finite capacity')
    return dict(enumerate(names))


def configuration(candidate, key, count, ordinals, paths):
    require(type(candidate) is str and re.fullmatch('[0-9a-f]{64}', candidate) and
            type(key) is bytes and len(key) == 32, 'probe candidate/key differs')
    names = stages(count, ordinals, paths)
    frames = {}
    for event in names:
        prefix = (MAGIC + struct.pack('<II', 10, event) + bytes.fromhex(candidate) +
                  struct.pack('<III', len(names), len(paths), count) + bytes(36))
        frames[str(event)] = (prefix + hmac.digest(key, DOMAIN + prefix, 'sha256')).hex()
    return dict(schema=SCHEMA, candidate_id=candidate, base=BASE, region_size=REGION,
                slot_size=SLOT, span=len(names) * SLOT, initcall_count=count,
                initcall_ordinals=ordinals, node_paths=paths, frames=frames)


def validate(config, candidate, key):
    require(config == configuration(candidate, key, config.get('initcall_count'),
                                    config.get('initcall_ordinals'), config.get('node_paths')),
            'V10 retained probe configuration differs')
    return config


def render(config):
    names = stages(config['initcall_count'], config['initcall_ordinals'], config['node_paths'])
    require(config['span'] == len(names) * SLOT and config['slot_size'] == SLOT and
            config['base'] == BASE and config['region_size'] == REGION and
            set(config['frames']) == {str(i) for i in names}, 'V10 probe write scope differs')
    rows = []
    for i in names:
        frame = bytes.fromhex(config['frames'][str(i)])
        require(len(frame) == SLOT, 'probe frame size differs')
        rows.append('\t{' + ','.join(str(v) for v in frame) + '},')
    replacements = {
        '@COUNT@': str(config['initcall_count']), '@SLOTS@': str(len(names)),
        '@NODES_COUNT@': str(len(config['node_paths'])),
        '@TLMM_NODE@': str(config['node_paths'].index(TLMM_PATH)),
        '@FIXED_COUNT@': str(len(FIXED)), '@TLMM_POINTS@': str(len(TLMM_POINTS)),
        '@TLMM_GROUPS@': str(len(TLMM_GROUPS)),
        '@EVENT_CONSTANTS@': '\n'.join(f'#define {constant(n)} {i}U' for i, n in enumerate(FIXED)),
        '@TLMM_CONSTANTS@': '\n'.join(f'#define {constant(n, "S22_TLMM_")} {i}U'
                                     for i, n in enumerate(TLMM_POINTS)),
        '@ORDINAL_COUNT@': str(len(config['initcall_ordinals'])),
        '@ORDINALS@': ','.join(str(i) for i in config['initcall_ordinals']),
        '@PATHS@': '\n'.join('\t"' + p + '",' for p in config['node_paths']),
        '@FRAMES@': '\n'.join(rows)}
    result = (HERE / 'retained-probe-v10-c.h').read_text()
    for key, value in replacements.items():
        result = result.replace(key, value)
    return result


def instrument_setup(old):
    declaration = 'void __init __no_sanitize_address setup_arch(char **cmdline_p)\n'
    anchor = '\tearly_ioremap_init();\n'
    require('s22_retained_' not in old and old.count(declaration) == old.count(anchor) == 1,
            'V10 early setup anchor differs')
    return old.replace(declaration, 'extern void __init s22_retained_probe_mark(u32 event);\n\n' +
                       declaration).replace(anchor, anchor + '\ts22_retained_probe_mark(0);\n')


def instrument_main(old, config):
    stages(config['initcall_count'], config['initcall_ordinals'], config['node_paths'])
    result = v9.instrument_main(old, config)
    result = re.sub(r's22_retained_probe_mark\(([0-5])\);',
                    lambda m: f's22_retained_probe_mark({len(FIXED) - len(v9.FIXED) + int(m[1])});', result)
    # start_kernel precedes V9's declaration site at do_initcall_level.
    result = result.replace('extern void __init s22_retained_probe_mark(u32 event);\n', '')
    declaration = ('asmlinkage __visible __init __no_sanitize_address __noreturn __no_stack_protector\n'
                   'void start_kernel(void)\n')
    require(old.count(declaration) == 1 and old.count('\tsetup_arch(&command_line);\n') == 1,
            'V10 post-setup anchor differs')
    result = result.replace(declaration, 'extern void __init s22_retained_probe_mark(u32 event);\n\n' + declaration)
    result = result.replace('\tsetup_arch(&command_line);\n',
                            '\tsetup_arch(&command_line);\n\ts22_retained_probe_mark(1);\n')
    anchor = 'static noinline void __init kernel_init_freeable(void)\n{\n'
    require(old.count(anchor) == 1, 'V10 kernel-init entry anchor differs')
    return result.replace(anchor, anchor + '\ts22_retained_probe_mark(2);\n')


def instrument_dd(old):
    result = v9.instrument_dd(old)
    for event in range(7, 15):
        result = result.replace(f's22_probe_hook(S22_FIXED, NULL, {event})',
                                f's22_probe_hook(S22_FIXED, NULL, {constant(v9.FIXED[event])})')
    return result


def instrument_tlmm(old):
    """Retain original branches and early returns inside a token-scoped body."""
    require('s22_retained_' not in old, 'TLMM source is already instrumented')
    gpio_start = 'static int msm_gpio_init(struct msm_pinctrl *pctrl)\n{\n'
    probe_start = ('int msm_pinctrl_probe(struct platform_device *pdev,\n'
                   '\t\t      const struct msm_pinctrl_soc_data *soc_data)\n{\n')
    export = 'EXPORT_SYMBOL(msm_pinctrl_probe);'
    require(old.count(gpio_start) == old.count(probe_start) == old.count(export) == 1,
            'TLMM function boundaries differ')
    prefix, remainder = old.split(gpio_start)
    gpio, remainder = remainder.split('\nstatic int msm_ps_hold_restart', 1)
    between, probe = remainder.split(probe_start)
    body, suffix = probe.split(export)

    def replace_once(text, before, after):
        require(text.count(before) == 1, 'TLMM structural anchor differs: ' + before[:64])
        return text.replace(before, after)

    def mark(point):
        return f'\ts22_retained_probe_tlmm_point(s22_token, {TLMM_POINTS.index(point)});\n'

    gpio = replace_once(gpio, '\tbool skip;\n', '\tbool skip;\n\n' + mark('gpio-enter'))
    gpio = replace_once(gpio, '\tgirq = &chip->irq;\n', mark('post-wakeup-parent-branch') + '\tgirq = &chip->irq;\n')
    anchor = '\tret = devm_gpiochip_add_data(pctrl->dev, &pctrl->chip, pctrl);\n'
    gpio = replace_once(gpio, anchor, mark('pre-gpiochip-add') + anchor + mark('post-gpiochip-add'))
    gpio = replace_once(gpio, '\treturn 0;\n}', mark('post-gpio-ranges-branch') + '\treturn 0;\n}')
    body = replace_once(body, '\tmsm_pinctrl_setup_pm_reset(pctrl);\n',
                        mark('post-resource-maps') + '\tmsm_pinctrl_setup_pm_reset(pctrl);\n')
    anchor = '\tpctrl->irq = platform_get_irq(pdev, 0);\n'
    body = replace_once(body, anchor, mark('pre-irq-lookup') + anchor + mark('post-irq-lookup'))
    anchor = ('\tret = devm_pinctrl_register_and_init(&pdev->dev, &pctrl->desc,\n'
              '\t\t\t\t\t     pctrl, &pctrl->pctrl);\n')
    body = replace_once(body, anchor, mark('pre-pinctrl-register') + anchor + mark('post-pinctrl-register'))
    anchor = '\tret = pinctrl_enable(pctrl->pctrl);\n'
    body = replace_once(body, anchor, mark('post-pinfunctions-pre-pinctrl-enable') + anchor + mark('post-pinctrl-enable'))
    anchor = '\tret = msm_gpio_init(pctrl);\n'
    body = replace_once(body, anchor,
                        '\tret = msm_gpio_init(pctrl, s22_token);\n' + mark('post-gpio-init'))
    declarations = ('extern u32 s22_retained_probe_tlmm_begin(struct device *dev);\n'
                    'extern void s22_retained_probe_tlmm_point(u32 token, u32 point);\n\n')
    wrapper = (probe_start +
               '\tu32 s22_token = s22_retained_probe_tlmm_begin(&pdev->dev);\n'
               '\tint ret = s22_msm_pinctrl_probe(pdev, soc_data, s22_token);\n\n'
               '\ts22_retained_probe_tlmm_point(s22_token,\n'
               f'\t\tret == 0 ? {TLMM_POINTS.index("probe-return-zero")} : '
               f'ret == -EPROBE_DEFER ? {TLMM_POINTS.index("probe-return-defer")} : '
               f'{TLMM_POINTS.index("probe-return-other")});\n'
               '\treturn ret;\n}\n')
    inner = ('static noinline int s22_msm_pinctrl_probe(struct platform_device *pdev,\n'
             '\t\tconst struct msm_pinctrl_soc_data *soc_data, u32 s22_token)\n{\n')
    return (prefix + declarations +
            'static int msm_gpio_init(struct msm_pinctrl *pctrl, u32 s22_token)\n{\n' + gpio +
            '\nstatic int msm_ps_hold_restart' + between + inner + body + wrapper + export + suffix)


def decode(data, candidate, key, config):
    require(type(data) is bytes and len(data) <= 4 * 1024 * 1024, 'retained capture exceeds bound')
    validate(config, candidate, key)
    names = stages(config['initcall_count'], config['initcall_ordinals'], config['node_paths'])
    expected = {e: bytes.fromhex(config['frames'][str(e)]) for e in names}
    found = {}; damaged = foreign = offset = 0
    while True:
        offset = data.find(MAGIC, offset)
        if offset < 0:
            break
        piece = data[offset:offset + SLOT]
        if len(piece) != SLOT:
            damaged += 1
        elif piece[16:48] != bytes.fromhex(candidate):
            foreign += 1
        else:
            version, event = struct.unpack_from('<II', piece, 8)
            if version != 10 or event not in names or not hmac.compare_digest(piece, expected[event]):
                damaged += 1
            else:
                found.setdefault(event, []).append(offset)
        offset += len(MAGIC)
    events = [dict(event=e, stage=names[e], offsets=o) for e, o in sorted(found.items())]
    return dict(schema='s22plus-mainline-retained-deferred-probe-result-v10',
                status='RETAINED_STAGE_OBSERVED' if events else 'NO_PROOF', events=events,
                record_count=sum(map(len, found.values())), observed_stages=[v['stage'] for v in events],
                damaged_candidates=damaged, foreign_candidates=foreign,
                initcall_count=config['initcall_count'], node_count=len(config['node_paths']),
                occurrence_scope='AT_LEAST_ONCE_IN_CANDIDATE_ATTEMPTS',
                phase_scope='PHASE_SAMPLED_AT_ENTRY_NOT_TRIGGER_PROVENANCE',
                same_boot_pair_proved=False, same_callback_pair_proved=False,
                unique_device_or_driver_proved=False, complete_retry_history=False,
                last_attempt_proved=False, stopped_at_last_record=False, reset_cause_proved=False,
                gpio_reservation_causality_proved=False, physical_retention_coverage_proved=False,
                callback_success_proved=False, mainline_pid1=False,
                authenticated_usb=False, replay_authorized=False)
