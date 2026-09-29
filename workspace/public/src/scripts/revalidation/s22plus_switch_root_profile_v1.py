"""Readonly host-PID1 transition scope, separate from Debian init execution."""
import s22plus_native_root_inspect_profile_v1 as inspection
import s22plus_native_staged_preflight_profile_v1 as staged
from s22plus_native_records_v3 import require,verify

ROOT=inspection.ROOT
SCHEMA='s22plus-switch-root-v1'
PROFILE='thermal-v3-reconnect-ufs-drain-switch-root-v1'
OPERATION=SELECTION='switch-root'
prior_inputs=inspection.prior_inputs
BUSYBOX_SHA256='7d93682be37cf6ed46699f6fff546b80bf133cf8ec342c2d04bc23387f78bc34'


def image_binding(image):
    require(image['profile']==PROFILE,'unselected root transition')
    root=inspection.image_binding(dict(image,profile=inspection.PROFILE))
    selected=image['switch_root']
    require(set(selected)=={'prepare','witness','busybox','checker','seconds','request','return_request',
        'root_readonly','installed_exec','same_transport','helpers_result'} and
        selected['seconds']==300 and selected['request']==37 and selected['return_request']==38 and
        selected['root_readonly'] is True and selected['installed_exec'] is False and selected['same_transport'] is True and
        selected['prepare']==root['helper'] and selected['busybox']['size']==1975064 and
        selected['busybox']['sha256']==BUSYBOX_SHA256 and selected['checker']==staged.execution_binding()['checker'],
        'root transition identity or effect scope differs')
    for name in ('prepare','witness','busybox','checker','helpers_result'):verify(selected[name])
    return root


class Profile:
    RESULT_KEY='switch_root'
    MUTATES=True
    OBSERVATION_SECONDS=360
