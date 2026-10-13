"""Declared ARM64-virt-only failure injection into copies of real producers."""
from pathlib import Path
import json

NAMES=('begin-log','done-log','ram-sync','kernel-readback','worker-exit','worker-signal',
    'pending','late-return','parent-death','lost-diagnostic','unstable','interrupted')


def source(out,original,fault):
    if fault not in NAMES:raise ValueError('unknown diagnostic fault')
    folder=out/'diagnostic-fault';folder.mkdir(exist_ok=True)
    base=Path(original).parent
    for name in ('file-first-prepare.c','integrated-prepare.c','fyg8-prepare.c','failure-observer.h','failure-state.h'):
        (folder/name).write_bytes((base/name).read_bytes())
    def change(name,old,new):
        path=folder/name;text=path.read_text()
        if text.count(old)!=1:raise ValueError('diagnostic fixture anchor differs: '+name)
        path.write_text(text.replace(old,new))
    if fault in ('begin-log','done-log'):
        marker='MODULE_BEGIN ordinal=1 ' if fault=='begin-log' else 'MODULE_DONE ordinal=1 '
        change('fyg8-prepare.c','ssize_t written=write(events,line,(size_t)n);',
            'ssize_t written; if(memmem(line,(size_t)n,'+json.dumps(marker)+','+str(len(marker))+')) {errno=EIO;written=-1;} else written=write(events,line,(size_t)n);')
    elif fault=='ram-sync':
        change('fyg8-prepare.c','error=fsync(events)?fs1_error():0;',
            'error=sequence==3?EIO:fsync(events)?fs1_error():0;')
    elif fault=='kernel-readback':
        change('fyg8-prepare.c','error=usb_retained(sequence,line,(size_t)n);',
            'error=sequence==4?ETIMEDOUT:usb_retained(sequence,line,(size_t)n);')
    elif fault=='lost-diagnostic':
        change('failure-observer.h','return checked_kmsg(line,n);','(void)line;return EIO;')
    elif fault in ('pending','late-return'):
        change('failure-observer.h','fo_parent=getpid();fo_phase(FO_START);',
            'fo_deadline=fo_now()+1200;fo_parent=getpid();fo_phase(FO_START);')
        delay='for(;;)pause();' if fault=='pending' else 'struct timespec stalled={2,0};if(nanosleep(&stalled,NULL))_exit(118);'
        change('fyg8-prepare.c','(void)fd; (void)parameters;',
            '(void)fd; (void)parameters;\n    if(!fake_insertions){'+delay+'}')
    elif fault in ('worker-exit','worker-signal','unstable','parent-death'):
        action={'worker-exit':'_exit(77);','worker-signal':'raise(SIGTERM);_exit(119);',
            'unstable':'atomic_fetch_add(&fo_state->generation,1);raise(SIGTERM);_exit(119);',
            'parent-death':'kill(getppid(),SIGKILL);struct timespec delay={1,0};(void)nanosleep(&delay,NULL);_exit(119);'}[fault]
        change('fyg8-prepare.c','(void)fd; (void)parameters;',
            '(void)fd; (void)parameters;\n    if(!fake_insertions){'+action+'}')
    elif fault=='interrupted':
        # Actual EINTR in the observer while its real worker continues.
        change('failure-observer.h','static void fo_park(void)',
            'static void fixture_signal(int sig){(void)sig;}\nstatic void fo_park(void)')
        change('failure-observer.h','pid_t worker=fork();',
            'struct sigaction sa={0};sa.sa_handler=fixture_signal;sigaction(SIGALRM,&sa,NULL);ualarm(1000,1000);\n    pid_t worker=fork();')
    wrapper=folder/'fixture.c'
    wrapper.write_text('#if !defined(FYG8_VM_TEST) || !defined(S22_FAILURE_OBSERVER)\n#error "VM-only diagnostic fault"\n#endif\n#include "file-first-prepare.c"\n')
    return wrapper
