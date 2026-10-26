"""One automatic N lifetime, fixed shutdown, attended original-A return."""
from device_action_raw_capture_v1 import RawCaptureError
from s22plus_native_records_v3 import pin,read,require,verify
from s22plus_debian_handoff_session_v1 import Coordinator as PhysicalCoordinator,intents,validate_task
from s22plus_debian_autoboot_access_v1 import Access


def normal_steps():
    from s22plus_native_session_v3 import Step
    return (Step('android-download','download','A'),Step('install-native-first','transfer','N'),
        Step('debian-health','debian-health','N'),Step('debian-shutdown','debian-shutdown','N'),
        Step('install-android','transfer','A'),Step('android-final','health','A'))


def validate_result(adapter,step,value,request):
    from s22plus_debian_access_v1 import access_for
    selected=access_for(adapter,request,step.name)
    if step.action=='debian-health':require(value==selected.rederive_health(),'automatic health differs')
    elif step.action in ('debian-shutdown','debian-reboot'):
        expected=selected.rederive_shutdown() if step.action=='debian-shutdown' else selected.rederive_control('reboot')
        require(value==expected,'automatic control differs')
        rows=intents(adapter,step.name)
        require(len(rows)==1 and rows[0]['detail']==read(adapter.folder(step.name)/'intent.json'),'automatic shutdown intent differs')


def terminal(adapter,request,*,recovered):
    from s22plus_debian_reboot_access_v1 import selected as reboot_selected
    if reboot_selected(request):return reboot_terminal(adapter,request,recovered=recovered)
    result=dict(status='NO_PROOF',debian_early_pid1=False,debian_boot_proved=False,debian_runtime_proved=False,
        ssh_access_proved=False,clean_shutdown_proved=False,normal_return=not recovered,replay_authorized=False)
    try:
        selected=Access(adapter,request);evidence=selected.evidence()
        result.update(status='PASS_AUTOMATIC_DEBIAN_RUNTIME_120S',debian_early_pid1=True,
            debian_boot_proved=True,debian_runtime_proved=True,observation=evidence['proof'])
        health=selected.rederive_health()
        result.update(status='PASS_DEBIAN_AUTOMATIC_INITIAL_PID1_TO_SSH',ssh_access_proved=True,ssh_health=health['health'])
    except (ValueError,OSError,KeyError,RawCaptureError) as error:
        result['evidence_error']=dict(type=type(error).__name__,message=str(error)[:256])
    return result


class Coordinator(PhysicalCoordinator):
    def execute(self,*,attended):
        from s22plus_debian_apt_access_v1 import selected as apt_selected
        try:return super().execute(attended=attended)
        finally:
            # Shared-network retirement cannot precede or delay automatic A.
            if apt_selected(self.session.request) and any(row['event']=='step-complete' and
                row['data']['step']=='install-android' for row in self.session.rows()):self.cleanup()

    def steps(self):
        from s22plus_native_session_v3 import operation_steps
        return operation_steps(self.session.request)

    def prepare_automatic_return(self):
        from s22plus_debian_reboot_access_v1 import download_selected,return_request
        if not download_selected(self.session.request):return False
        return_request(self.session.adapter,self.session.request,create=True)
        return True


def reboot_terminal(adapter,request,*,recovered):
    from s22plus_debian_reboot_access_v1 import Access as RebootAccess,download_selected,return_request
    result=dict(status='NO_PROOF',boots=[],ordinary_reboot_proved=False,ssh_access_proved=False,
        first_post_reboot_root_clean=False,clean_final_shutdown_proved=False,
        normal_return=not recovered,replay_authorized=False)
    if download_selected(request):result['automatic_download_return_proved']=False
    for phase in (1,2):
        try:
            selected=RebootAccess(adapter,request,phase=phase)
            evidence=selected.evidence();health=selected.rederive_health()
            result['boots'].append(dict(phase=phase,observation=evidence['proof'],ssh_health=health,
                status='PASS_DEBIAN_AUTOMATIC_INITIAL_PID1_TO_SSH'))
            if 'package' in evidence['proof']:
                package=evidence['proof']['package']
                result.update(package_installation_proved=package['installation_proved'],
                    package_function_proved=package['function_proved'],
                    package_exact_reboot_retention_proved=package['exact_reboot_retention_proved'])
                from s22plus_debian_apt_access_v1 import selected as apt_selected
                if apt_selected(request):result['package_manager_network_proved']=package['package_manager_network_proved']
            if phase==1:result['status']='PASS_FIRST_BOOT_SSH'
            else:
                selected.basis()
                require(result['boots'][0]['ssh_health']['health']['boot_count']+1==health['health']['boot_count'],
                    'installed boot count did not advance exactly once')
                result.update(status='PASS_TWO_DEBIAN_BOOTS_SSH',ordinary_reboot_proved=True,
                    ssh_access_proved=True,first_post_reboot_root_clean=True)
                if 'cron_configuration' in evidence['proof']:
                    first=result['boots'][0]['observation']['cron_configuration'];second=evidence['proof']['cron_configuration']
                    require(first['created']==second['created'] and
                        first['configuration_sha256']==second['configuration_sha256'] and
                        second['configuration_consumed'] is True and second['configuration_retired'] is True,
                        'configuration creation, consumption and retirement do not join')
                    result.update(cron_workload_proved=True,cron_configuration_preserved=True,
                        cron_configuration_consumed=True,cron_configuration_retired=True,
                        configuration_retained_after_experiment=False)
                    if 'package' not in evidence['proof']:result['package_installation_proved']=False
                elif 'cron' in evidence['proof']:
                    require(result['boots'][0]['observation']['cron']==evidence['proof']['cron'],
                        'cron proof changed across the ordinary reboot')
                    result.update(cron_workload_proved=True,cron_exact_retention_proved=True,
                        persistent_configuration_proved=False,package_installation_proved=False)
        except (ValueError,OSError,KeyError,RawCaptureError) as error:
            result['evidence_error']=dict(phase=phase,type=type(error).__name__,message=str(error)[:256]);break
    # A completed normal A followed by health-only recovery retains the same
    # automatic Download proof. A physical recover-android transfer cannot
    # satisfy this original install-android evidence join.
    if download_selected(request) and result['ssh_access_proved']:
        try:
            from s22plus_native_session_v3 import Step
            ready=return_request(adapter,request)
            returned=adapter.recover_transfer_result(Step('install-android','transfer','A'),request)
            launch=read(verify(returned['launch']))
            require(launch['arrival_deadline_ns']==ready['deadline_ns'] and
                ready['requested_ns']<launch['boottime_ns']<ready['deadline_ns'] and
                launch['ticket'] and launch['revalidation'] and returned['completed'] is True,
                'automatic Download/A does not join the original final intent')
            result.update(status='PASS_TWO_DEBIAN_BOOTS_AUTOMATIC_DOWNLOAD_A_RETURN',
                automatic_download_return_proved=True,download_return=pin(adapter.directory/'debian-return-ready.json'),
                original_A_return=returned)
        except (ValueError,OSError,KeyError,RawCaptureError) as error:
            result['download_error']=dict(type=type(error).__name__,message=str(error)[:256])
    return result
