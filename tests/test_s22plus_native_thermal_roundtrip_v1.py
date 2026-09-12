"""New thermal E in the actual resident C/PTY/IPC and durable N/E/N owner."""
from pathlib import Path
import json
import time
import unittest
from unittest import mock

import test_s22plus_native_baseline_owner_v2 as baseline
import s22plus_resident_adoption_h0_support as support
import s22plus_native_thermal_source_v1 as source


def thermal_metrics_fixture(text):
    start=text.index('static int status_read(');end=text.index('static ssize_t metrics_send(',start)
    body=text[start:end]
    branch=r'''
    if(!strcmp(path,"/sys/module/s22plus_thermal_telemetry/parameters/sample")){
        static uint64_t thermal_sequence;uint64_t stamp;assert(resident_clock(&stamp));
        unsigned valid=3,mask=8191;int cpu=52000,battery=250,uv=522166,error=0,cpu_error=0;
        if(!strcmp(scenario,"thermal-unavailable")){valid=mask=0;cpu=battery=uv=0;error=cpu_error=-19;}
        if(!strcmp(scenario,"thermal-battery-fault")){valid=1;battery=uv=0;error=-110;}
        int n=snprintf(out,cap,"S22THERM1 seq=%llu start_ms=%llu end_ms=%llu valid=%u cpu_mask=%u cpu_temp_mc=%d battery_uv=%d battery_temp_deci=%d battery_error=%d cpu0_error=%d cpu1_error=%d\n",
            (unsigned long long)++thermal_sequence,(unsigned long long)stamp,(unsigned long long)stamp,
            valid,mask,cpu,uv,battery,error,cpu_error,cpu_error);
        assert(n>0&&(size_t)n<cap);return 1;
    }
'''
    body=body.replace('    int size=-1;',branch+'    int size=-1;',1)
    cpu=body.index('        }else {\n            unsigned zone;')
    tail=body.rindex('    assert(size>0')
    body=body[:cpu]+'        }else {assert(0);}\n    }\n'+body[tail:]
    text=text[:start]+body+text[end:]
    start=text.index('static ssize_t metrics_send(int fd,');end=text.index('int main(',start)
    send=r'''
static ssize_t metrics_send(int fd,const void *data,size_t size,int flags){
    assert(fd==1&&size==sizeof(struct status_metrics)&&flags==(MSG_DONTWAIT|MSG_NOSIGNAL));
    const struct status_metrics *m=data;static struct status_metrics previous;
    uint64_t now;assert(resident_clock(&now));
    assert(m->sequence==++fixture_sent&&resident_sample_valid(m,&previous,m->source,now,m->run));
    previous=*m;return send(fd,data,size,flags);
}
'''
    return text[:start]+send+text[end:]


class Backend(baseline.previous.Backend):
    def start_peer(self,phase):
        self.test.current_prefix=self.test.EXPERIMENT if phase=='experiment' else 'p387'
        super().start_peer(phase)


class ThermalRoundtrip(unittest.TestCase):
    EXPERIMENT='p389'
    SOURCE=source
    METRICS=staticmethod(thermal_metrics_fixture)
    EXTRA_DOMAINS=()
    execute=baseline.OwnerV2Tests.execute
    running=baseline.OwnerV2Tests.running
    grant=baseline.OwnerV2Tests.grant
    bootstrap=baseline.OwnerV2Tests.bootstrap

    def exercise_native(self,**kwargs):
        return baseline.OwnerV2Tests.exercise_native(self,observation_seconds=60 if self.current_prefix==self.EXPERIMENT else 5,**kwargs)

    @classmethod
    def setUpClass(cls):
        cls.resources={}
        for prefix in ('p387',cls.EXPERIMENT):
            resource=type('ThermalFixture_'+prefix,(unittest.TestCase,),{})
            options=dict(render_source=cls.SOURCE,metrics_transform=cls.METRICS) if prefix==cls.EXPERIMENT else {}
            support.compile_components(resource,baseline.candidates.DECLARATIONS[prefix],**options)
            cls.addClassCleanup(resource.doClassCleanups);cls.resources[prefix]=resource
        cls.binary=cls.resources['p387'].binary

    def fixture(self):
        with mock.patch.object(baseline,'Backend',Backend): fixture=baseline.OwnerV2Tests.fixture(self)
        fixture.experiment_manifest=fixture.prepared.root/(self.EXPERIMENT+'-manifest.json')
        # The real optional HUD admission needs 26 seconds remaining. Preserve
        # the short legacy tests; this E fixture uses the actual 60-second bound.
        fixture.bundles[self.EXPERIMENT].manifest['observation']['timeout_sec']=60
        fixture.experiment_manifest.chmod(0o600)
        fixture.experiment_manifest.write_text(json.dumps(fixture.bundles[self.EXPERIMENT].manifest,sort_keys=True)+'\n')
        fixture.experiment_manifest.chmod(0o400)
        return fixture

    def test_thermal_E_proof_and_distinct_N_restoration(self):
        fixture=self.fixture();prior,_=self.bootstrap(fixture)
        grant=self.grant(fixture,operations=['experiment'])
        result=self.execute(fixture,grant,'experiment','native',prior)
        self.assertEqual(result['state'],'NATIVE_CLOSED')
        operation=baseline.owner.load_operation(baseline.live,fixture.prepared.root,grant.parent/'operation-01')
        proof=baseline.owner.experiment_outcome(baseline.live,operation)
        hud=proof['sessions'][-1]['hud']
        self.assertTrue(hud['cpu_temperature_observed'],hud);self.assertTrue(hud['battery_temperature_observed'],hud)
        for domain in self.EXTRA_DOMAINS:self.assertTrue(hud[domain+'_temperature_observed'],hud)
        self.assertEqual(hud['latest']['cpu_mask'],8191);self.assertEqual(hud['latest']['battery_temp_deci'],250)
        self.assertEqual([row.namespace for _,row in fixture.backend.raw_observers],['p387','p387','p387',self.EXPERIMENT,'p387'])
        self.assertEqual(fixture.backend.calls.count('transfer-'+baseline.owner.TRANSFER_ANDROID),0)
        self.assertEqual(baseline.owner.native_terminal(baseline.live,fixture.prepared.root,operation.directory),result)

    def test_unavailable_temperatures_do_not_repeat_E_or_block_healthy_N_return(self):
        fixture=self.fixture();prior,_=self.bootstrap(fixture)
        running=self.running
        def selected(case='normal'):
            return running('thermal-unavailable' if self.current_prefix==self.EXPERIMENT else case)
        with mock.patch.object(self,'running',side_effect=selected):
            grant=self.grant(fixture,operations=['experiment'])
            result=self.execute(fixture,grant,'experiment','native',prior)
        self.assertEqual(result['state'],'NATIVE_CLOSED')
        operation=baseline.owner.load_operation(baseline.live,fixture.prepared.root,grant.parent/'operation-01')
        proof=baseline.owner.experiment_outcome(baseline.live,operation)
        hud=proof['sessions'][-1]['hud']
        self.assertFalse(hud['cpu_temperature_observed']);self.assertFalse(hud['battery_temperature_observed'])
        for domain in self.EXTRA_DOMAINS:self.assertFalse(hud[domain+'_temperature_observed'])
        self.assertEqual(fixture.backend.calls.count('transfer-'+baseline.owner.TRANSFER_NATIVE),4)
        self.assertEqual(fixture.backend.calls.count('transfer-'+baseline.owner.TRANSFER_ANDROID),0)
        before=len(fixture.backend.raw_observers)
        again=self.grant(fixture,operations=['experiment'])
        with self.assertRaises(baseline.owner.registry.RegistryError):
            self.execute(fixture,again,'experiment','native',operation.directory/'terminal.json')
        self.assertEqual(len(fixture.backend.raw_observers),before)

    def test_original_grant_expiry_during_settle_sends_no_HUD_or_normal_N(self):
        for prefix in ('p387','p388'):
            self.assertEqual(baseline.candidates.DECLARATIONS[prefix].observer.io_class.HUD_SETTLE_SECONDS,0)
        self.assertEqual(baseline.candidates.DECLARATIONS[self.EXPERIMENT].observer.io_class.HUD_SETTLE_SECONDS,3)
        fixture=self.fixture();prior,_=self.bootstrap(fixture)
        grant=self.grant(fixture,operations=['experiment'])
        expiry=baseline.owner.read(grant)[0]['deadline_boottime_ns']
        real_now=baseline.owner.protocol.host_now_ns;real_sleep=time.sleep;expired=[]
        def sleeping(seconds):
            if seconds==3: expired.append(True)
            else: real_sleep(seconds)
        with mock.patch.object(time,'sleep',side_effect=sleeping), \
             mock.patch.object(baseline.owner.protocol,'host_now_ns',side_effect=lambda:expiry if expired else real_now()):
            result=self.execute(fixture,grant,'experiment','native',prior)
        self.assertEqual(expired,[True]);self.assertEqual(result['state'],'ANDROID_CLOSED',result)
        self.assertEqual(fixture.backend.calls.count('transfer-'+baseline.owner.TRANSFER_NATIVE),3)
        self.assertEqual(fixture.backend.calls.count('transfer-'+baseline.owner.TRANSFER_ANDROID),1)
        operation=baseline.owner.load_operation(baseline.live,fixture.prepared.root,grant.parent/'operation-01')
        self.assertFalse((operation.directory/'native-final').exists())
        self.assertFalse((operation.directory/'experiment/native-before-terminal.json').exists())


if __name__=='__main__':unittest.main()
