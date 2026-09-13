"""Fixed resident D0 observations, including bounded fresh attempts after failure.

An attempt never sends CONTROL or a caller-selected command. Its old raw result
stays immutable. Only a complete new authenticated health/DETACH/close can form
a native-state tail; no observation can retire a pending F1 recovery owner.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import select
import stat
import struct
import termios
import time

import device_action_cdc_acm_observer_v1 as cdc
import device_action_raw_capture_v1 as raw
import s22plus_native_baseline_owner_v1 as owner
import s22plus_native_baseline_protocol_v1 as protocol
import s22plus_native_baseline_health_v1 as health
import s22plus_native_baseline_v2_candidates as candidates

ROOT = owner.ROOT
SCHEMA = 's22plus-native-reobservation-v1'
BASE = Path('workspace/private/runs/s22plus-native-reobservation-v1')
LEGACY_SCHEMA = 's22plus-p387-requested-resident-checkpoint-d0-v1'
LEGACY_SOURCE_SHA256 = '7f5b63e5d85f7d2f597965cc4f2c434b0d639a547229bd454d0a219f2b245abb'
MAX_SECONDS = 60


def _completed(handle):
    # These two profiles deliberately use stderr: fuser's exact node label,
    # and the wire capture's TX stream. Each caller validates those bytes.
    owner.require(handle.returncode == 0 and not handle.timed_out and not handle.output_exceeded
                  and handle.producer_error_type is None, 'observation producer did not complete')


class DurableWriter:
    """Publish each received chunk before the protocol can interpret it."""
    def __init__(self, directory):
        self.directory = directory; directory.mkdir(mode=0o700); raw._fsync_dir(directory.parent)
        self.writer = raw.RawCaptureWriter(directory, 'wire', stdout_maximum=131072, stderr_maximum=65536)
        self.sequence = 0

    def write_stdout(self, payload):
        owner.require(self.writer.stdout_size+len(payload) <= self.writer.stdout_maximum, 'raw observation bound exceeded')
        self.sequence += 1
        path = self.directory/f'rx-{self.sequence:04d}.bin'
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
        try:
            owner.require(os.write(descriptor, payload) == len(payload), 'short observation raw publication')
            os.fsync(descriptor)
        finally: os.close(descriptor)
        raw._fsync_dir(self.directory)
        owner.require(path.read_bytes() == payload, 'observation raw readback differs')
        self.writer.write_stdout(payload)

    def finish(self, tx, error=None):
        self.writer.write_stderr(tx)
        return self.writer.finalize(returncode=0 if error is None else None,
            producer_error_type=type(error).__name__ if error else None)


def _projection(io):
    return dict(run_id_hex=io.identity.run_id_hex, kernel_boot_identity_sha256=health.digest(io.audit.boot_id),
                nonce_sha256=health.digest(io.audit.nonce), baseline_info=io.preparation.info)


def _fresh(context, current):
    previous = context.last_good
    info = current['baseline_info']; last = previous['baseline_info']
    owner.require(current['run_id_hex'] == previous['run_id_hex']
        and current['kernel_boot_identity_sha256'] == previous['kernel_boot_identity_sha256']
        and current['nonce_sha256'] not in context.seen
        and last['authentication_ordinal'] < info['authentication_ordinal']
        <= last['authentication_ordinal']+context.uncertain_opens+1
        and info['preparation_cached'] is True and info['elapsed_ms'] >= last['elapsed_ms'],
        'fresh same-boot read-only observation is unproved')


def _io_class(context):
    class BoundIO(context.declared.observer.io_class):
        def send(self, kind, sequence, payload):
            if self.raw_rx is None and kind == 4:
                owner.require(len(self.audit.nonce) == 32, 'observation challenge nonce missing')
                ordinal = struct.unpack('<Q', self.audit.nonce[24:])[0]
                previous = context.last_good['baseline_info']['authentication_ordinal']
                owner.require(previous < ordinal <= previous+context.uncertain_opens+1
                    and health.digest(self.audit.nonce) not in context.seen,
                    'observation challenge ordinal/nonce differs before AUTH')
            return super().send(kind, sequence, payload)

        def handshake(self):
            super().handshake()
            if self.raw_rx is None: _fresh(context, _projection(self))
    return BoundIO


@dataclass
class Context:
    root: Path
    previous: Path
    anchor: Path
    base: dict
    prepared: object
    declared: object
    codec: object
    endpoint: dict
    spec: dict
    last_good: dict
    seen: set
    uncertain_opens: int


def _anchor(live, root, terminal):
    base = owner.native_terminal(live, root, terminal.parent)
    operation = owner.load_operation(live, root, terminal.parent)
    owner.require(owner.v2(operation.request) and base['native_expiry_boottime_ns'] is None
                  and owner.read(operation.directory/'completed.json')[0]['terminal'] == owner.pin(terminal),
                  'observation needs a completed admitted resident baseline')
    owner.admission(live, root, base['native'], target=base['target'])
    prepared = owner.phase_prepared(live, operation, 'native-final')
    declared = candidates.declared_for(prepared.bundle)
    owner.require(candidates.research_profile(declared) in candidates.RESEARCH_PROFILES, 'unreviewed observation profile')
    codec = live._open_header_initial_observer_module(declared.runtime, declared.observer, 'native-reobservation')
    endpoint_raw = owner.read(operation.directory/'native-final'/(
        declared.IDENTITY.namespace+'-candidate-end.raw.json'))[0]
    owner.require(len(endpoint_raw['endpoints']) == 1, 'retained native endpoint is ambiguous')
    endpoint = endpoint_raw['endpoints'][0]; identity = endpoint['identity']
    projection = dict(tty_name=identity['tty_name'], topology=endpoint['topology'].removeprefix('usb:'),
        vendor=identity['vendor'], product=identity['product_id'], serial=identity['serial'],
        interface=identity['interface'], driver=identity['driver'])
    owner.require(cdc.digest(projection) == base['endpoint_identity_sha256'], 'retained native endpoint projection differs')
    spec = live._p327_inherited_spec(prepared.bundle.manifest['observation']['candidate_observer'])
    return Context(Path(root), terminal, terminal, base, prepared, declared, codec, endpoint, spec,
                   base['proof']['sessions'][-1], set(base['seen_nonce_hashes']), 0)


def _legacy(live, root, path):
    stopped, _ = owner.read(path); directory = path.parent; original = directory.parent
    owner.require(path.name == 'stopped.json' and stopped.get('schema') == LEGACY_SCHEMA,
                  'legacy observation stop differs')
    plan, plan_pin = owner.read(original/'plan.json')
    owner.require(owner.pin(original/'probe.py')['sha256'] == LEGACY_SOURCE_SHA256
                  and plan.get('schema') == LEGACY_SCHEMA, 'legacy observer was not the reviewed read-only caller')
    context = _anchor(live, root, owner.verify_pin(root, plan['prior']))
    intent, intent_pin = owner.read(directory/'intent.json')
    successor = owner.read(context.anchor.parent/'next-operation.json')[0]
    owner.require(intent['plan'] == plan_pin and stopped['intent'] == intent_pin
                  and successor == dict(schema=LEGACY_SCHEMA, kind='read-only-d0-successor', operation=intent_pin)
                  and plan['target'] == context.base['target'] and plan['endpoint'] == context.endpoint,
                  'legacy D0 is not the actual successor of this native terminal')
    handle = raw.load_handle(directory/'raw/wire.capture.json')
    tx = raw.read_stderr(handle, maximum=65536); rx = raw.read_stdout(handle, maximum=131072)
    expected = context.codec._CODEC.encode_frame(1, 0, bytes.fromhex(context.declared.IDENTITY.run_id_hex))
    owner.require(tx == expected and rx == b'' and handle.producer_error_type == 'TimeoutError'
                  and not handle.output_exceeded and owner.read(directory/'candidate-observer-guard-release.json')[0]['released'] is True
                  and not (directory/'terminal.json').exists() and not (directory/'detach-intent.json').exists(),
                  'legacy import is limited to the retained one-OPEN/RX-zero read-only failure')
    context.previous = path; context.uncertain_opens = 1
    return context


def _read_only_tx(context, tx):
    """A partial observation transcript cannot hide a completed CONTROL/write."""
    offset = 0; wanted = 0; opens = 0
    while offset < len(tx):
        if len(tx)-offset < 16: break
        magic, version, kind, size, sequence, _ = struct.unpack('<4sBBHII', tx[offset:offset+16])
        owner.require(magic == b'S328' and version == 1 and sequence == wanted and size <= protocol.wire.MAX_PAYLOAD,
                      'failed read transcript framing/sequence differs')
        owner.require((wanted == 0 and kind == 1) or (wanted == 1 and kind == 4)
                      or (wanted == 3 and kind == protocol.wire.EXEC)
                      or (wanted == 4 and kind == protocol.wire.STATUS)
                      or (wanted == 5 and kind in (protocol.wire.EXEC, protocol.DETACH))
                      or (wanted == 6 and kind == protocol.DETACH),
                      'failed observation contains an undeclared or state-changing request')
        end = offset+16+size
        if end > len(tx): break
        payload = tx[offset+16:end]
        owner.require(context.codec._CODEC.encode_frame(kind, sequence, payload) == tx[offset:end],
                      'failed read transcript checksum differs')
        if wanted == 0:
            owner.require(payload == bytes.fromhex(context.declared.IDENTITY.run_id_hex), 'failed read OPEN target differs')
            opens = 1; wanted = 1
        elif wanted == 1:
            owner.require(len(payload) == 32, 'failed read AUTH shape differs'); wanted = 3
        else:
            expected = (health.COMMAND_BODY if wanted == 3 else context.declared.observer.io_class.HUD_BODY
                        if wanted == 5 and kind == protocol.wire.EXEC else b'')
            owner.require(len(payload) >= 32 and payload[:-32] == expected, 'failed read contains a caller-selected command')
            wanted = wanted+1 if kind != protocol.DETACH else -1
        offset = end
    return opens


def _failed_state(live, context, path, value):
    handle = raw.load_handle(owner.verify_pin(context.root, value['raw']))
    tx = raw.read_stderr(handle, maximum=65536); rx = raw.read_stdout(handle, maximum=131072)
    context.uncertain_opens += _read_only_tx(context, tx)
    key, _ = live._p328_read_auth_key(context.prepared)
    decoder = context.declared.observer.io_class(context.codec, key, context.declared.IDENTITY, rx=rx, tx=tx)
    try: decoder.handshake()
    except Exception: pass  # Only retain an already parsed nonce; never invent successful preparation.
    if len(decoder.audit.nonce or b'') == 32:
        context.seen.add(health.digest(decoder.audit.nonce))


def context(live, root, previous, *, follow=False):
    """Read a bounded immutable chain; never infer health from a failure tail."""
    path = owner.direct(root, previous); chain = []; seen = set()
    while True:
        value, receipt = owner.read(path)
        owner.require(receipt['sha256'] not in seen and len(chain) < owner.registry.MAX_RECORDS,
                      'observation history is cyclic or exceeds its bounded reader')
        seen.add(receipt['sha256'])
        if value.get('schema') == LEGACY_SCHEMA:
            result = _legacy(live, root, path); break
        if value.get('schema') != SCHEMA:
            owner.require(path.name == 'terminal.json', 'observation anchor is not a native terminal')
            result = _anchor(live, root, path); break
        owner.require(path.name in ('terminal.json', 'stopped.json'), 'observation history record name differs')
        chain.append((path, value, receipt))
        intent, _ = owner.read(owner.verify_pin(root, value['intent']))
        owner.require(intent['schema'] == SCHEMA and intent['kind'] == 'observation-intent', 'observation intent differs')
        path = owner.verify_pin(root, intent['previous'])
    for path, value, receipt in reversed(chain):
        _validate_attempt(live, result, path, value)
        if value['state'] == 'NATIVE_OBSERVED':
            result.last_good = value['proof']; result.seen.add(value['proof']['nonce_sha256']); result.uncertain_opens = 0
        else:
            # Only observed complete OPENs can consume an ordinal. Nonces seen
            # in a failed exchange also remain unavailable to later attempts.
            _failed_state(live, result, path, value)
        result.previous = path
    if not follow:
        owner.require(not os.path.lexists(result.previous.parent/'next-operation.json'),
                      'observation predecessor already has a later owner')
    return result


def _validate_attempt(live, context, path, value):
    owner.core._exact(value, {'schema', 'state', 'intent', 'raw', 'proof', 'close', 'guard_release', 'failure_type'},
                      'native observation result')
    intent_path = owner.verify_pin(context.root, value['intent'])
    owner.require(intent_path == path.parent/'intent.json', 'observation intent path differs')
    intent, intent_pin = owner.read(intent_path)
    owner.core._exact(intent, {'schema', 'kind', 'previous', 'anchor', 'target', 'native_sha256', 'review',
        'purpose', 'seconds', 'started_boottime_ns', 'deadline_boottime_ns', 'host_boot_sha256'}, 'native observation intent')
    owner.require(value['schema'] == SCHEMA and intent['schema'] == SCHEMA and intent['kind'] == 'observation-intent'
                  and value['state'] in ('NATIVE_OBSERVED', 'UNRESOLVED')
                  and value['state'] == ('NATIVE_OBSERVED' if path.name == 'terminal.json' else 'UNRESOLVED')
                  and intent['previous'] == owner.pin(context.previous) and intent['anchor'] == owner.pin(context.anchor)
                  and intent['target'] == context.base['target'] and intent['native_sha256'] == owner.core.json_sha256(context.base['native'])
                  and type(intent['seconds']) is int and 1 <= intent['seconds'] <= MAX_SECONDS
                  and type(intent['started_boottime_ns']) is int and intent['started_boottime_ns'] > 0
                  and intent['deadline_boottime_ns']-intent['started_boottime_ns'] == intent['seconds']*10**9,
                  'native observation chain, target or budget differs')
    successor = owner.read(context.previous.parent/'next-operation.json')[0]
    owner.require(successor == dict(schema=SCHEMA, kind='read-only-observation-successor', operation=intent_pin),
                  'observation is not the registered next owner')
    handle = raw.load_handle(owner.verify_pin(context.root, value['raw']))
    owner.require(handle.receipt_path == path.parent/'raw/wire.capture.json' and not handle.output_exceeded,
                  'observation raw receipt differs')
    rx = raw.read_stdout(handle, maximum=131072); tx = raw.read_stderr(handle, maximum=65536)
    if value['state'] == 'UNRESOLVED':
        owner.require(value['proof'] is None and value['failure_type'] is not None,
                      'failed observation was promoted to health')
        return
    _completed(handle)
    key, key_sha = live._p328_read_auth_key(context.prepared)
    owner.require(key_sha == context.base['native']['auth_key']['sha256'], 'retained observation key differs')
    proof, nrx, ntx = protocol.replay_one(context.codec, context.declared.IDENTITY, key, rx, tx,
                                         io_class=context.declared.observer.io_class)
    owner.require((nrx, ntx) == (len(rx), len(tx)) and proof == value['proof']
                  and proof['ending'] == 'detach' and proof['detach_ack_observed'] is True
                  and value['failure_type'] is None, 'observation raw health/DETACH proof differs')
    _fresh(context, proof)
    close_path = owner.verify_pin(context.root, value['close']); close = owner.read(close_path)[0]
    guard_path = owner.verify_pin(context.root, value['guard_release']); guard = owner.read(guard_path)[0]
    owner.require(close_path == path.parent/'close-result.json' and close['intent'] == intent_pin
                  and close['closed'] is True and close['exclusivity_released'] is True
                  and close['endpoint_identity_sha256'] == context.base['endpoint_identity_sha256']
                  and intent['started_boottime_ns'] <= close['closed_boottime_ns'] < intent['deadline_boottime_ns']
                  and guard_path == path.parent/'candidate-observer-guard-release.json' and guard['released'] is True,
                  'observation descriptor/guard closure is unproved')


def native_tail(live, root, terminal):
    current = context(live, root, terminal, follow=True)
    value, receipt = owner.read(terminal)
    owner.require(value['schema'] == SCHEMA and value['state'] == 'NATIVE_OBSERVED', 'observation tail is not healthy')
    intent = owner.read(owner.verify_pin(root, value['intent']))[0]
    close = owner.read(owner.verify_pin(root, value['close']))[0]
    result = dict(current.base)
    result.update(schema=SCHEMA, state='NATIVE_OBSERVED', observation=receipt,
        proof=dict(sessions=[value['proof']], native_health_proved=True),
        host_boot_sha256=intent['host_boot_sha256'], closed_boottime_ns=close['closed_boottime_ns'],
        seen_nonce_hashes=sorted(current.seen), health_scope='past-authenticated-read-only-snapshot')
    return result


def exact_endpoint(context, descriptor=None):
    entries = sorted(Path('/sys/class/tty').glob('ttyACM*'))
    owner.require(len(entries) <= 16, 'too many tty endpoints')
    rows = [cdc._resolve_endpoint(path) for path in entries]
    matches = [endpoint for _, endpoint in rows if endpoint.identity_sha256 == context.base['endpoint_identity_sha256']]
    owner.require(len(matches) == 1, 'exact native tty absent or ambiguous'); endpoint = matches[0]
    owner.require(str(endpoint.usb_path.resolve()) == context.endpoint['usb_device_path']
        and not [ep for ident, ep in rows if ident['vendor'] == context.spec['usb_vendor_id']
                 and ident['product'] == context.spec['usb_product_id'] and ep.identity_sha256 != endpoint.identity_sha256],
        'native physical binding changed or another candidate-like endpoint is present')
    node = Path('/dev')/endpoint.tty_name; info = node.stat()
    owner.require(stat.S_ISCHR(info.st_mode) and (os.major(info.st_rdev), os.minor(info.st_rdev)) == (endpoint.major, endpoint.minor)
                  and (descriptor is None or os.fstat(descriptor).st_rdev == info.st_rdev), 'native tty node differs')
    return endpoint


def own_descriptor_only(endpoint, directory):
    node = str(Path('/dev')/endpoint.tty_name)
    handle = raw.acquire_command([cdc.PKEXEC, '/usr/bin/fuser', node], directory, 'tty-openers',
                                 timeout=5, stdout_maximum=4096, stderr_maximum=4096)
    _completed(handle)
    stderr = raw.read_stderr(handle, maximum=4096); label = node.encode()+b':'
    owner.require(stderr.startswith(label) and stderr[len(label):].endswith(b'\n')
                  and all(c in b' \t' for c in stderr[len(label):-1]), 'tty opener inventory emitted diagnostics')
    tokens = raw.read_stdout(handle, maximum=4096).split()
    owner.require(tokens and all(token.isdigit() for token in tokens) and {int(token) for token in tokens} == {os.getpid()},
                  'another process owns the native tty')


class Connection:
    def __init__(self, descriptor, endpoint, guarded, directory, intent, context):
        self.descriptor = descriptor; self.endpoint = endpoint; self.guarded = guarded
        self.directory = directory; self.intent = intent
        self.context = context

    def check(self):
        owner.require(self.guarded.guard.healthy() and self.guarded.guard.matches_node(self.endpoint.tty_class),
                      'native observation guard lost')
        exact_endpoint(self.context, self.descriptor)

    def close(self, *, clean):
        if self.descriptor is None: return
        descriptor = self.descriptor; self.descriptor = None
        try:
            if clean: fcntl.ioctl(descriptor, termios.TIOCNXCL)
        finally: os.close(descriptor)
        if clean:
            owner.publish(self.directory/'close-result.json', dict(schema=SCHEMA, intent=self.intent,
                closed=True, exclusivity_released=True, closed_boottime_ns=protocol.host_now_ns(),
                endpoint_identity_sha256=self.endpoint.identity_sha256))


class Backend:
    @contextmanager
    def connection(self, context, directory, intent, budget):
        endpoint = exact_endpoint(context)
        baseline = dict(schema=SCHEMA, exact_candidate_absent=False,
            endpoint_identity_sha256=endpoint.identity_sha256, spec_sha256=cdc.digest(context.spec))
        binding = dict(schema=SCHEMA, intent=intent)
        with cdc._bound_observer_session(context.spec, 'usb:'+endpoint.topology, directory, binding,
                                         baseline=baseline) as guarded:
            owner.require(guarded.guard.matches_node(endpoint.tty_class), 'current ModemManager flags missing')
            budget()
            descriptor = os.open(Path('/dev')/endpoint.tty_name,
                os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC)
            connection = Connection(descriptor, endpoint, guarded, directory, intent, context)
            try:
                fcntl.ioctl(descriptor, termios.TIOCEXCL); guarded._raw_tty(descriptor)
                exact_endpoint(context, descriptor); own_descriptor_only(endpoint, directory); connection.check(); budget()
                yield connection
            finally: connection.close(clean=False)


def observe(live, root, previous, output, *, purpose, seconds=MAX_SECONDS, backend=None):
    """One directly requested/foreground-task fixed read; no automatic retries."""
    import s22plus_native_research_scope_v1 as scope
    root = Path(root).resolve(); output = owner.direct(root, output)
    owner.require(output.is_relative_to(root/BASE) and not os.path.lexists(output)
                  and type(seconds) is int and 1 <= seconds <= MAX_SECONDS
                  and type(purpose) is str and 0 < len(purpose.strip()) <= 2000, 'observation path/purpose/budget differs')
    with owner.registry.target_session_lease(root, research_read_only=True):
        # Read-only success must never be used to steal or release a transfer's
        # owner. Pending F1 still has its independent host observation/recovery.
        owner.registry.require_no_f1_owner(root)
        current = context(live, root, previous)
        review = scope.reviewed(root)
        key, key_sha = live._p328_read_auth_key(current.prepared)
        owner.require(key_sha == current.base['native']['auth_key']['sha256'], 'observation key changed')
        output.mkdir(parents=True, mode=0o700); owner.core._fsync_dir(output.parent)
        start = protocol.host_now_ns(); expiry = start+seconds*10**9; epoch = owner.host_epoch()
        intent = owner.publish(output/'intent.json', dict(schema=SCHEMA, kind='observation-intent',
            previous=owner.pin(current.previous), anchor=owner.pin(current.anchor), target=current.base['target'],
            native_sha256=owner.core.json_sha256(current.base['native']), review=review, purpose=purpose.strip(),
            seconds=seconds, started_boottime_ns=start, deadline_boottime_ns=expiry, host_boot_sha256=epoch))
        owner.publish(current.previous.parent/'next-operation.json',
            dict(schema=SCHEMA, kind='read-only-observation-successor', operation=intent))
        writer = DurableWriter(output/'raw'); io = None; failure = None; proof = None; last = start
        def budget():
            nonlocal last
            now = protocol.host_now_ns()
            owner.require(last <= now < expiry and owner.host_epoch() == epoch,
                          'observation original clock/budget expired')
            last = now
        try:
            with (backend or Backend()).connection(current, output, intent, budget) as connection:
                def before_write():
                    budget(); connection.check()
                before_write()
                remaining = (expiry-protocol.host_now_ns())/1e9
                io = _io_class(current)(current.codec, key, current.declared.IDENTITY,
                    fd=connection.descriptor, writer=writer, deadline=time.monotonic()+remaining-.1,
                    before_write=before_write)
                def before_terminal(request):
                    before_write(); _fresh(current, request)
                    owner.require(request['mode'] == 'detach', 'observation cannot send CONTROL')
                proof = protocol.qualify_one(io, ending='detach', evidence=output/'console',
                                              before_terminal=before_terminal, hud=True)
                before_write()
                ready, _, _ = select.select([connection.descriptor], [], [], .01)
                if ready:
                    part = os.read(connection.descriptor, 1)
                    if part: writer.write_stdout(part)
                    owner.require(not part, 'trailing byte after observation DETACH')
                connection.close(clean=True)
                budget()
        except BaseException as exc: failure = exc
        handle = writer.finish(bytes(io.audit.tx) if io is not None else b'', failure)
        result = dict(schema=SCHEMA, state='NATIVE_OBSERVED' if failure is None else 'UNRESOLVED',
            intent=intent, raw=owner.pin(handle.receipt_path), proof=proof if failure is None else None,
            close=owner.pin(output/'close-result.json') if (output/'close-result.json').exists() else None,
            guard_release=owner.pin(output/'candidate-observer-guard-release.json')
                if (output/'candidate-observer-guard-release.json').exists() else None,
            failure_type=type(failure).__name__ if failure is not None else None)
        # Rederive before publishing a healthy terminal. A parser/reporting
        # failure becomes this attempt's failure, never another device command.
        if failure is None:
            try: _validate_attempt(live, current, output/'terminal.json', result)
            except BaseException as exc:
                failure = exc; result.update(state='UNRESOLVED', proof=None, failure_type=type(exc).__name__)
        name = 'terminal.json' if failure is None else 'stopped.json'
        owner.publish(output/name, result)
        return dict(state=result['state'], result=owner.pin(output/name),
            native_elapsed_ms=proof['baseline_info']['elapsed_ms'] if failure is None else None,
            actual_authentication_ordinal=proof['baseline_info']['authentication_ordinal'] if failure is None else None,
            device_control_requests=0, device_transfers=0, recovery_owner_released=False,
            failure_type=result['failure_type'])


def main(argv=None):
    import device_action_f1_live_v2 as live
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    run = sub.add_parser('observe'); run.add_argument('--previous', type=Path, required=True)
    run.add_argument('--output', type=Path, required=True); run.add_argument('--purpose', required=True)
    run.add_argument('--seconds', type=int, default=MAX_SECONDS)
    read = sub.add_parser('read'); read.add_argument('--terminal', type=Path, required=True)
    args = parser.parse_args(argv)
    result = (observe(live, ROOT, args.previous, args.output, purpose=args.purpose, seconds=args.seconds)
              if args.command == 'observe' else native_tail(live, ROOT, args.terminal))
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == '__main__': main()
