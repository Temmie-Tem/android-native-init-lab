"""P366 exact native departure successor; no device authority."""
from s22plus_fyg8_p366_namespace import load
load(globals())

import s22plus_native_usb_departure_v1 as departure
_base_read_intent=read_intent
_base_validate_window=validate_window

def read_intent(run_dir, **kwargs):
    value,receipt=_base_read_intent(run_dir,**kwargs)
    try:
        departure.read_binding(run_dir,value)
    except departure.DepartureError as exc:
        raise ReturnControlError('P366 native departure binding differs') from exc
    return value,receipt

def validate_window(value, *, binding, intent, intent_receipt):
    result=_base_validate_window(value,binding=binding,intent=intent,intent_receipt=intent_receipt)
    if value['outcome'] in ('exact-download-within-control-window','exact-download-after-control-window'):
        try:
            observed,_=departure.read_observation(Path(intent_receipt['path']).parent,intent,intent_receipt)
        except departure.DepartureError as exc:
            raise ReturnControlError('P366 native departure witness absent') from exc
        if observed['status'] != 'absent':
            raise ReturnControlError('P366 arrival lacks prior native departure')
    return result
