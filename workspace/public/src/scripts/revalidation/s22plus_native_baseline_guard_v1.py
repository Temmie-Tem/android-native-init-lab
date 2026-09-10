"""Exact-present native entry composed from the existing CDC/P324/P325 guard.

Default sessions retain their absent-candidate baseline. A retained native
entry records presence honestly and requires current ModemManager ignore flags;
it does not trigger udev, repair properties or promise protection between owners.
"""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import re

import device_action_cdc_acm_observer_v1 as cdc
import device_action_f1_v2 as core
import s22plus_fyg8_p324_cdc_acm_observer as lane_observer
import s22plus_fyg8_p325_cdc_acm_guard_adapter as guard_adapter

BASELINE_SCHEMA = 's22plus-native-baseline-present-cdc-v1'
ARM_SCHEMA = 's22plus-native-baseline-present-lane-arm-v1'


def retained(live, prepared, *, active=False):
    context = prepared.native_baseline_context
    if context is None or context.get('phase') != 'native-start': return None
    import s22plus_native_baseline_owner_v1 as owner
    owner.validate_observation_context(live, prepared)
    operation = owner.load_operation(live, prepared.root, context['operation'], active=active)
    terminal_path = owner.verify_pin(prepared.root, operation.value['prior_native'])
    previous = owner.native_terminal(live, prepared.root, terminal_path.parent)
    owner.require(owner.same(previous['target'], operation.request['target']),
                  'retained native guard belongs to another physical target')
    return dict(context_sha256=core.json_sha256(context), terminal=operation.value['prior_native'],
        endpoint_identity_sha256=previous['endpoint_identity_sha256'])


def validate_inventory(inventory, expected=None):
    lane_observer._validate_inventory(inventory, label='native baseline arm')
    source = inventory['rows'][lane_observer.lane.SOURCE_TOPOLOGY]
    candidate = inventory['rows'][lane_observer.lane.CANDIDATE_TOPOLOGY]
    valid = (inventory['foreign_candidate_like_count'] == 0 and source['candidate_like_count'] == 0
        and source['exact_candidate_count'] == 0)
    if expected is None:
        valid = valid and candidate['candidate_like_count'] == 0 and candidate['exact_candidate_count'] == 0
    else:
        valid = valid and candidate['candidate_like_count'] == 1 and candidate['exact_candidate_count'] == 1
        valid = valid and expected in candidate['endpoint_identity_sha256']
    if not valid: raise cdc.ObserverError('native baseline arm candidate inventory differs')


@contextmanager
def observer_session(live, prepared, spec, source_topology, run_dir, binding, lane_binding, lane_receipt, *,
                     usb_root, typec_root, class_tty=Path('/sys/class/tty'), dev_root=Path('/dev')):
    request = retained(live, prepared, active=True)
    if request is None:
        with guard_adapter.observer_session(spec, source_topology, run_dir, binding, lane_binding, lane_receipt,
                usb_root=usb_root, typec_root=typec_root, class_tty=class_tty, dev_root=dev_root) as session:
            yield session
        return
    cdc.validate_spec(spec)
    current_lane = lane_observer.lane.revalidate_binding(lane_binding, source_topology=source_topology,
        usb_root=usb_root, typec_root=typec_root)
    inventory = lane_observer._inventory(spec, class_tty, usb_root)
    validate_inventory(inventory, request['endpoint_identity_sha256'])
    entries = [cdc._resolve_endpoint(path) for path in sorted(class_tty.glob('ttyACM*'))]
    exact = [endpoint for identity, endpoint in entries if lane_observer._exact(spec,
        lane_observer.lane.CANDIDATE_TOPOLOGY, identity, endpoint, usb_root)]
    if len(exact) != 1 or exact[0].identity_sha256 != request['endpoint_identity_sha256']:
        raise cdc.ObserverError('retained native candidate endpoint changed')
    partner = lane_observer._partner(typec_root)
    arm = dict(schema=ARM_SCHEMA, contract_id=lane_observer.CONTRACT_ID, target=lane_observer.TARGET,
        lane_binding=lane_receipt, lane_binding_sha256=lane_observer._digest(current_lane),
        source_topology=lane_observer.lane.SOURCE_TOPOLOGY, candidate_topology=lane_observer.lane.CANDIDATE_TOPOLOGY,
        selector_topology_count=1, partner_before=partner, inventory=inventory,
        both_topologies_inventory_complete=True, candidate_absent_on_both=False,
        candidate_like_absent_everywhere=False, opens_candidate_acm=False, device_commands=False,
        retained_native=request)
    arm_pin = cdc.persist_json(run_dir/lane_observer.ARM_NAME, arm)
    topology = lane_observer.lane.CANDIDATE_TOPOLOGY
    baseline = dict(schema=BASELINE_SCHEMA, spec_sha256=cdc.digest(spec),
        topology_sha256=hashlib.sha256(topology.removeprefix('usb:').encode()).hexdigest(),
        identity_sha256=sorted(endpoint.identity_sha256 for _,endpoint in entries),
        exact_candidate_absent=False, retained_native=request)
    with cdc._bound_observer_session(spec, topology, run_dir, binding, baseline=baseline,
            class_tty=class_tty, dev_root=dev_root, usb_root=usb_root) as base:
        # A reload does not update existing devices. Retained same-endpoint
        # entry uses only flags actually observed now; missing flags stop it.
        if not base.guard.matches_node(exact[0].tty_class):
            raise cdc.ObserverError('retained native current ModemManager flags missing')
        lane_session = lane_observer.P324ObserverSession(base, spec, run_dir, current_lane,
            lane_receipt, arm, arm_pin, partner, class_tty, usb_root, typec_root)
        with guard_adapter.adapt_delegate(base) as audit:
            yield guard_adapter.P325ObserverSession(lane_session, audit)


def validate_baseline(live, prepared, value):
    request = retained(live, prepared)
    baseline = live._read_json(prepared.run_dir/'candidate-observer-baseline.json', 'native baseline capture')
    arm = live._read_json(prepared.run_dir/lane_observer.ARM_NAME, 'native baseline lane arm')
    spec = live._p327_inherited_spec(prepared.bundle.manifest['observation']['candidate_observer'])
    baseline_keys = {'schema','spec_sha256','topology_sha256','identity_sha256','exact_candidate_absent'}
    arm_keys = {'schema','contract_id','target','lane_binding','lane_binding_sha256','source_topology',
        'candidate_topology','selector_topology_count','partner_before','inventory','both_topologies_inventory_complete',
        'candidate_absent_on_both','candidate_like_absent_everywhere','opens_candidate_acm','device_commands'}
    if request is not None:
        baseline_keys.add('retained_native'); arm_keys.add('retained_native')
    lane, lane_pin = live._p324_typec_lane_value(prepared)
    absent = request is None
    if (set(baseline) != baseline_keys or set(arm) != arm_keys
            or baseline['schema'] != (cdc.BASELINE_SCHEMA if absent else BASELINE_SCHEMA)
            or baseline['spec_sha256'] != cdc.digest(spec)
            or baseline['topology_sha256'] != value['topology_sha256']
            or baseline['exact_candidate_absent'] is not absent
            or type(baseline['identity_sha256']) is not list or len(baseline['identity_sha256']) > 256
            or any(type(v) is not str or re.fullmatch('[0-9a-f]{64}', v) is None for v in baseline['identity_sha256'])
            or baseline['identity_sha256'] != sorted(set(baseline['identity_sha256']))
            or arm['schema'] != (lane_observer.ARM_SCHEMA if absent else ARM_SCHEMA)
            or arm['contract_id'] != lane_observer.CONTRACT_ID or arm['target'] != lane_observer.TARGET
            or arm['lane_binding'] != lane_pin or arm['lane_binding_sha256'] != lane_observer._digest(lane)
            or arm['source_topology'] != lane_observer.lane.SOURCE_TOPOLOGY
            or arm['candidate_topology'] != lane_observer.lane.CANDIDATE_TOPOLOGY
            or type(arm['selector_topology_count']) is not int or arm['selector_topology_count'] != 1
            or arm['both_topologies_inventory_complete'] is not True
            or arm['candidate_absent_on_both'] is not absent or arm['candidate_like_absent_everywhere'] is not absent
            or arm['opens_candidate_acm'] is not False or arm['device_commands'] is not False):
        raise live.F1LiveError('native baseline initial presence/absence proof differs')
    lane_observer._validate_partner(arm['partner_before'], 'native baseline arm')
    if not live._p319_exact_equal(arm['partner_before'], value['lane'].get('partner_before')):
        raise live.F1LiveError('native arm/observation Type-C partner differs')
    validate_inventory(arm['inventory'], request['endpoint_identity_sha256'] if request else None)
    if request is not None and (not live._p319_exact_equal(baseline['retained_native'], request)
            or not live._p319_exact_equal(arm['retained_native'], request)
            or value['endpoint_identity_sha256'] != request['endpoint_identity_sha256']
            or request['endpoint_identity_sha256'] not in baseline['identity_sha256']):
        raise live.F1LiveError('native retained initial/current endpoint binding differs')
    return True
