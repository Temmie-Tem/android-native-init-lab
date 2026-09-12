"""V2 PID1 + V2 collectors/renderer through actual PTY, IPC and role owner."""
from unittest import mock
import unittest

import test_s22plus_native_thermal_roundtrip_v1 as previous
import s22plus_native_thermal_source_v2 as source

baseline=previous.baseline


def metrics_fixture(text):
    text=previous.thermal_metrics_fixture(text)
    start=text.index('    if(!strcmp(path,"/sys/module/s22plus_thermal_telemetry/parameters/sample"))')
    end=text.index('    int size=-1;',start)
    branch=r'''
    if(!strcmp(path,"/sys/module/s22plus_thermal_telemetry/parameters/sample")) {
        static uint64_t thermal_sequence;uint64_t stamp;assert(resident_clock(&stamp));
        struct s22_thermal_data s={.sequence=++thermal_sequence,.start_ms=stamp,.end_ms=stamp,
            .map_mask=65535,.mask=65535,.bound_mask=3,.mapped_mask=3,
            .phase={2,2},.seen={15,15},.version={0x20060000,0x20060000},.enable={1,1},.ready={1,1},
            .battery_uv=522166,.battery_deci=250,.battery_valid=1};
        for(unsigned i=0;i<S22_THERMAL_SENSOR_COUNT;i++) {
            const struct s22_thermal_cpu *sensor=s22_thermal_sensor(i);
            s.temp_mc[i]=52000+(int)i*100;s.status_valid[sensor->bank]|=1U<<sensor->sensor;
        }
        if(!strcmp(scenario,"thermal-unavailable")) {
            s=(struct s22_thermal_data){.sequence=thermal_sequence,.start_ms=stamp,.end_ms=stamp,
                .error={-19,-19},.phase={1,1},.battery_error=-19};
        }
        if(!strcmp(scenario,"thermal-battery-fault")) {
            s.battery_uv=s.battery_deci=s.battery_valid=0;s.battery_error=-110;
        }
        assert(s22_thermal_data_valid(&s));char row[768];
        int n=thermal_record(row,sizeof(row),1,&s);assert(n>0);
        const char *raw=strstr(row,"S22THERM2 ");assert(raw&&strlen(raw)<cap);
        memcpy(out,raw,strlen(raw)+1);return 1;
    }
'''
    text=text[:start]+branch+text[end:]
    return source.resident.replace(text.encode(),b'previous=*m;return send(fd,data,size,flags);',
        b'previous=*m;\n'
        b'    if(!strcmp(scenario,"thermal-old-ipc") && m->source) {'
        b'struct status_metrics old=*m;old.magic=0x31525353U;return send(fd,&old,128,flags);}\n'
        b'    return send(fd,data,size,flags);').decode()


class ThermalRoundtripV2(previous.ThermalRoundtrip):
    EXPERIMENT='p390'
    SOURCE=source
    METRICS=staticmethod(metrics_fixture)
    EXTRA_DOMAINS=('gpu','ddr')

    def test_legacy_worker_packet_is_rejected_by_actual_PID1(self):
        fixture=self.fixture();prior,_=self.bootstrap(fixture);running=self.running
        def selected(case='normal'):
            return running('thermal-old-ipc' if self.current_prefix==self.EXPERIMENT else case)
        with mock.patch.object(self,'running',side_effect=selected):
            grant=self.grant(fixture,operations=['experiment'])
            result=self.execute(fixture,grant,'experiment','native',prior)
        self.assertEqual(result['state'],'NATIVE_CLOSED')
        operation=baseline.owner.load_operation(baseline.live,fixture.prepared.root,grant.parent/'operation-01')
        hud=baseline.owner.experiment_outcome(baseline.live,operation)['sessions'][-1]['hud']
        self.assertIsNotNone(hud['latest'],hud)
        self.assertEqual(hud['latest']['hardware_state'],'FAULT')
        for domain in ('cpu','gpu','ddr','battery'):self.assertFalse(hud[domain+'_temperature_observed'])

    def test_battery_fault_preserves_TSENS_and_healthy_return(self):
        fixture=self.fixture();prior,_=self.bootstrap(fixture);running=self.running
        def selected(case='normal'):
            return running('thermal-battery-fault' if self.current_prefix==self.EXPERIMENT else case)
        with mock.patch.object(self,'running',side_effect=selected):
            grant=self.grant(fixture,operations=['experiment'])
            result=self.execute(fixture,grant,'experiment','native',prior)
        self.assertEqual(result['state'],'NATIVE_CLOSED')
        operation=baseline.owner.load_operation(baseline.live,fixture.prepared.root,grant.parent/'operation-01')
        hud=baseline.owner.experiment_outcome(baseline.live,operation)['sessions'][-1]['hud']
        self.assertFalse(hud['battery_temperature_observed'])
        for domain in ('cpu','gpu','ddr'):self.assertTrue(hud[domain+'_temperature_observed'],hud)
        self.assertTrue(hud['thermal_diagnostics_complete'])


if __name__=='__main__':unittest.main()
