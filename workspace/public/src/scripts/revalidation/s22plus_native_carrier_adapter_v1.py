"""Fresh candidate binding of the existing Carrier parser; supplemental only."""
import hashlib
import importlib.util
import json
from pathlib import Path

import s22plus_fyg8_p320_stock_process_v2_adapter as parser_source


class CarrierAdapter:
    ContractError = AdapterIdentityError = DecodeError = ObserverContractError = ValueError
    PROFILE = parser_source.PROFILE
    PARENT_SOURCE_CONTRACT_ID = parser_source.PARENT_SOURCE_CONTRACT_ID
    P320_PAYLOAD_ABI = parser_source.P320_PAYLOAD_ABI
    OBSERVER_RECEIPT_SIZE = parser_source.OBSERVER_RECEIPT_SIZE
    SOURCE_PATHS = dict(parser_source.SOURCE_PATHS)
    SOURCE_KEYS = frozenset(SOURCE_PATHS)
    RAW_PARSER_SOURCE = Path(parser_source.__file__)
    RAW_PARSER_SOURCE_IDENTITY = dict(size=56669, sha256='92be097287be67867b263e5534996228d275d1d70fa03c38b3a124a948a94d88')
    INITIAL_SESSION_COUNT = SAME_FD_SESSION_COUNT = 1
    INITIAL_RECONNECT_COUNT = IDLE_SECONDS = 0
    TOTAL_COMMANDS = 2
    NATIVE_SOURCE_PROFILE = 'local-display-v1'
    model = parser_source.model
    spec = parser_source.spec

    def __init__(self, selected, observer):
        self.selected, self.observer = selected, observer
        self.__file__ = __file__; self.SOURCE = Path(__file__)
        self.RUN_ID = self.STOCK_RUN_ID = bytes.fromhex(selected.run_id_hex)
        setattr(self, selected.namespace.upper()+'_RUN_ID_HEX', selected.run_id_hex)
        setattr(self, selected.namespace.upper()+'_RUN_ID', self.RUN_ID)
        self.OVERLAY_CONTRACT_ID = 's22plus-fyg8-'+selected.namespace+'-local-display-console-v1'
        self.DECODER_ID = 's22plus_fyg8_'+selected.namespace+'_local_display_console_v1'
        self.OBSERVER_CONTRACT_ID = observer.CONTRACT_ID
        self.SCHEMA = 's22plus_fyg8_'+selected.namespace+'_stock_process_v2_adapter_v1'
        self.POLICY_ID = hashlib.sha256((self.OVERLAY_CONTRACT_ID+'|'+selected.run_id_hex+
            '|fixed-native-health|optional-local-hud|one-authenticated-tty|control5-or6|one-android-rollback').encode()).hexdigest()[:32]
        self._parser = None

    @staticmethod
    def identity(raw): return dict(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())

    def _raw_parser(self):
        if self._parser is None:
            if self.identity(self.RAW_PARSER_SOURCE.read_bytes()) != self.RAW_PARSER_SOURCE_IDENTITY:
                raise ValueError('Carrier parser source differs')
            spec = importlib.util.spec_from_file_location('carrier_bound_'+self.selected.namespace, self.RAW_PARSER_SOURCE)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            # Exact immutable parser source, parameter binding before any decode.
            for key in ('STOCK_RUN_ID', 'RUN_ID', 'P320_RUN_ID', 'P320_STOCK_RUN_ID'): setattr(module, key, self.RUN_ID)
            for key in ('SCHEMA', 'OVERLAY_CONTRACT_ID', 'DECODER_ID', 'POLICY_ID'): setattr(module, key, getattr(self, key))
            self._parser = module
        return self._parser

    def _fresh(self, value):
        return dict(value, schema=self.SCHEMA, run_id=self.selected.run_id_hex,
            decoder=self.DECODER_ID, policy_id=self.POLICY_ID, overlay_contract_id=self.OVERLAY_CONTRACT_ID,
            userspace_overlay_contract_id=self.OVERLAY_CONTRACT_ID, observer_contract_id=self.OBSERVER_CONTRACT_ID,
            raw_parser_bound_run_id=self.selected.run_id_hex, predecessor_raw_relabelled=False,
            causal_result_allowed=False, candidate_success=False, device_contact=False, live_authorized=False)

    def _bound(self, profile, run_id):
        if profile != self.PROFILE or run_id not in (None, self.RUN_ID): raise ValueError('Carrier candidate binding differs')

    def decode_record(self, record, *, expected_profile=PROFILE, expected_run_id=None):
        self._bound(expected_profile, expected_run_id)
        return self._fresh(self._raw_parser().decode_record(record, expected_profile=self.PROFILE, expected_run_id=self.RUN_ID))

    def classify_observation(self, payload, *, expected_profile=PROFILE, expected_run_id=None):
        self._bound(expected_profile, expected_run_id)
        value = self._raw_parser().classify_observation(payload, expected_profile=self.PROFILE, expected_run_id=self.RUN_ID)
        return dict(self._fresh(value), acm_primary=True, carrier_supplemental=True, acm_supplemental=False,
            acm_required_for_acceptance=True, acm_required_for_arrival_proof=True,
            **{self.selected.namespace+'_stock': [r['p320_stock']['stock'] for r in value.get('records', ())
                                                if type(r) is dict and 'p320_stock' in r]})

    def classify_clean_baseline(self, payload, *, expected_profile=PROFILE, expected_run_id=None):
        self._bound(expected_profile, expected_run_id)
        return self._fresh(self._raw_parser().classify_clean_baseline(payload, expected_profile=self.PROFILE, expected_run_id=self.RUN_ID))

    def source_bytes(self, root=None): return parser_source.source_bytes(root)

    def _contract(self):
        return dict(userspace_overlay_contract_id=self.OVERLAY_CONTRACT_ID, decoder=self.DECODER_ID,
            policy_id=self.POLICY_ID, profile=self.PROFILE, source_contract_id=self.PARENT_SOURCE_CONTRACT_ID,
            observer_contract_id=self.OBSERVER_CONTRACT_ID, payload_abi=self.P320_PAYLOAD_ABI,
            observer_receipt_size=self.OBSERVER_RECEIPT_SIZE, causal_result_allowed=False, candidate_success=False,
            runtime_behavior_unchanged=False, runtime_delta_identity_only=False, root_console=True,
            read_only_child_required=False, initial_session_count=self.INITIAL_SESSION_COUNT,
            same_fd_session_count=self.SAME_FD_SESSION_COUNT,
            initial_reconnect_count=self.INITIAL_RECONNECT_COUNT, idle_seconds=0, later_action_lease_active=False, mandatory_rollback=True,
            native_return_control=True, native_usb_departure_before_odin=True, software_window_renewed=False,
            control_ack_scope='acceptance-only', local_display_profile=self.NATIVE_SOURCE_PROFILE,
            root_work_stages_61_62='cached-before-auth', arbitrary_operator_commands=False,
            automatic_recovery_proved=False, permanent_boundaries_unchanged=True)

    def acceptance_fixture(self):
        value = parser_source.acceptance_fixture()
        value.update(decoder=self.DECODER_ID, policy_id=self.POLICY_ID, run_id=self.selected.run_id_hex,
            userspace_overlay_contract_id=self.OVERLAY_CONTRACT_ID, observer_contract_id=self.OBSERVER_CONTRACT_ID,
            observer_contract=dict(id=self.OBSERVER_CONTRACT_ID, payload_abi=self.P320_PAYLOAD_ABI,
                                   receipt_size=self.OBSERVER_RECEIPT_SIZE),
            initial_session_count=self.INITIAL_SESSION_COUNT, same_fd_session_count=self.SAME_FD_SESSION_COUNT,
            initial_reconnect_count=self.INITIAL_RECONNECT_COUNT, idle_seconds=0,
            later_action_lease_active=False, mandatory_rollback=True, qualification_schema=self.observer.SCHEMA,
            qualification_commands=[dict(ordinal=s.ordinal, name=s.name, command_hex=s.command.hex(), expected_outcome='ok')
                                    for s in self.observer.QUALIFICATION_COMMANDS])
        return value

    def validate_acceptance_item(self, value):
        expected = self.acceptance_fixture()
        if (type(value) is not dict or set(value) != set(expected)
                or any(json.dumps(value[k], sort_keys=True) != json.dumps(v, sort_keys=True) for k, v in expected.items() if k != 'contract')):
            raise ValueError('native candidate acceptance differs')
        contracts = value['contract']
        if type(contracts) is not dict or set(contracts) != {'candidate_static', 'run_manifest', 'static_check'}:
            raise ValueError('native candidate acceptance source contract differs')
        for receipt in contracts.values():
            if (type(receipt) is not dict or set(receipt) != {'path', 'size', 'sha256'} or type(receipt['path']) is not str
                    or not receipt['path'] or type(receipt['size']) is not int or receipt['size'] <= 0
                    or type(receipt['sha256']) is not str or len(receipt['sha256']) != 64
                    or any(c not in '0123456789abcdef' for c in receipt['sha256'])):
                raise ValueError('native candidate acceptance receipt differs')
        return value

    def validate_contract(self, value):
        if type(value) is not dict or any(json.dumps(value.get(k), sort_keys=True) != json.dumps(v, sort_keys=True)
                                          for k, v in self._contract().items()):
            raise ValueError('native candidate overlay contract differs')
        return value

    def bind_exact_sources(self, auth_key=None):
        value = self._raw_parser().bind_exact_sources()
        return dict(self._fresh({}), target=value['target'], sources=value['sources'],
            parent_source_contract_id=self.PARENT_SOURCE_CONTRACT_ID, carrier_binding=value,
            raw_parser_source=dict(path=str(self.RAW_PARSER_SOURCE), **self.RAW_PARSER_SOURCE_IDENTITY),
            contract=self._contract(), initial_collector=self.observer.audit_binding())

    bind_lineage = bind_exact_sources

    def audit(self):
        return dict(self.bind_exact_sources(), schema=self.SCHEMA,
            verdict='PASS_'+self.selected.namespace.upper()+'_STOCK_PROCESS_V2_ADAPTER_H0',
            initial_session_count=self.INITIAL_SESSION_COUNT,
            initial_reconnect_count=self.INITIAL_RECONNECT_COUNT, total_commands=self.TOTAL_COMMANDS,
            runtime_behavior_unchanged=False, catalog_unchanged=False, later_action_lease_active=False, mandatory_rollback=True)
