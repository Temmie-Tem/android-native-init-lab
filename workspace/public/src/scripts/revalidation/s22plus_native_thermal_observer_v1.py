"""Exact new thermal HUD grammar on the existing fixed resident workload."""
import re
import s22plus_native_baseline_resident_v2 as resident
import s22plus_native_resident_observer_v1 as frames
import s22plus_native_resident_protocol_v1 as wire

_THERMAL = re.compile(frames._FRAME.pattern.replace(b'RESIDENT_FRAME ',b'RESIDENT_THERMAL_FRAME ')
    .replace(b' expected=13',b' expected=13 battery_temp_deci=(-?\\d+)'))


def decode_hud(raw):
    if type(raw) is not bytes or len(raw)>50000: raise ValueError('thermal HUD bound differs')
    parts=raw.split(b'\n',2)
    tail=b'S22RPROBE1 COMPLETE\n'
    if len(parts)!=3 or not parts[2].endswith(tail): raise ValueError('thermal HUD framing differs')
    retained=wire.decode_log(parts[2][:-len(tail)])
    temperatures={};converted=[]
    for row in retained['records']:
        if row.startswith(b'RESIDENT_FRAME '): raise ValueError('old HUD grammar in thermal profile')
        if row.startswith(b'RESIDENT_THERMAL_FRAME '):
            match=_THERMAL.fullmatch(row)
            if not match: raise ValueError('thermal HUD record grammar differs')
            # Battery field is inserted before producer_dropped, the final old field.
            sequence=int(match.groups()[0]);deci=int(match.groups()[-2])
            if not -(2**31)<=deci<2**31 or sequence in temperatures:
                raise ValueError('thermal HUD battery value/sequence differs')
            temperatures[sequence]=deci
            row=re.sub(rb' battery_temp_deci=-?\d+',b'',row, count=1)
            row=row.replace(b'RESIDENT_THERMAL_FRAME ',b'RESIDENT_FRAME ',1)
        converted.append(row)
    header=parts[2].split(b'\n',1)[0]+b'\n'
    normalized=parts[0]+b'\n'+parts[1]+b'\n'+header+b''.join(converted)+b'S22RLOG1 COMPLETE\n'+tail
    value=frames.decode_probe(normalized)
    latest=value['latest'];fresh=False
    if latest:
        if latest['sequence'] not in temperatures: raise ValueError('thermal HUD lacks temperature join')
        latest['battery_temp_deci']=temperatures[latest['sequence']]
        if latest['hardware_valid']&16 and not -200<=latest['battery_temp_deci']<=900:
            raise ValueError('thermal battery is outside the exact board table')
        fresh=latest['hardware_state']=='FRESH' and value['current_age_upper_ms']['hardware_age_ms']<=5000
    return dict(value,cpu_temperature_observed=bool(latest and fresh and latest['hardware_valid']&256),
        battery_temperature_observed=bool(latest and fresh and latest['hardware_valid']&16),
        cpu_hardware_conversion_age='UNPROVED',battery_source='board-adc-temp-0x14b-shared-wpc')


class IO(resident.IO):
    HUD_SETTLE_SECONDS=3
    @staticmethod
    def decode_hud(raw,run_id):
        return decode_hud(raw)


class Observer(resident.Observer):
    io_class=IO
    def __init__(self,identity,control):
        super().__init__(identity,control)
        self.__file__=__file__
