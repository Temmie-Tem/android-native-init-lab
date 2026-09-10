"""H0-only three-role journal prototype. No backend, registry or live dispatcher.

Inputs are simulated adapter facts, NOT live authority or transfer proof. Reuse
the ordinary F1 bounded immutable writer while keeping its live state machine
and consumed registry untouched. This prototype cannot qualify a device run.
"""
from pathlib import Path
import re

import device_action_f1_v2 as core

SCHEMA = 's22plus-native-roundtrip-h0-v1'
ROLES = ('native-install', 'native-restore', 'android-cleanup')


def sha(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('exact SHA256 required')
    return value


def binding(value):
    if type(value) is not dict or set(value) != {'schema', 'host_only', 'target', 'native', 'android'}:
        raise ValueError('H0 binding fields differ')
    if value['schema'] != SCHEMA or value['host_only'] is not True:
        raise ValueError('only H0 simulation is implemented')
    if value['target'] != 'SM-S906N/g0q/S906NKSS7FYG8':
        raise ValueError('target differs')
    for name in ('native', 'android'):
        item = value[name]
        if type(item) is not dict or set(item) != {'ap_sha256', 'ap_size', 'member_sha256', 'member_size'}:
            raise ValueError('artifact fields differ')
        sha(item['ap_sha256']); sha(item['member_sha256'])
        if any(type(item[key]) is not int or not 0 < item[key] <= 128*1024*1024
               for key in ('ap_size', 'member_size')):
            raise ValueError('artifact size differs')
    if (value['native']['ap_sha256'] == value['android']['ap_sha256']
            or value['native']['member_sha256'] == value['android']['member_sha256']):
        raise ValueError('independent Android fallback required')
    return value


def evaluate(plan, events):
    """Reopen from all durable events; absence never becomes transfer success."""
    binding(plan)
    if type(events) is not list or len(events) > 20:
        raise ValueError('bounded event list required')
    intents, results, health = {}, {}, {}
    download = None
    failed = closed = False
    for event in events:
        if closed or type(event) is not dict:
            raise ValueError('event after terminal or invalid event')
        kind = event.get('kind')
        fields = {
            'intent': {'kind', 'role', 'artifact'},
            'result': {'kind', 'role', 'outcome', 'receipt_sha256'},
            'native-health': {'kind', 'arrival', 'boot_sha256', 'nonce_sha256', 'receipt_sha256'},
            'failure': {'kind', 'receipt_sha256'},
            'download': {'kind', 'source', 'receipt_sha256'},
            'android-health': {'kind', 'receipt_sha256'},
        }
        if kind not in fields or set(event) != fields[kind]:
            raise ValueError('event schema differs')
        if 'receipt_sha256' in event:
            sha(event['receipt_sha256'])
        if kind == 'intent':
            role = event['role']
            if role not in ROLES or role in intents:
                raise ValueError('unknown role or consumed intent; no replay')
            artifact = plan['android' if role == 'android-cleanup' else 'native']
            if core.json_sha256(event['artifact']) != core.json_sha256(artifact):
                raise ValueError('exact role artifact differs')
            if role == 'native-install':
                if intents or failed or download is not None:
                    raise ValueError('installation is first and one-shot')
            elif role == 'native-restore':
                if (failed or results.get('native-install') != 'complete'
                        or 1 not in health or download != 'native-1'
                        or 'android-cleanup' in intents):
                    raise ValueError('native restoration requires proved first return')
            elif not intents or download is None:
                raise ValueError('Android cleanup requires exact Download after N intent')
            elif not failed and not (2 in health and download == 'native-2'):
                raise ValueError('normal cleanup requires second native departure')
            intents[role] = True
            download = None
        elif kind == 'result':
            role = event['role']
            if role not in intents or role in results or role != next(reversed(intents)):
                raise ValueError('transfer result has no current unmatched intent')
            if event['outcome'] not in ('complete', 'failed', 'uncertain'):
                raise ValueError('transfer outcome differs')
            results[role] = event['outcome']
            failed |= event['outcome'] != 'complete'
        elif kind == 'native-health':
            arrival = event['arrival']
            if type(arrival) is not int or arrival not in (1, 2) or arrival in health or failed:
                raise ValueError('native health arrival differs or research stopped')
            role = ROLES[arrival-1]
            if results.get(role) != 'complete' or role != next(reversed(intents)) or download is not None:
                raise ValueError('native health requires its completed transfer')
            sha(event['boot_sha256']); sha(event['nonce_sha256'])
            if arrival == 2 and (1 not in health or any(event[key] == health[1][key]
                                                       for key in ('boot_sha256', 'nonce_sha256'))):
                raise ValueError('fresh kernel boot and nonce required')
            health[arrival] = event
        elif kind == 'failure':
            if not intents or failed:
                raise ValueError('failure is a single research stop')
            failed = True
        elif kind == 'download':
            source = event['source']
            if download is not None or not intents or 'android-cleanup' in intents:
                raise ValueError('Download observation not expected')
            if source == 'physical':
                if not failed:
                    raise ValueError('physical fallback requires research stop')
            elif source not in ('native-1', 'native-2'):
                raise ValueError('unknown Download source')
            else:
                arrival = int(source[-1])
                if failed or arrival not in health or next(reversed(intents)) != ROLES[arrival-1]:
                    raise ValueError('Download requires current healthy native arrival')
            download = source
        elif kind == 'android-health':
            if results.get('android-cleanup') != 'complete':
                raise ValueError('final health requires completed Android transfer')
            closed = True
    return dict(schema=SCHEMA, host_only=True, live_authorized=False,
                transfer_intents=list(intents), transfer_results=results,
                first_native_health=1 in health, second_native_health=2 in health,
                research_stopped=failed, android_health=closed,
                outcome=('H0_SIMULATED_PASS' if closed and 2 in health and not failed
                         else 'H0_SIMULATED_NO_PROOF_RECOVERED' if closed
                         else 'H0_INCOMPLETE'))


class Transcript:
    """Private H0 fixture transcript with the actual 32 KiB F1 durable writer.

    There is intentionally no live session lease or device adapter here. A
    partial publication is a hard stop. A complete intent survives reopen and
    cannot be appended twice even if its result was never published.
    """
    def __init__(self, directory):
        self.directory = Path(directory)
        self.plan, _ = core.load_json(self.directory/'binding.json', 'H0 binding')
        binding(self.plan)

    @classmethod
    def create(cls, directory, plan):
        binding(plan)
        directory = Path(directory)
        directory.mkdir(mode=0o700, exist_ok=False)
        core._fsync_dir(directory.parent)
        core._write_exclusive(directory/'binding.json', plan)
        return cls(directory)

    def events(self):
        events = []
        previous = core.json_sha256(self.plan)
        entries = sorted(self.directory.iterdir())
        paths = [path for path in entries if path.name != 'binding.json']
        if len(paths) > 20:
            raise ValueError('H0 transcript bound exceeded')
        for index, path in enumerate(paths):
            if path.name != f'{index:04d}.json':
                raise ValueError('unexpected H0 transcript entry')
            record, _ = core.load_json(path, 'H0 event')
            if (set(record) != {'previous_sha256', 'event'}
                    or record['previous_sha256'] != previous):
                raise ValueError('H0 transcript chain differs')
            events.append(record['event'])
            previous = core.json_sha256(record)
        evaluate(self.plan, events)
        return events, previous

    def append(self, event):
        events, previous = self.events()
        result = evaluate(self.plan, events + [event])
        core._write_exclusive(self.directory/f'{len(events):04d}.json',
                              dict(previous_sha256=previous, event=event))
        return result

    def result(self):
        return evaluate(self.plan, self.events()[0])
