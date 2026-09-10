"""Native-baseline observation and exact retained multi-session replay.

The F1 owner supplies all endpoint operations and durable terminal intents.
This adapter never discovers, opens or reconnects a device by itself.
"""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import s22plus_native_baseline_protocol_v1 as protocol
import s22plus_native_console_observer_v1 as console
import s22plus_native_source_v1 as source
import s22plus_native_baseline_health_v1 as health

MODES = ('pair-control', 'pair-detach', 'control', 'detach')


def mode_sessions(mode):
    if mode not in MODES: raise ValueError('native baseline observation mode differs')
    return 2 if mode.startswith('pair-') else 1


class Observer(console.Observer):
    SESSION_COUNT = 2
    PROOF_SCOPE = 'fixed-native-health-and-clean-bounded-reauthentication'

    def __init__(self, identity, control):
        super().__init__(identity, control)
        self.__file__ = __file__
        self.SCHEMA = 's22plus-fyg8-'+identity.namespace+'-native-baseline-qualification-v1'
        self.CONTRACT_ID = 's22plus-fyg8-'+identity.namespace+'-native-baseline-observer-v1'
        self.PROOF_SCOPE = type(self).PROOF_SCOPE
        self.QUALIFICATION_COMMANDS = tuple(SimpleNamespace(ordinal=i,
            name='native-health-authentication-'+str(i), command=health.COMMAND) for i in (1, 2))

    def IO(self, codec, key, **kwargs):
        return protocol.IO(codec, key, self.identity, **kwargs)

    def progress_projection(self, audit):
        return getattr(audit, 'native_preparation', protocol.Progress(self.identity)).projection()

    @staticmethod
    def operator_plan_rows(proof):
        if type(proof.get('commands', [])) is not list:
            raise ValueError('native baseline command rows differ')
        return []

    def _joined(self, mode, rows):
        expected = mode_sessions(mode)
        if len(rows) != expected: raise ValueError('baseline authentication count differs')
        if len({row['nonce_sha256'] for row in rows}) != len(rows):
            raise ValueError('baseline nonce was reused within retained proof')
        if len(rows) == 2: protocol.fresh_same_boot(rows[0], rows[1])
        ending = 'download' if mode.endswith('control') else 'detach'
        if rows[-1]['ending'] != ending:
            raise ValueError('baseline terminal mode differs')
        if any(not row['native_health_proved'] or not row['all_commands_terminal_or_rejected']
               or row['source_profile'] != source.profile_contract(source.BASELINE_PROFILE) for row in rows):
            raise ValueError('baseline complete health/profile is missing')
        commands = [dict(row, authentication=i+1) for i, session in enumerate(rows) for row in session['commands']]
        last = rows[-1]
        return dict(schema=self.SCHEMA, run_id_hex=self.RUN_ID_HEX, mode=mode, proved=True,
            session_count=expected, command_count=len(commands), request_count=sum(row['request_count'] for row in rows),
            commands=commands, sessions=rows, preparation=rows[0]['preparation'], root_ready=last['root_ready'],
            nonce_sha256=last['nonce_sha256'], kernel_boot_identity_sha256=last['kernel_boot_identity_sha256'],
            control_sequence=last['terminal_sequence'] if ending == 'download' else None,
            control_acceptance_observed=ending == 'download', clean_detach_observed=ending == 'detach',
            same_tty_fd=expected == 1, physical_reopen_count=expected-1, console_reentry=expected == 2,
            all_commands_terminal_or_rejected=True, qualified_command_count=expected,
            control_ack_scope='acceptance-only', native_health_proved=True,
            remaining_authentications=protocol.AUTH_LIMIT-last['baseline_info']['authentication_ordinal'],
            boot_elapsed_ms=last['baseline_info']['elapsed_ms'], boot_limit_ms=protocol.BOOT_LIMIT_MS,
            physical_visibility='UNPROVED', source_profile=source.profile_contract(source.BASELINE_PROFILE))

    def replay_session(self, codec, rx, tx, key, *, partial=False, mode='pair-control'):
        count = mode_sessions(mode); rows = []; roffset = toffset = 0
        for _ in range(count):
            row, received, sent = protocol.replay_one(codec, self.identity, key, rx[roffset:], tx[toffset:])
            row['rx']['offset'] = roffset; row['tx']['offset'] = toffset
            rows.append(row); roffset += received; toffset += sent
        if (roffset, toffset) != (len(rx), len(tx)):
            raise ValueError('baseline trailing or additional authentication bytes')
        value = self._joined(mode, rows)
        if not partial: self.validate_qualification(value)
        return value

    def validate_qualification(self, value):
        if (type(value) is not dict or value.get('schema') != self.SCHEMA
                or value.get('run_id_hex') != self.RUN_ID_HEX or value.get('proved') is not True
                or type(value.get('sessions')) is not list):
            raise console.QualificationError('native baseline qualification identity differs')
        try:
            expected = self._joined(value['mode'], value['sessions'])
            if json.dumps(value, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False):
                raise ValueError('baseline qualification projection differs')
        except (ValueError, TypeError, KeyError) as exc:
            raise console.QualificationError('native baseline qualification differs') from exc
        return copy.deepcopy(value)

    def qualify(self, codec, descriptor, auth_key, expected_boot_sha256, seen_nonces, writer, *,
                deadline, before_control, evidence, interactive=None, mode='pair-control',
                before_detach=None, reopen=None, before_auth=None, before_native_terminal=None, before_write=None):
        count = mode_sessions(mode)
        if expected_boot_sha256 is not None or seen_nonces:
            raise console.QualificationError('baseline observation cannot inherit an unbound session')
        if not callable(before_detach) or count == 2 and not callable(reopen):
            raise console.QualificationError('baseline requires its descriptor/DETACH owner')
        sessions = []; rows = []; current = descriptor; io = None
        Path(evidence).mkdir(mode=0o700, parents=False, exist_ok=False)
        def terminal(request):
            if rows:
                protocol.fresh_same_boot(rows[-1], request)
            if before_native_terminal is not None:
                before_native_terminal(request)
            if request['mode'] == 'detach':
                before_detach(request)
            else:
                before_control({**{k: v for k, v in request.items() if k != 'baseline_info'},
                    'boot_id_semantic': self.control.BOOT_ID_SEMANTIC,
                    'boot_receipt_semantic': self.control.BOOT_RECEIPT_SEMANTIC})
        try:
            if interactive is not None: interactive(None, [], deadline)
            for index in range(count):
                io = self.IO(codec, auth_key, fd=current, writer=writer, deadline=deadline, before_write=before_write)
                if before_auth is not None: before_auth(index+1)
                ending = 'detach' if index < count-1 or mode.endswith('detach') else 'download'
                row = protocol.qualify_one(io, ending=ending, evidence=Path(evidence)/('auth-'+str(index+1)),
                    before_terminal=terminal, hud=count == 2 and index == count-1)
                if rows: protocol.fresh_same_boot(rows[-1], row)
                rows.append(row)
                sessions.append(SimpleNamespace(session=SimpleNamespace(audit=io.audit)))
                seen_nonces.add(health.digest(io.audit.nonce))
                if index < count-1:
                    current = reopen(row, deadline)
            rx = b''.join(bytes(s.session.audit.rx) for s in sessions)
            tx = b''.join(bytes(s.session.audit.tx) for s in sessions)
            value = self.replay_session(codec, rx, tx, auth_key, mode=mode)
            return console.QualificationResult(value, tuple(sessions))
        except BaseException as exc:
            # Completed sessions and the failing current session remain distinct
            # so the outer raw writer's prefix can always be reconstructed.
            failed = io.audit if io is not None and not any(s.session.audit is io.audit for s in sessions) else None
            if failed is not None: failed.failure_stage = failed.current_stage
            error = console.QualificationError('native baseline stopped; no authentication replay', audit=failed,
                partial_receipt=dict(schema=self.SCHEMA, run_id_hex=self.RUN_ID_HEX, mode=mode,
                    proved=False, sessions=rows, commands=[], session_count=len(sessions),
                    preparation=(rows[0]['preparation'] if rows else io.preparation.projection() if io else None),
                    failure_type=type(exc).__name__))
            error.completed_sessions = tuple(sessions)
            raise error from exc

    def audit_binding(self):
        return dict(schema=self.SCHEMA, contract_id=self.CONTRACT_ID, session_count=2,
            qualification_timeout_sec=60, root_console=True, qualified_exec_count=2,
            optional_hud_exec_count=1, interactive_commands=False, physical_reopen_count=1,
            source_profile=source.profile_contract(source.BASELINE_PROFILE),
            control_sequences=[5, 6], detach_sequences=[5, 6], control_ack_scope='acceptance-only',
            raw_replay_required=True, live_authorized=False)
