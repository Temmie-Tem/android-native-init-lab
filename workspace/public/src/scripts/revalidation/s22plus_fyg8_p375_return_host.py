"""P375 one durable Download intent with the actual console CONTROL sequence."""
from s22plus_fyg8_p375_namespace import projected,_definitions


def _control_sequence(request):
    if type(request) is not dict or type(request.get('sequence')) is not int or not 3<=request['sequence']<0xffffffff:
        raise ValueError('P375 CONTROL sequence differs')
    return request['sequence']

_source=projected('s22plus_fyg8_p375_return_host.py')
if _source.count(b'sequence=10')!=3:raise ValueError('P375 immutable return intent seam differs')
_source=_source.replace(b'sequence=10',b'sequence=_control_sequence(request)')
exec(compile(_definitions(_source),__file__+'#return-owner','exec'),globals())
_root_read_intent=read_intent


def read_intent(run_dir,*,binding=None,endpoint_identity_sha256=None,proof=None):
    value,receipt=_root_read_intent(run_dir,binding=binding,endpoint_identity_sha256=endpoint_identity_sha256,proof=None)
    if proof is not None:
        expected=dict(run_id_hex=RUN_ID,mode='download',sequence=proof['control_sequence'],
            nonce_sha256=proof['nonce_sha256'],kernel_boot_identity_sha256=proof['kernel_boot_identity_sha256'],
            boot_id_semantic=spec.BOOT_ID_SEMANTIC,boot_receipt_semantic=spec.BOOT_RECEIPT_SEMANTIC)
        if value['request']!=expected:raise ReturnControlError('P375 intent/raw console join differs')
    return value,receipt
