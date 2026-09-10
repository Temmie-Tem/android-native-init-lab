"""Small native-baseline extensions of the existing Samsung observer owner.

The existing guard, measured endpoint, raw writer, strict key reader and Odin
transport remain in the common backend. This module owns only clean native
descriptor transitions and their source-bound records.
"""
import fcntl
import os
from pathlib import Path
import re
import sys
import termios
import time

import device_action_f1_v2 as core
import s22plus_native_baseline_protocol_v1 as protocol
import s22plus_native_baseline_observer_v1 as observer
import s22plus_native_baseline_guard_v1 as guard

SCHEMA = 's22plus-native-baseline-descriptor-v1'


def observer_session(live, prepared, *args, **kwargs):
    return guard.observer_session(live, prepared, *args, **kwargs)


def context(live, prepared):
    value = getattr(prepared, 'native_baseline_context', None)
    if value is None:
        return None
    import s22plus_native_baseline_owner_v1 as owner
    return owner.validate_observation_context(live, prepared)


def mode(live, prepared):
    value = context(live, prepared)
    return value['mode'] if value is not None else 'pair-control'


def _name(prefix, index, suffix):
    return f'{prefix}-native-auth-{index:02d}.{suffix}.json'


class ObserverMixin:
    @property
    def _live(self):
        return sys.modules[type(self).__module__]

    def _baseline_receipt(self, path):
        return self._live._receipt(path, 'native baseline descriptor record')

    def _baseline_publish(self, name, value):
        path = self.run_dir/name
        core._write_exclusive(path, value)
        return self._baseline_receipt(path)

    def _baseline_write_budget(self):
        now = protocol.host_now_ns()
        native_expiry = getattr(self,'baseline_native_expiry_ns',None)
        if now >= self.baseline_observation_expiry_ns or native_expiry is not None and now >= native_expiry:
            raise self._live.F1LiveError('baseline original write budget expired')
        if self.native_baseline_prepared.native_baseline_context is not None:
            import s22plus_native_baseline_owner_v1 as owner
            context=self.native_baseline_prepared.native_baseline_context
            owner.load_operation(self._live,self.native_baseline_prepared.root,context['operation'],active=True)

    def _baseline_before_auth(self, index):
        live = self._live
        if protocol.host_now_ns() >= self.baseline_observation_expiry_ns:
            raise live.F1LiveError('baseline original observation deadline expired')
        if getattr(self.native_baseline_prepared, 'native_baseline_context', None) is not None:
            import s22plus_native_baseline_owner_v1 as owner
            operation = owner.before_native_auth(live, self.native_baseline_prepared)
            if self.native_baseline_prepared.native_baseline_context['phase'] == 'native-start':
                prior = owner.native_terminal(live, operation.root, Path(operation.value['prior_native']['path']).parent)
                self.baseline_native_expiry_ns = prior['native_expiry_boottime_ns']
        known_expiry = getattr(self, 'baseline_native_expiry_ns', None)
        if known_expiry is not None and protocol.host_now_ns() >= known_expiry:
            raise live.F1LiveError('baseline original native lifetime expired before AUTH')
        if self.owned_descriptor is None or not self._endpoint_exact(self.endpoint, self.owned_descriptor):
            raise live.F1LiveError('baseline exact endpoint missing before authentication')
        self.baseline_auth_index = index
        self.baseline_owned_index = index
        value = dict(schema=SCHEMA, kind='authentication', index=index,
            mode=self.baseline_mode, binding=dict(self.base.binding),
            endpoint_identity_sha256=self.endpoint.identity_sha256,
            host_boot_sha256=live.RETURN_HOSTS[self.namespace].host_boot_sha256(),
            observation_expiry_boottime_ns=self.baseline_observation_expiry_ns,
            started_boottime_ns=protocol.host_now_ns())
        self.baseline_auth_record = value
        self.baseline_auth_receipt = self._baseline_publish(_name(self.namespace,index,'intent'),value)

    def _baseline_before_terminal(self, request):
        live = self._live
        info = request['baseline_info']
        expiry = (self.baseline_auth_record['started_boottime_ns']+
                  (protocol.BOOT_LIMIT_MS-info['elapsed_ms'])*10**6)
        previous_expiry = getattr(self, 'baseline_native_expiry_ns', None)
        self.baseline_native_expiry_ns = min(expiry, previous_expiry) if previous_expiry is not None else expiry
        if protocol.host_now_ns() >= min(self.baseline_native_expiry_ns, self.baseline_observation_expiry_ns):
            raise live.F1LiveError('baseline original native lifetime expired')
        if self.owned_descriptor is None or not self._endpoint_exact(self.endpoint, self.owned_descriptor):
            raise live.F1LiveError('baseline exact endpoint differs before terminal request')
        if getattr(self.native_baseline_prepared, 'native_baseline_context', None) is not None:
            import s22plus_native_baseline_owner_v1 as owner
            owner.before_native_terminal(live, self.native_baseline_prepared, request,
                                         self.baseline_auth_index, self.baseline_native_expiry_ns)
        self._baseline_publish(_name(self.namespace,self.baseline_auth_index,'terminal-check'),
            dict(schema=SCHEMA, kind='terminal-check', binding=dict(self.base.binding),
                authentication=self.baseline_auth_receipt, request=request,
                host_boot_sha256=self.baseline_auth_record['host_boot_sha256'],
                created_boottime_ns=protocol.host_now_ns()))

    def _baseline_before_detach(self, request):
        lane = self._live._P345ObserverSession._lane_supplement(self,True)
        if lane.get('accepted_for_p324') is not True:
            raise self._live.F1LiveError('baseline pre-DETACH lane differs')
        value = dict(schema=SCHEMA, kind='detach', binding=dict(self.base.binding),
            request=request, authentication=self.baseline_auth_receipt,
            endpoint_identity_sha256=self.endpoint.identity_sha256,
            host_boot_sha256=self.baseline_auth_record['host_boot_sha256'],
            native_expiry_boottime_ns=self.baseline_native_expiry_ns,
            created_boottime_ns=protocol.host_now_ns())
        self.baseline_detach_receipt = self._baseline_publish(
            _name(self.namespace,self.baseline_auth_index,'detach-intent'),value)
        self.baseline_detach_lane = dict(lane,observation_phase='before-native-detach',
                                         post_control_observation=False)

    def _baseline_close_owned(self, *, reason, row=None):
        """Transfer ownership to None before exactly one close, including errors."""
        live = self._live
        current = self.owned_descriptor
        if current is None:
            return None
        index = getattr(self, 'baseline_owned_index', getattr(self,'baseline_auth_index',0))
        intent = dict(schema=SCHEMA, kind='descriptor-close', reason=reason, index=index,
            binding=dict(self.base.binding), authentication=getattr(self,'baseline_auth_receipt',None),
            detach_intent=getattr(self,'baseline_detach_receipt',None) if row is not None else None,
            rx={k:row['rx'][k] for k in ('size','sha256')} if row is not None else None,
            tx={k:row['tx'][k] for k in ('size','sha256')} if row is not None else None,
            endpoint_identity_sha256=self.endpoint.identity_sha256 if self.endpoint is not None else None,
            host_boot_sha256=live.RETURN_HOSTS[self.namespace].host_boot_sha256(),
            started_boottime_ns=protocol.host_now_ns())
        try:
            intent_receipt = self._baseline_publish(_name(self.namespace,index,'close-intent'),intent)
        except BaseException:
            # A reporting failure must not prevent local descriptor cleanup.
            # Without a close result there is no reattachment/native terminal.
            self.owned_descriptor = None
            try: os.close(current)
            except OSError: pass
            raise
        self.owned_descriptor = None
        error = None
        release_error = None
        if row is not None:
            try:
                fcntl.ioctl(current, termios.TIOCNXCL)
            except OSError as exc:
                release_error = dict(error_type=type(exc).__name__, errno=exc.errno)
                self.descriptor_close_error = type(exc).__name__
        try:
            os.close(current)
        except OSError as exc:
            error = dict(error_type=type(exc).__name__, errno=exc.errno)
            self.descriptor_close_error = type(exc).__name__
        closed = protocol.host_now_ns()
        expiry = getattr(self,'baseline_native_expiry_ns',0)
        value = dict(schema=SCHEMA, kind='descriptor-close-result', intent=intent_receipt,
            status='closed' if error is None and release_error is None else 'close-uncertain', error=error,
            exclusivity_released=row is not None and release_error is None, release_error=release_error,
            completed_boottime_ns=closed, native_expiry_boottime_ns=expiry,
            within_native_lifetime=bool(expiry and closed<expiry))
        receipt = self._baseline_publish(_name(self.namespace,index,'close-result'),value)
        if error is not None or release_error is not None:
            raise live.F1LiveError('native descriptor close is uncertain; no retry')
        return value, receipt

    def _baseline_reopen(self, row, deadline):
        live = self._live
        if (self.baseline_auth_index != 1 or getattr(self,'baseline_reopen_receipt',None) is not None
                or row['ending'] != 'detach' or not row['detach_ack_observed']):
            raise live.F1LiveError('baseline reattachment has no unique clean detach')
        descriptor = self.owned_descriptor
        if descriptor is None or not self._endpoint_exact(self.endpoint,descriptor):
            raise live.F1LiveError('baseline endpoint differs before clean close')
        self.trailing_rx = live._p327_trailing_probe(descriptor,self.baseline_writer)
        if self.trailing_rx:
            raise live.F1LiveError('baseline trailing bytes before reattachment')
        close, close_receipt = self._baseline_close_owned(reason='reattach',row=row)
        if not close['within_native_lifetime'] or time.monotonic()>=deadline:
            raise live.F1LiveError('baseline clean close exhausted original lifetime')
        if not self._endpoint_exact(self.endpoint):
            raise live.F1LiveError('baseline endpoint changed while closed')
        value = dict(schema=SCHEMA, kind='descriptor-reopen', close=close_receipt,
            binding=dict(self.base.binding), endpoint_identity_sha256=self.endpoint.identity_sha256,
            started_boottime_ns=protocol.host_now_ns())
        intent = self._baseline_publish(_name(self.namespace,1,'reopen-intent'),value)
        descriptor = os.open(self.base.dev_root/self.endpoint.tty_name,
            os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK|os.O_CLOEXEC)
        self.owned_descriptor = descriptor
        self.baseline_owned_index = 2
        self.baseline_auth_receipt = None
        self.baseline_detach_receipt = None
        fcntl.ioctl(descriptor,termios.TIOCEXCL)
        if not self._endpoint_exact(self.endpoint,descriptor):
            raise live.F1LiveError('baseline reopened descriptor differs')
        self.base._raw_tty(descriptor)
        if time.monotonic()>=deadline or protocol.host_now_ns()>=min(self.baseline_native_expiry_ns, self.baseline_observation_expiry_ns):
            raise live.F1LiveError('baseline reopening exhausted original lifetime')
        self.baseline_reopen_receipt = self._baseline_publish(_name(self.namespace,1,'reopen-result'),
            dict(schema=SCHEMA, kind='descriptor-reopen-result', intent=intent, status='reopened',
                endpoint_identity_sha256=self.endpoint.identity_sha256, completed_boottime_ns=protocol.host_now_ns()))
        return descriptor

    def _qualify_on_descriptor(self, codec, descriptor, writer, deadline):
        live = self._live
        self._require_control_absent()
        self.baseline_mode = mode(live,self.native_baseline_prepared)
        self.baseline_writer = writer
        self.baseline_auth_index = 0
        self.baseline_owned_index = 1
        self.baseline_detach_receipt = None
        self.baseline_native_expiry_ns = None
        self.baseline_observation_expiry_ns = protocol.host_now_ns()+int(max(0,deadline-time.monotonic())*10**9)
        if (type(self.root_console_plan_value) is not dict
                or type(self.root_console_plan_receipt) is not dict):
            raise live.F1LiveError('baseline sealed empty console plan is missing')
        return self.qualification_observer.qualify(codec,descriptor,self.auth_key,None,set(),writer,
            deadline=deadline, mode=self.baseline_mode,
            evidence=self.run_dir/(self.namespace+'-root-console-evidence'),
            before_auth=self._baseline_before_auth, before_detach=self._baseline_before_detach,
            before_native_terminal=self._baseline_before_terminal, reopen=self._baseline_reopen,
            before_write=self._baseline_write_budget,
            before_control=lambda request:self._seal_control_intent(request,self.owned_descriptor),
            interactive=lambda *_:live.ROOT_CONSOLE_PLAN_OWNERS[self.namespace].validate(self.root_console_plan_value))

    def _baseline_final_close(self):
        row = None
        if self.qualification is not None:
            last = self.qualification.receipt['sessions'][-1]
            if last['ending']=='detach': row=last
        result = self._baseline_close_owned(reason='terminal' if row is not None else 'cleanup',row=row)
        if row is not None:
            self.baseline_native_close_completed = bool(result is not None and result[0]['within_native_lifetime']
                and result[0]['completed_boottime_ns'] < self.baseline_observation_expiry_ns)

    def _baseline_requires_endpoint(self):
        return getattr(self,'baseline_mode','pair-control').endswith('detach')

    def _lane_supplement(self,accepted):
        if self._baseline_requires_endpoint() and getattr(self,'baseline_detach_lane',None) is not None:
            return dict(self.baseline_detach_lane)
        return super()._lane_supplement(accepted)

    def _publish_value(self,value,lane_supplement,*,label):
        live=self._live; error=None
        try:
            payload=live.p318_topology.capture_candidate_raw(phase='candidate_end')
        except (live.p318_topology.TopologyReceiptError,OSError) as exc:
            error=type(exc).__name__
            payload=live.p318_topology.raw_snapshot(phase='candidate_end',capture_complete=False,endpoints=[])
        path=self.run_dir/(self.namespace+'-candidate-end.raw.json')
        receipt=live.p318_topology.publish_raw(path,payload,phase='candidate_end')
        parsed=live.p318_topology.parse_raw_snapshot(payload,phase='candidate_end')
        value[self.namespace+'_closure_snapshot']=dict(path=str(path),**receipt,
            capture_complete=parsed['capture_complete'],error_type=error,
            continuity_proved=False,role='baseline-transport-diagnostic')
        live._P345ObserverSession._publish_value(self,value,lane_supplement,label=label)


def project_observation(session, value, complete):
    proof = session.proof or {}
    selected = getattr(session, 'baseline_mode', 'pair-control')
    count = observer.mode_sessions(selected)
    detached = selected.endswith('detach')
    close_ok = getattr(session, 'baseline_native_close_completed', False)
    value.update(same_tty_fd=complete and count == 1,
        framed_session_closed=complete and detached,
        physical_reopen_count=1 if getattr(session, 'baseline_reopen_receipt', None) is not None else 0,
        expected_size=len(session.auth_runtime.DEVICE_BANNER)*count,
        control_requested_mode='none' if detached else 'download',
        native_descriptor_close_completed=bool(close_ok))
    if value['accepted'] and (value.get('descriptor_close_error') is not None or detached and not close_ok):
        value.update(accepted=False, classification='authenticated-session-error',
            qualification_complete=False, pid1_framed_exec_proof=False,
            busybox_ash_command_proof=False, root_console=False, framed_session_closed=False,
            protocol_error='baseline-descriptor-release-unproved')


def validate_detached_plan(live, prepared, value, proof):
    prefix = live._shell_definition(prepared.bundle).prefix
    lane = value['lane']
    if (lane.get('observation_phase') != 'before-native-detach'
            or lane.get('post_control_observation') is not False
            or value.get(prefix+'_control_intent') is not None
            or (prepared.run_dir/live.RETURN_HOSTS[prefix].INTENT_NAME).exists()):
        raise live.F1LiveError('native DETACH is not a Download CONTROL')
    plan_owner = live.ROOT_CONSOLE_PLAN_OWNERS[prefix]
    plan, receipt = plan_owner.seal(prepared.run_dir/plan_owner.SEALED_NAME, prepared.run_dir)
    execution = plan_owner.execution_projection(plan, live._root_operator_plan_rows(prefix, proof))
    if (value.get(prefix+'_console_plan') != receipt or value.get('caller_selected_command') is not False
            or value.get(prefix+'_plan_execution') != execution):
        raise live.F1LiveError('baseline sealed empty plan differs')


def proof_ok(value,variant):
    proof=value.get('proof',value.get(variant.proof_key))
    if type(proof) is not dict: return False
    count=observer.mode_sessions(proof.get('mode'))
    detached=proof['mode'].endswith('detach')
    return (all(value.get(key) is True for key in ('qualification_complete','pid1_framed_exec_proof',
                'busybox_ash_command_proof','root_console'))
        and value.get('same_tty_fd') is (count==1)
        and type(value.get('session_count')) is int and value['session_count']==count
        and type(value.get('command_count')) is int and type(value.get('request_count')) is int
        and value.get('command_count')==proof.get('command_count')
        and value.get('request_count')==proof.get('request_count')
        and type(value.get('physical_reopen_count')) is int and value['physical_reopen_count']==count-1
        and value.get('framed_session_closed') is detached
        and value.get('control_acceptance_observed') is (not detached)
        and value.get('control_requested_mode')==('none' if detached else 'download')
        and value.get('descriptor_close_error') is None
        and value.get('later_action_lease_active') is False and value.get('caller_selected_command') is False
        and type(value.get('root_uid')) is int and value['root_uid']==0
        and type(value.get('root_gid')) is int and value['root_gid']==0
        and value.get('proof_scope')==variant.observer.PROOF_SCOPE
        and value.get('control_ack_scope')=='acceptance-only'
        and value.get('software_download_arrival')=='UNPROVED'
        and type(value.get(variant.prefix+'_console_plan')) is dict
        and type(value.get(variant.prefix+'_plan_execution')) is dict
        and value[variant.prefix+'_plan_execution'].get('all_planned_terminal') is True
        and type(value.get(variant.prefix+'_closure_snapshot')) is dict
        and (not detached or value.get('native_descriptor_close_completed') is True))


def validate_observer_ownership(live,prepared,value,proof):
    """Reopen physical close/reopen records against already authenticated raw."""
    prefix=live._shell_definition(prepared.bundle).prefix
    selected=mode(live,prepared)
    if value.get('accepted') is not True:
        # Partial raw/intent evidence is retained. It never admits another AUTH.
        return False
    if proof['mode']!=selected:
        raise live.F1LiveError('baseline observer mode differs from its owner')
    binding=live._candidate_observer_binding(prepared)
    endpoint=value['endpoint_identity_sha256']
    keys = {
        'intent': {'schema','kind','index','mode','binding','endpoint_identity_sha256','host_boot_sha256',
                   'started_boottime_ns','observation_expiry_boottime_ns'},
        'terminal-check': {'schema','kind','binding','authentication','request','host_boot_sha256','created_boottime_ns'},
        'detach-intent': {'schema','kind','binding','request','authentication','endpoint_identity_sha256',
                          'host_boot_sha256','native_expiry_boottime_ns','created_boottime_ns'},
        'close-intent': {'schema','kind','reason','index','binding','authentication','detach_intent','rx','tx',
                         'endpoint_identity_sha256','host_boot_sha256','started_boottime_ns'},
        'close-result': {'schema','kind','intent','status','error','exclusivity_released','release_error',
                         'completed_boottime_ns','native_expiry_boottime_ns','within_native_lifetime'},
        'reopen-intent': {'schema','kind','close','binding','endpoint_identity_sha256','started_boottime_ns'},
        'reopen-result': {'schema','kind','intent','status','endpoint_identity_sha256','completed_boottime_ns'},
    }
    kinds = dict(intent='authentication', **{'terminal-check':'terminal-check','detach-intent':'detach','close-intent':'descriptor-close',
        'close-result':'descriptor-close-result','reopen-intent':'descriptor-reopen',
        'reopen-result':'descriptor-reopen-result'})
    read_names = set()
    def read(index,suffix):
        path=prepared.run_dir/_name(prefix,index,suffix)
        record = live._read_json(path,'baseline descriptor record')
        if (set(record) != keys[suffix] or record['schema'] != SCHEMA or record['kind'] != kinds[suffix]
                or any(type(record[k]) is not int or record[k] <= 0 for k in record if k.endswith('_ns'))
                or 'host_boot_sha256' in record and (type(record['host_boot_sha256']) is not str
                    or re.fullmatch('[0-9a-f]{64}', record['host_boot_sha256']) is None)):
            raise live.F1LiveError('baseline descriptor record fields differ')
        read_names.add(path.name)
        return record,live._receipt(path,'baseline descriptor record')
    expiries=[]; epoch=None; previous_reopen=None; observation_expiry=None
    for index,row in enumerate(proof['sessions'],1):
        auth,auth_receipt=read(index,'intent')
        expected=keys['intent']
        if (set(auth)!=expected or auth['schema']!=SCHEMA or auth['kind']!='authentication'
                or auth['index']!=index or type(auth['index']) is not int or auth['mode']!=selected
                or auth['binding']!=binding or auth['endpoint_identity_sha256']!=endpoint
                or type(auth['started_boottime_ns']) is not int or auth['started_boottime_ns']<=0):
            raise live.F1LiveError('baseline authentication owner differs')
        if epoch is None: epoch=auth['host_boot_sha256']
        if observation_expiry is None: observation_expiry=auth['observation_expiry_boottime_ns']
        if (auth['host_boot_sha256'] != epoch or previous_reopen is not None
                and auth['started_boottime_ns'] < previous_reopen
                or auth['observation_expiry_boottime_ns'] != observation_expiry
                or not auth['started_boottime_ns'] < observation_expiry <= auth['started_boottime_ns']+60*10**9):
            raise live.F1LiveError('baseline authentication epoch/order differs')
        expiry=auth['started_boottime_ns']+(protocol.BOOT_LIMIT_MS-row['baseline_info']['elapsed_ms'])*10**6
        if expiries: expiry=min(expiry,expiries[-1])
        if prepared.native_baseline_context is not None and prepared.native_baseline_context['phase']=='native-start':
            import s22plus_native_baseline_owner_v1 as owner
            operation=owner.load_operation(live,prepared.root,prepared.native_parent)
            prior=owner.native_terminal(live,prepared.root,Path(operation.value['prior_native']['path']).parent)
            expiry=min(expiry,prior['native_expiry_boottime_ns'])
        expiries.append(expiry)
        terminal,_=read(index,'terminal-check')
        request=dict(run_id_hex=row['run_id_hex'],mode='detach' if row['ending']=='detach' else 'download',
            sequence=row['terminal_sequence'],nonce_sha256=row['nonce_sha256'],
            kernel_boot_identity_sha256=row['kernel_boot_identity_sha256'],baseline_info=row['baseline_info'])
        if (terminal['binding'] != binding or terminal['authentication'] != auth_receipt
                or terminal['host_boot_sha256'] != epoch or not live._p319_exact_equal(terminal['request'],request)
                or not auth['started_boottime_ns'] <= terminal['created_boottime_ns'] < min(expiry,observation_expiry)):
            raise live.F1LiveError('baseline terminal original clock/raw binding differs')
        if row['ending']=='detach':
            detach,detach_receipt=read(index,'detach-intent')
            request=dict(run_id_hex=row['run_id_hex'],mode='detach',sequence=row['terminal_sequence'],
                nonce_sha256=row['nonce_sha256'],kernel_boot_identity_sha256=row['kernel_boot_identity_sha256'],
                baseline_info=row['baseline_info'])
            if (detach.get('schema')!=SCHEMA or detach.get('kind')!='detach'
                    or detach.get('binding')!=binding or detach.get('authentication')!=auth_receipt
                    or not live._p319_exact_equal(detach.get('request'),request)
                    or detach.get('endpoint_identity_sha256')!=endpoint
                    or detach.get('host_boot_sha256')!=auth['host_boot_sha256']
                    or detach.get('native_expiry_boottime_ns')!=expiry
                    or not terminal['created_boottime_ns'] <= detach['created_boottime_ns'] < min(expiry,observation_expiry)):
                raise live.F1LiveError('baseline DETACH raw/owner binding differs')
            close,close_intent=read(index,'close-intent');done,close_result=read(index,'close-result')
            if (close.get('schema')!=SCHEMA or close.get('kind')!='descriptor-close'
                    or close.get('reason')!=('reattach' if index<len(proof['sessions']) else 'terminal')
                    or close.get('binding')!=binding or close.get('authentication')!=auth_receipt
                    or close.get('detach_intent')!=detach_receipt or close.get('index')!=index
                    or type(close['index']) is not int or close['endpoint_identity_sha256'] != endpoint
                    or close['host_boot_sha256'] != epoch
                    or close.get('rx')!={k:row['rx'][k] for k in ('size','sha256')}
                    or close.get('tx')!={k:row['tx'][k] for k in ('size','sha256')}
                    or done.get('schema')!=SCHEMA or done.get('intent')!=close_intent
                    or done.get('status')!='closed' or done.get('error') is not None
                    or done.get('exclusivity_released') is not True or done.get('release_error') is not None
                    or done.get('native_expiry_boottime_ns')!=expiry
                    or done.get('within_native_lifetime') is not True
                    or type(done.get('completed_boottime_ns')) is not int
                    or not detach['created_boottime_ns']<=close['started_boottime_ns']<=done['completed_boottime_ns']<min(expiry,observation_expiry)):
                raise live.F1LiveError('baseline clean descriptor close is unproved')
            if index<len(proof['sessions']):
                opened,open_intent=read(index,'reopen-intent');ready,_=read(index,'reopen-result')
                if (opened.get('schema')!=SCHEMA or opened.get('close')!=close_result
                        or opened.get('binding')!=binding or opened.get('endpoint_identity_sha256')!=endpoint
                        or ready.get('schema')!=SCHEMA or ready.get('intent')!=open_intent
                        or ready.get('status')!='reopened' or ready.get('endpoint_identity_sha256')!=endpoint
                        or type(ready.get('completed_boottime_ns')) is not int
                        or not done['completed_boottime_ns']<=opened['started_boottime_ns']<=ready['completed_boottime_ns']<expiry):
                    raise live.F1LiveError('baseline exact descriptor reattachment is unproved')
                previous_reopen = ready['completed_boottime_ns']
        else:
            close, close_intent = read(index,'close-intent'); done,_ = read(index,'close-result')
            if (close['binding'] != binding or close['authentication'] != auth_receipt
                    or close['reason'] != 'cleanup' or type(close['index']) is not int or close['index'] != index
                    or close['detach_intent'] is not None or close['rx'] is not None or close['tx'] is not None
                    or close['host_boot_sha256'] != epoch or close['endpoint_identity_sha256'] != endpoint
                    or done['intent'] != close_intent or done['status'] != 'closed'
                    or done['error'] is not None or done['release_error'] is not None
                    or done['exclusivity_released'] is not False
                    or done['native_expiry_boottime_ns'] != expiry
                    or done['within_native_lifetime'] is not (done['completed_boottime_ns'] < expiry)
                    or not auth['started_boottime_ns'] <= close['started_boottime_ns'] <= done['completed_boottime_ns']):
                raise live.F1LiveError('baseline CONTROL descriptor cleanup differs')
    if {path.name for path in prepared.run_dir.glob(prefix+'-native-auth-*.json')} != read_names:
        raise live.F1LiveError('baseline unexpected authentication owner record')
    return True
