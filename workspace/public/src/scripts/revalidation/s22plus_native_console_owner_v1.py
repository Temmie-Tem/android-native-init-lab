"""Parameterized durable CONTROL and empty-plan interfaces; no device opener.

Uses existing record publication/read rules and the original 30-second return
window. Each instance belongs to one candidate, never the consumed roundtrip.
"""
import datetime
import hashlib
import importlib
import json
from pathlib import Path
import re
import time

# Resolve storage after the candidate's source-isolated import has completed.
# Importing the F1 coordinator while its registry is being built is recursive.
# Both modules are explicitly included in the execution source closure.
def _core(): return importlib.import_module('device_action_f1_v2')
def _records(): return importlib.import_module('s22plus_fyg8_p363_return_host')


def identity(raw): return dict(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
def digest(value): return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None
def canonical(value): return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


class ReturnHost:
    SOFTWARE_WINDOW_SECONDS = 30
    ReturnControlError = ValueError
    stable_record = staticmethod(lambda path: _records().stable_record(path))
    host_boot_sha256 = staticmethod(lambda: _records().host_boot_sha256())

    def __init__(self, selected, semantics):
        self.selected, self.spec = selected, semantics
        self.RUN_ID = selected.run_id_hex; self.__file__ = __file__
        self.INTENT_NAME = selected.namespace+'-control-intent.json'
        self.WINDOW_NAME = selected.namespace+'-return-window.json'
        self.intent_schema = 's22plus_fyg8_'+selected.namespace+'_control_intent_v1'
        self.window_schema = 's22plus_fyg8_'+selected.namespace+'_return_window_v1'

    def exists(self, run_dir):
        path = Path(run_dir)/self.INTENT_NAME
        return path.exists() or path.is_symlink()

    def _request(self, request):
        expected = dict(run_id_hex=self.RUN_ID, mode='download', boot_id_semantic=self.spec.BOOT_ID_SEMANTIC,
                        boot_receipt_semantic=self.spec.BOOT_RECEIPT_SEMANTIC)
        if (type(request) is not dict or set(request) != set(expected)|{'sequence', 'nonce_sha256', 'kernel_boot_identity_sha256'}
                or any(type(request[k]) is not type(v) or request[k] != v for k, v in expected.items())
                or type(request['sequence']) is not int or request['sequence'] not in (5, 6)
                or not all(digest(request[k]) for k in ('nonce_sha256', 'kernel_boot_identity_sha256'))):
            raise self.ReturnControlError('native CONTROL request differs')

    def write_intent(self, run_dir, *, binding, endpoint_identity_sha256, lane, request):
        if self.exists(run_dir): raise self.ReturnControlError('native CONTROL is already consumed')
        self._request(request)
        if (type(binding) is not dict or not binding or not digest(endpoint_identity_sha256)
                or type(lane) is not dict or lane.get('accepted_for_p324') is not True
                or lane.get('observation_phase') != 'before-native-return-control'):
            raise self.ReturnControlError('native pre-CONTROL binding differs')
        value = dict(schema=self.intent_schema, binding=binding, endpoint_identity_sha256=endpoint_identity_sha256,
            request=request, lane=lane, created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            created_monotonic_ns=time.monotonic_ns(), host_boot_sha256=self.host_boot_sha256(),
            software_window_seconds=self.SOFTWARE_WINDOW_SECONDS, replay_forbidden=True,
            effect_occurrence='UNKNOWN', source=identity(Path(__file__).read_bytes()))
        _core()._write_exclusive(Path(run_dir)/self.INTENT_NAME, value)
        reopened, receipt = self.read_intent(run_dir, binding=binding, endpoint_identity_sha256=endpoint_identity_sha256)
        if reopened != value: raise self.ReturnControlError('native CONTROL durable reopen differs')
        return receipt

    def read_intent(self, run_dir, *, binding=None, endpoint_identity_sha256=None, proof=None):
        value, receipt = self.stable_record(Path(run_dir)/self.INTENT_NAME)
        fields = {'schema', 'binding', 'endpoint_identity_sha256', 'request', 'lane', 'created_utc',
                  'created_monotonic_ns', 'host_boot_sha256', 'software_window_seconds', 'replay_forbidden',
                  'effect_occurrence', 'source'}
        if (set(value) != fields or value['schema'] != self.intent_schema or value['replay_forbidden'] is not True
                or value['effect_occurrence'] != 'UNKNOWN' or type(value['created_monotonic_ns']) is not int
                or value['created_monotonic_ns'] <= 0 or not digest(value['host_boot_sha256'])
                or type(value['software_window_seconds']) is not int or value['software_window_seconds'] != 30
                or not digest(value['endpoint_identity_sha256']) or type(value['binding']) is not dict or not value['binding']
                or type(value['lane']) is not dict or value['lane'].get('accepted_for_p324') is not True
                or value['lane'].get('observation_phase') != 'before-native-return-control'
                or value['source'] != identity(Path(__file__).read_bytes())):
            raise self.ReturnControlError('native CONTROL retained fields differ')
        self._request(value['request'])
        if binding is not None and value['binding'] != binding: raise self.ReturnControlError('native CONTROL run differs')
        if endpoint_identity_sha256 is not None and value['endpoint_identity_sha256'] != endpoint_identity_sha256:
            raise self.ReturnControlError('native CONTROL endpoint differs')
        if proof is not None:
            for field, proof_key in (('sequence', 'control_sequence'), ('nonce_sha256', 'nonce_sha256'),
                                     ('kernel_boot_identity_sha256', 'kernel_boot_identity_sha256')):
                if value['request'][field] != proof[proof_key]: raise self.ReturnControlError('native CONTROL raw join differs')
        return value, receipt

    def remaining_window(self, intent):
        if intent['host_boot_sha256'] != self.host_boot_sha256(): return 0.0
        now = time.monotonic_ns(); started = intent['created_monotonic_ns']
        if now < started: return 0.0
        return max(0.0, self.SOFTWARE_WINDOW_SECONDS-(now-started)/1e9)

    def validate_window(self, value, *, binding, intent, intent_receipt):
        fields = {'schema', 'binding', 'control_intent', 'outcome', 'observed_within_software_deadline',
                  'closed_monotonic_ns', 'host_boot_sha256', 'physical_prompt_required', 'physical_intervention',
                  'software_causal_attribution', 'rollback_topology_record'}
        if (type(value) is not dict or set(value) != fields or value['schema'] != self.window_schema
                or value['binding'] != binding or value['control_intent'] != intent_receipt
                or type(value['closed_monotonic_ns']) is not int or value['closed_monotonic_ns'] <= 0
                or not digest(value['host_boot_sha256']) or type(value['outcome']) is not str
                or value['physical_intervention'] != 'UNOBSERVED' or value['software_causal_attribution'] != 'UNPROVED'):
            raise self.ReturnControlError('native return window shape differs')
        arrived = value['outcome'] in ('exact-download-within-control-window', 'exact-download-after-control-window')
        within = value['outcome'] == 'exact-download-within-control-window'
        if (value['outcome'] not in {'not-requested', 'window-expired-before-observation', 'software-window-timed-out',
                                    'exact-download-within-control-window', 'exact-download-after-control-window'}
                or value['observed_within_software_deadline'] is not within
                or value['physical_prompt_required'] is not (not arrived)
                or (intent is None) != (value['outcome'] == 'not-requested')):
            raise self.ReturnControlError('native return window status differs')
        receipt = value['rollback_topology_record']
        if arrived:
            if (type(receipt) is not dict or set(receipt) != {'path', 'size', 'sha256'}
                    or type(receipt['path']) is not str or type(receipt['size']) is not int
                    or receipt['size'] <= 0 or not digest(receipt['sha256'])):
                raise self.ReturnControlError('native return exact Download receipt missing')
        elif receipt is not None: raise self.ReturnControlError('native return absent Download has receipt')
        if within and (value['host_boot_sha256'] != intent['host_boot_sha256'] or not
                intent['created_monotonic_ns'] <= value['closed_monotonic_ns'] <= intent['created_monotonic_ns']+30*10**9):
            raise self.ReturnControlError('native return original deadline differs')
        return value


class EmptyPlan:
    ConsolePlanError = ValueError
    MAX_COMMANDS = 0

    def __init__(self, selected):
        self.selected = selected; self.__file__ = __file__
        self.SCHEMA = 's22plus_fyg8_'+selected.namespace+'_root_console_plan_v1'
        self.SEALED_NAME = selected.namespace+'-root-console-plan.json'

    def validate(self, value):
        if value != {'schema': self.SCHEMA, 'commands': []}: raise ValueError('native adoption requires an empty operator plan')
        return value

    def load(self, path):
        value, _ = _core().load_json(Path(path), 'native empty plan')
        self.validate(value)
        if Path(path).read_bytes() != canonical(value): raise ValueError('native empty plan encoding differs')
        return value

    def seal(self, source, run_dir):
        value = self.load(source) if source is not None else dict(schema=self.SCHEMA, commands=[])
        path = Path(run_dir)/self.SEALED_NAME
        if path.exists() or path.is_symlink():
            if self.load(path) != value: raise ValueError('native empty plan differs')
        else: _core()._write_exclusive(path, value)
        raw = path.read_bytes()
        return value, dict(path=str(path), **identity(raw), command_count=0)

    def execution_projection(self, plan, command_rows):
        self.validate(plan)
        if command_rows != []: raise ValueError('unexpected operator command after fixed local observation')
        return dict(schema='s22plus_fyg8_'+self.selected.namespace+'_plan_execution_v1', planned_command_count=0,
            executed_request_count=0, terminal_command_count=0, unexecuted_command_count=0, all_planned_terminal=True, results=[])

    def run(self, session, events, deadline, plan): self.validate(plan)
