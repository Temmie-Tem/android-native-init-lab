"""One returned operator approval for a fixed, finite series of attended mainline steps.

A series record names its steps before approval: mainline tasks by their exact
qualified image, and fixed Android block reads by the mainline step they follow.
One exact returned approval of the series covers every step. Each step still
needs its own prepared task or read, fresh readiness and attendance, and starts
only after every earlier step closed healthy with an admitted outcome. A step is
claimed once (no-replay) before it opens; a claimed step is never repeated.
The series ends at its expiry, at a host reboot, or at the first step whose
outcome is not admitted. It grants no step type, image or outcome it does not
name, and no recovery, retry or replay beyond the single-step rules.

Every mainline step names a distinct qualified UFS storage image of report V17
or later (a distinct candidate and AP: a consumed AP is never reused). A READBACK
mismatch or foreign content is not an admitted outcome, so it ends the series.
"""
from pathlib import Path
import re

from s22plus_native_records_v3 import clock, host_boot, pin, private_path, publish, read, require, verify

SCHEMA = 's22plus-mainline-series-v1'
APPROVAL_SCHEMA = 's22plus-mainline-series-approval-v1'
CLAIM_SCHEMA = 's22plus-mainline-series-claim-v1'
KINDS = ('mainline', 'android-block')
MAX_STEPS = 4
MAX_SECONDS = 86400
CONTINUE_STATUS = ('PASS_MAINLINE_UFS_LINK',)
CONTINUE_WRITE = ('WRITTEN', 'ALREADY_PRESENT')
# Outcomes after which no further V17 run starts, in or outside a series, until a
# reviewed change and a new single-run approval.
STOP_WRITE = ('READBACK_MISMATCH', 'FOREIGN_CONTENT')
NAME = re.compile(r's22plus-[a-z0-9-]+-series-h0-[0-9]{8}-[0-9]+')


def approval_text(series, receipt):
    return (f"APPROVE S22PLUS MAINLINE SERIES V1 {receipt['sha256']} "
            f"{len(series['steps'])}steps {series['seconds']}s attended")


def directory(root, series_pin):
    path = private_path(root, Path(series_pin['path']))
    base = path.parent
    require(path.name == 'series.json' and base.parent == Path(root) / 'workspace/private/outputs' and
            NAME.fullmatch(base.name), 'not a direct S22+ series directory')
    return base


def write_image(image):
    """A UFS storage image whose capability fixes report V17 or later (the write stage)."""
    import s22plus_mainline_task_v1 as mainline
    return mainline.ufs_write(image)


def qualified(image_pin):
    """A mainline series image: a UFS storage capability of report V17 or later."""
    image = read(verify(image_pin))
    return image if write_image(image) else None


def validate(root, series_pin, *, images=True):
    """The series record. `images` also qualifies every named image; a step's own
    recovery skips that, so later images never block it."""
    series = read(verify(series_pin))
    base = directory(root, series_pin)
    require(set(series) == {'schema', 'steps', 'seconds', 'first_preceding_closed', 'host_boot',
                            'created_ns', 'expires_ns', 'attended', 'grants_device_authority'} and
            series['schema'] == SCHEMA and series['attended'] is True and
            series['grants_device_authority'] is False and
            type(series['seconds']) is int and 0 < series['seconds'] <= 3600 and
            type(series['created_ns']) is int and type(series['expires_ns']) is int and
            0 < series['expires_ns'] - series['created_ns'] <= MAX_SECONDS * 1_000_000_000 and
            type(series['steps']) is list and 1 <= len(series['steps']) <= MAX_STEPS, 'series record differs')
    mainline = []
    for index, step in enumerate(series['steps']):
        require(type(step) is dict and step.get('kind') in KINDS, 'unselected series step kind')
        if step['kind'] == 'mainline':
            require(set(step) == {'kind', 'image'}, 'mainline series step differs')
            private_path(root, Path(step['image']['path']), exists=images)
            mainline.append(index)
        else:
            # A block read follows the named mainline step directly.
            require(set(step) == {'kind', 'of_step'} and type(step['of_step']) is int and
                    step['of_step'] == index - 1 and step['of_step'] in mainline, 'Android block step differs')
    require(mainline and mainline[0] == 0, 'a series starts with a mainline step')
    private_path(root, Path(series['first_preceding_closed']['path']))
    if images:
        values = [qualified(series['steps'][i]['image']) for i in mainline]
        require(all(values), 'a series mainline image is not a V17 UFS storage image')
        for field in ('candidate', 'ap'):
            require(len({v[field]['sha256'] for v in values}) == len(values),
                    'series mainline steps reuse a candidate or AP')
    return series, base


def approved(root, series_pin):
    """The one exact returned operator approval of this series."""
    series, base = validate(root, series_pin)
    value = read(verify(pin(base / 'operator-approval.json')))
    require(set(value) == {'schema', 'series', 'approval', 'actual_user_text', 'attended'} and
            value['schema'] == APPROVAL_SCHEMA and value['series'] == series_pin and
            value['approval'] == approval_text(series, series_pin) and value['attended'] is True and
            type(value['actual_user_text']) is str and value['actual_user_text'].strip() == value['approval'],
            'actual returned series approval is absent or differs')
    require(host_boot() == series['host_boot'] and series['created_ns'] <= clock() < series['expires_ns'],
            'series expired or belongs to another host boot')
    return series, base, value


def claim_path(base, index):
    return base / f'step-{index}.json'


def block_path(base, index):
    """The one output directory of the series' Android block read at `index`."""
    return base / f'block-{index}'


def write_outcome(terminal):
    """The V17 write outcome a mainline Android terminal recorded, or None."""
    result = terminal.get('mainline', {}).get('ufs_evidence', {}).get('result', {}) if type(terminal) is dict else None
    storage = result.get('storage') if type(result) is dict else None
    write = storage.get('write') if type(storage) is dict else None
    return write.get('outcome') if type(write) is dict else None


def final_health(terminal):
    """The final rooted Android health a mainline terminal's result proved."""
    return read(verify(read(verify(terminal['terminal_result']))['health']))


def lane_stopped(root):
    """The first closed mainline run whose V17 write stopped on a mismatch or foreign
    content, or None. Any such closure stops every later V17 run, whichever closure a
    task names as its predecessor."""
    outputs = Path(root) / 'workspace/private/outputs'
    # A V17 grant opens only for a task at outputs/<run>/task-1, so every V17
    # closure is found here; series block reads live at <series>/block-<step>.
    for path in sorted(outputs.glob('*/task-*/closed.json')):
        closed = read(path)
        terminal = closed.get('current_android_terminal') if type(closed) is dict else None
        if type(terminal) is dict and type(terminal.get('path')) is str and Path(terminal['path']).is_file():
            if write_outcome(read(Path(terminal['path']))) in STOP_WRITE:
                return str(path)
    for path in sorted([*outputs.glob('*-series-h0-*/block-*/terminal.json'),
                        *outputs.glob('*-series-h0-*/block-*/stopped.json')]):
        block = read(path).get('block')
        if type(block) is dict and block.get('status') == 'OTHER':
            return str(path)
    return None


def _mainline_outcome(root, closed_path, subject):
    """An earlier mainline step's closure: its claimed task's own grant, operation,
    terminal and final health, admitted only with a continuing outcome."""
    closed = read(verify(pin(closed_path)))
    folder = closed_path.parent
    require(closed_path.name == 'closed.json' and closed['task'] == subject and
            closed['grant']['path'] == str(folder / 'grant.json') and read(verify(closed['grant']))['task'] == subject,
            'earlier series closure is not its claimed task')
    terminal_pin = closed['current_android_terminal']
    terminal = read(verify(terminal_pin))
    require(Path(terminal_pin['path']).parent.parent == folder and
            Path(closed['operation']['path']).parent == Path(terminal_pin['path']).parent and
            terminal['grant'] == closed['grant'], 'earlier series terminal is not its claimed operation')
    require(closed['terminal_state'] == terminal['terminal_state'] == 'ANDROID_CLOSED_HEALTHY' and
            terminal['research_closed'] is True and closed['scientific_status'] in CONTINUE_STATUS,
            'earlier series step did not close with a continuing outcome')
    operation = Path(terminal_pin['path']).parent
    final = read(verify(terminal['terminal_result']))
    require(Path(terminal['terminal_result']['path']).parent == operation and
            Path(final['health']['path']).is_relative_to(operation),
            'earlier series final health is not its claimed operation')
    final_health(terminal)
    outcome = write_outcome(terminal)
    require(outcome in CONTINUE_WRITE, 'earlier series step has no admitted write outcome')
    return closed, outcome


def claimed_for(root, claim_receipt, task_pin, statement, task):
    """A grant under a series approval: only for the task its series claimed (after
    the claim's own ordering checks), for that step's exact image, with the claim's
    own approval text."""
    require(claim_receipt is not None, 'a series approval opens a grant only through its series claim')
    value = read(verify(claim_receipt))
    series, base = validate(root, value['series'], images=False)
    step = series['steps'][value['step']] if type(value['step']) is int and 0 <= value['step'] < len(series['steps']) else {}
    require(value['schema'] == CLAIM_SCHEMA and Path(claim_receipt['path']) == claim_path(base, value['step']) and
            value['subject'] == task_pin and value['actual_user_text'] == statement and
            step.get('kind') == 'mainline' and task['N'] == read(verify(step['image'])) and
            task['seconds'] == series['seconds'], 'series claim does not name this task and approval')
    # The claim was made before expiry on the series' host boot (its own record), and
    # the grant opens on that same host boot; expiry is never re-decided here.
    require(value['host_boot'] == series['host_boot'] == host_boot() and type(value['claimed_ns']) is int and
            series['created_ns'] <= value['claimed_ns'] < series['expires_ns'],
            'series claim was not made inside the series')
    return value


def taken(root, series_pin, index, subject):
    """A step already claimed by this exact subject (its own resume or recovery)."""
    path = claim_path(directory(root, series_pin), index)
    if not path.exists():
        return False
    value = read(path)
    require(value['schema'] == CLAIM_SCHEMA and value['series'] == series_pin and value['step'] == index and
            value['subject'] == subject, 'series step was claimed by another subject; no replay')
    return value


def _earlier_admitted(root, series, base, series_pin, index):
    """Every step before `index` was claimed and closed healthy, by its own claimed
    subject, with an admitted outcome."""
    for earlier in range(index):
        require(claim_path(base, earlier).exists(), 'an earlier series step was not taken')
        claim = read(claim_path(base, earlier))
        require(claim['schema'] == CLAIM_SCHEMA and claim['series'] == series_pin and claim['step'] == earlier,
                'earlier series claim differs')
        require((Path(claim['closed']['path']).exists() if claim['closed'] else False),
                'earlier series step is not closed')
        closed_path = Path(claim['closed']['path'])
        if series['steps'][earlier]['kind'] == 'mainline':
            _mainline_outcome(root, closed_path, claim['subject'])
        else:
            result = read(verify(pin(closed_path)))
            require(claim['subject'] == dict(output=str(closed_path.parent)) and closed_path.name == 'terminal.json' and
                    closed_path.parent == block_path(base, earlier) and
                    result['series'] == series_pin and result['step'] == earlier,
                    'earlier Android block result is not its claimed read')
            require(result['terminal_state'] == 'ANDROID_CLOSED_HEALTHY' and result['block']['status'] == 'PATTERN',
                    'earlier Android block read did not find the pattern')


def bind_step(root, series_pin, index, *, kind, task=None, task_pin=None, preceding_closed=None):
    """Check that step `index` may start now; returns the series and its approval.

    A step this subject already claimed is its own resume or recovery: it stays bound
    to the same approval its claim recorded; expiry, later steps or images and the
    approval file never block its recovery. A step claimed before expiry runs to its
    own close under the single-step rules; no step is claimed at or after expiry."""
    own = taken(root, series_pin, index, task_pin) if type(index) is int and index >= 0 else False
    if own:
        series, base = validate(root, series_pin, images=False)
        require(series['steps'][index]['kind'] == kind and own['approval'] == approval_text(series, series_pin),
                'claimed series step differs')
        return series, base, dict(approval=own['approval'], actual_user_text=own['actual_user_text'])
    series, base, value = approved(root, series_pin)
    require(type(index) is int and 0 <= index < len(series['steps']) and
            series['steps'][index]['kind'] == kind, 'series step selection differs')
    _earlier_admitted(root, series, base, series_pin, index)
    step = series['steps'][index]
    if kind == 'mainline':
        require(task is not None and task['N'] == read(verify(step['image'])) and
                task['seconds'] == series['seconds'], 'mainline task differs from its series step')
        earlier = [i for i in range(index) if series['steps'][i]['kind'] == 'mainline']
        expected = (series['first_preceding_closed'] if not earlier else
                    pin(Path(read(claim_path(base, earlier[-1]))['closed']['path'])))
        require(preceding_closed == expected, 'series step does not follow its preceding closure')
    return series, base, value


def claim(root, series_pin, index, *, subject, closed_path):
    """Consume step `index` once, before it opens; never released.

    Expiry is decided here, once: the claim records the boot-clock time and host boot
    at which it was made, inside the approved series, and that record (not the time
    its file became durable, nor when a grant later opens) is what the grant gate
    checks. A claimed step then runs and recovers under the single-step rules."""
    series, base, value = approved(root, series_pin)
    require(type(index) is int and 0 <= index < len(series['steps']), 'series step selection differs')
    # The claim itself re-establishes the step's order, never only bind_step().
    _earlier_admitted(root, series, base, series_pin, index)
    now = clock()
    require(host_boot() == series['host_boot'] and series['created_ns'] <= now < series['expires_ns'],
            'series expired or belongs to another host boot')
    return publish(claim_path(base, index), dict(schema=CLAIM_SCHEMA, series=series_pin, step=index,
        subject=subject, closed=dict(path=str(closed_path)), approval=value['approval'],
        actual_user_text=value['actual_user_text'], approval_record=pin(base / 'operator-approval.json'),
        claimed_ns=now, host_boot=series['host_boot']))


def create(root, output, steps, *, seconds, first_preceding_closed, lifetime_seconds=86400):
    """H0: write a series record for approval; grants nothing by itself."""
    output = private_path(root, output, exists=False)
    require(not output.exists() and NAME.fullmatch(output.name), 'fresh series directory required')
    require(0 < lifetime_seconds <= MAX_SECONDS, 'series lifetime differs')
    output.mkdir(mode=0o700)
    now = clock()
    receipt = publish(output / 'series.json', dict(schema=SCHEMA, steps=steps, seconds=seconds,
        first_preceding_closed=first_preceding_closed, host_boot=host_boot(), created_ns=now,
        expires_ns=now + lifetime_seconds * 1_000_000_000, attended=True, grants_device_authority=False))
    validate(root, receipt)
    return receipt
