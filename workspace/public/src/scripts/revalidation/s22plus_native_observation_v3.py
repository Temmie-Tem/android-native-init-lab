"""One fixed native health session over an owner-supplied exact host binding."""
from pathlib import Path
import re
import time
from types import SimpleNamespace

import device_action_raw_capture_v1 as raw
import s22plus_native_baseline_protocol_v1 as protocol
import s22plus_native_thermal_observer_v3 as thermal
import s22plus_native_storage_census_v1 as storage
import s22plus_native_gpt_profile_v1 as gpt
import s22plus_root_console_v1 as console
import s22plus_native_target_io_v3 as target_io
from s22plus_native_wire_v3 import Codec
from s22plus_native_records_v3 import SessionError, clock, digest, pin, publish, read, read_bytes, require, verify


class NativeClosePublicationError(SessionError):
    protocol_completed=True


class IO(thermal.IO):
    @staticmethod
    def decode_hud(value, run_id):
        try:
            return dict(status='OBSERVED',value=thermal.IO.decode_hud(value,run_id))
        except (ValueError,KeyError,TypeError) as error:
            # This collector's bytes are optional research data. Complete fixed
            # health and a completed command remain independently verifiable.
            return dict(status='NO_PROOF_OPTIONAL_HUD',error_type=type(error).__name__,
                size=len(value),sha256=digest(value))


class StorageIO(IO):
    EXTRA_PROFILE = storage
    SOURCE_PROFILE = storage.SCHEMA


def io_class(profile, image=None):
    if profile in gpt.SELECTIONS:
        require(image is not None,'GPT observation has no bound image')
        class GptIO(IO):
            EXTRA_PROFILE=gpt.Profile(image,profile)
            SOURCE_PROFILE=dict(schema=gpt.SCHEMA,selection=profile,
                proposal_sha256=image['gpt']['proposal']['sha256'])
        return GptIO
    require(profile in ('health','storage-census'), 'unknown native observation profile')
    return StorageIO if profile == 'storage-census' else IO


class TransmittedBytes(bytearray):
    def __init__(self, writer):
        super().__init__(); self.writer=writer

    def extend(self, value):
        self.writer.write_stderr(value)
        super().extend(value)


def identity(image):
    require(re.fullmatch('p[0-9]{3,6}',image['namespace'])
        and re.fullmatch('[0-9a-f]{32}',image['run_id_hex']),'native image wire identity differs')
    return SimpleNamespace(namespace=image['namespace'],run_id_hex=image['run_id_hex'])


def key_bytes(image):
    path=verify(image['key'],maximum=32)
    value=read_bytes(path,maximum=32); require(len(value)==32,'native authentication key differs')
    return value


def check_freshness(io, *, previous=None, first_boot=False, seen_nonces=(), seen_boots=()):
    current=dict(run_id_hex=io.identity.run_id_hex,
        kernel_boot_identity_sha256=digest(io.audit.boot_id),nonce_sha256=digest(io.audit.nonce),
        baseline_info=io.preparation.info)
    require(current['nonce_sha256'] not in seen_nonces,'native nonce was already used')
    if first_boot:
        require(previous is None and current['baseline_info']['authentication_ordinal']==1
            and current['kernel_boot_identity_sha256'] not in seen_boots,
            'new installation did not prove a fresh first native boot')
    else:
        require(previous is not None,'native reentry has no previous closed authenticated tail')
        protocol.fresh_same_boot(previous,current,seen_nonce_hashes=seen_nonces)


def rederive(directory, image, *, ending, hud, previous=None, first_boot=False,
             seen_nonces=(), seen_boots=(), require_close=True, profile='health'):
    require(profile=='health' or ending=='detach' and hud is False,
        'storage census replay may not change mode or collect HUD')
    directory=Path(directory)
    close=read(directory/'close.json')
    require(close['open']==pin(directory/'open.json'),'native descriptor close belongs to a different open')
    opened=read(directory/'open.json')
    require(all(close[key]==opened[key] for key in ('image','ending','hud'))
        and {key:value for key,value in close['acquisition'].items() if key!='close'}
            =={key:value for key,value in opened['acquisition'].items() if key!='close'},
        'native acquisition changed across actual descriptor close')
    reconstructed={key:value for key,value in close.items() if key!='open'}
    reconstructed.update(raw=pin(directory/'session.capture.json'),closure=pin(directory/'close.json'))
    attempt_path=directory/'attempt.json'
    attempt=read(attempt_path) if attempt_path.exists() else reconstructed
    require(attempt==reconstructed,'native aggregate differs from independent close and raw records')
    require(attempt['schema']=='s22plus-native-observation-v3' and attempt['image']==image
        and attempt['ending']==ending and attempt['hud']==hud,'native observation context differs')
    require(opened.get('profile','health') == close.get('profile','health')
        == attempt.get('profile','health') == profile, 'native observation profile changed')
    selected_io=io_class(profile,image)
    handle=raw.load_handle(verify(attempt['raw']))
    # The two direct-source streams are RX and TX, not command stdout/stderr.
    # Preserve every producer-completion check without rejecting valid TX.
    require(handle.returncode==0 and not handle.timed_out and not handle.output_exceeded
        and handle.producer_error_type is None,'native raw producer did not complete')
    rx=raw.read_stdout(handle,maximum=console.RAW_CAPTURE_MAXIMUM)
    tx=raw.read_stderr(handle,maximum=65536)
    bound=identity(image); key=key_bytes(image); codec=Codec(bound.namespace)
    proof,rend,tend=protocol.replay_one(codec,bound,key,rx,tx,io_class=selected_io)
    require((rend,tend)==(len(rx),len(tx)) and proof['native_health_proved'] is True
        and proof['ending']==ending and (not proof['hud_requested'] or hud),
        'native fixed profile or complete raw boundary differs')
    io=selected_io(codec,key,bound,rx=rx,tx=tx); io.handshake()
    check_freshness(io,previous=previous,first_boot=first_boot,seen_nonces=seen_nonces,seen_boots=seen_boots)
    if require_close:
        close=attempt['acquisition']['close']
        require(close['descriptor_closed'] is True and (ending!='detach' or close['exclusive_release_errno'] is None),
            'native descriptor/exclusive close is unproved')
    if not attempt_path.exists(): publish(attempt_path,attempt)
    return dict(proof=proof,attempt=pin(attempt_path))


def observe(directory, image, host, *, ending, hud, guard, before_terminal,
            previous=None, first_boot=False, seen_nonces=(), seen_boots=(), before_auth=None,
            profile='health',before_extra=None):
    require(ending in ('detach','download') and type(hud) is bool,'native observation selection differs')
    selected_io=io_class(profile,image)
    if profile in gpt.SELECTIONS and selected_io.EXTRA_PROFILE.MUTATES:
        require(callable(before_extra),'GPT mutation has no durable owner callback')
    require(profile=='health' or ending=='detach' and hud is False,
        'storage census may not change mode or collect HUD')
    extra_fields={} if profile=='health' else dict(profile=profile)
    directory=Path(directory); directory.mkdir(mode=0o700)
    bound=identity(image); key=key_bytes(image); codec=Codec(bound.namespace)
    guard()
    writer=raw.RawCaptureWriter(directory,'session',stdout_maximum=console.RAW_CAPTURE_MAXIMUM,
        stderr_maximum=65536,stdout_name='rx.bin',stderr_name='tx.bin',argv0_name='fixed-native-session-v3')
    io=None; acquisition=None; proof=None; error=None; before=None; departure_deadline=None
    try:
        with host.open_native(bound.run_id_hex,before_open=guard) as (fd,acquisition):
            observation_deadline_ns=clock()+59_900_000_000
            publish(directory/'open.json',dict(image=image,ending=ending,hud=hud,
                acquisition=acquisition,boottime_ns=clock(),deadline_ns=observation_deadline_ns,**extra_fields))
            def native_guard():
                guard()
                if clock()>=observation_deadline_ns: raise TimeoutError('original native BOOTTIME window expired')
            io=selected_io(codec,key,bound,fd=fd,writer=writer,deadline=observation_deadline_ns/1e9,
                clock=lambda:clock()/1e9,before_write=native_guard)
            io.audit.tx=TransmittedBytes(writer)
            if before_auth is not None: before_auth()
            def terminal(request):
                nonlocal before,departure_deadline
                guard()
                check_freshness(io,previous=previous,first_boot=first_boot,
                    seen_nonces=seen_nonces,seen_boots=seen_boots)
                if ending=='download':
                    before=target_io.usb_snapshot('usb:'+host.config['topology'],directory)
                    publish(directory/'departure-before.json',before)
                    departure_deadline=clock()+30_000_000_000
                    before_terminal(dict(request=request,departure=pin(directory/'departure-before.json'),
                        departure_deadline_ns=departure_deadline))
                else:
                    before_terminal()
            def extra(request):
                guard()
                check_freshness(io,previous=previous,first_boot=first_boot,
                    seen_nonces=seen_nonces,seen_boots=seen_boots)
                if before_extra is not None: before_extra(request)
            proof=protocol.qualify_one(io,ending=ending,evidence=directory/'console',
                before_terminal=terminal,hud=hud,before_extra=extra)
    except BaseException as caught:
        error=caught
    finally:
        closed=dict(schema='s22plus-native-observation-v3',image=image,
            ending=ending,hud=hud,acquisition=acquisition,
            stage=io.audit.current_stage if io else 'before-open',error_type=type(error).__name__ if error else None,
            **extra_fields)
        close_error=None
        try:
            if acquisition is not None and (directory/'open.json').exists():
                publish(directory/'close.json',dict(closed,open=pin(directory/'open.json')))
        except Exception as caught: close_error=caught
        try:
            handle=writer.finalize(returncode=0 if proof is not None else None,
                timed_out=isinstance(error,TimeoutError),producer_error_type=type(error).__name__ if error else None)
            if close_error is not None: raise close_error
            publish(directory/'attempt.json',dict(closed,raw=pin(handle.receipt_path),
                closure=pin(directory/'close.json') if (directory/'close.json').exists() else None))
        except Exception as publication_error:
            if proof is not None and ending=='detach':
                raise NativeClosePublicationError('completed native DETACH needs H0 evidence publication') from publication_error
            raise
    if error is not None: raise error
    result=rederive(directory,image,ending=ending,hud=hud,previous=previous,first_boot=first_boot,
        seen_nonces=seen_nonces,seen_boots=seen_boots,profile=profile)
    if ending=='download':
        departure=target_io.wait_departure(before,directory,deadline_ns=departure_deadline,guard=guard)
        publish(directory/'departure.json',departure)
        result['departure']=pin(directory/'departure.json')
    return result
