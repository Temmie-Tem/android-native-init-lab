"""Bounded post-reap output drain over the frozen UFS V1 composition."""
from pathlib import Path

import s22plus_native_ufs_source_v1 as previous

resident=previous.resident
ROOT,NATIVE,PROFILE=previous.ROOT,previous.NATIVE,previous.PROFILE
THERMAL_PROFILE,RECONNECT_PROFILE=previous.THERMAL_PROFILE,previous.RECONNECT_PROFILE
STORAGE_PROFILE=previous.STORAGE_PROFILE
CONSOLE_PROFILE='settled-output-drain-v1'
SAMPLE_MAGIC,VIEW_MAGIC=previous.SAMPLE_MAGIC,previous.VIEW_MAGIC
render_display=previous.render_display
provider_sources,provider_files=previous.provider_sources,previous.provider_files
core_source,sensor_map,wire_source=previous.core_source,previous.sensor_map,previous.wire_source


def upgrade_native(raw):
    old=b'''        int clean=s->reaped && n==-P328_ECHILD && group==-3 && s->pipe[0]<0 && s->pipe[1]<0 && s->exec_seen;
        if(clean || (s->cancel_phase && now-s->cancel_start>=2000U)) {'''
    new=b'''        /* Process-group cleanup and buffered pipe delivery are distinct.
         * A settled group may drain until the original command deadline.
         * Explicit cancellation/timeout retains the bounded cleanup stop. */
        int settled=s->reaped && n==-P328_ECHILD && group==-3 && s->exec_seen;
        int clean=settled && s->pipe[0]<0 && s->pipe[1]<0;
        int forced=s->flags&(RC1_FLAG_CANCEL|RC1_FLAG_TIMEOUT|RC1_FLAG_CONTROL);
        if(clean || (s->cancel_phase && now-s->cancel_start>=2000U && (!settled || forced))) {'''
    return resident.replace(raw,old,new)


def helper_template(identity):
    return upgrade_native(previous.helper_template(identity))


def materialize_helper(identity,key):
    return upgrade_native(previous.materialize_helper(identity,key))


def profile_contract():
    return dict(previous.profile_contract(),console_profile=CONSOLE_PROFILE,
        settled_output_deadline='original command deadline',
        unsettled_cleanup_ms=2000,output_limits_unchanged=True)


def source_files():
    return tuple(sorted(set(previous.source_files())|{Path(__file__)}))
