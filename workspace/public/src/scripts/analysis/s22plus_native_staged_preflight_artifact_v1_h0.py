"""Qualify actual A/B streamed-preparation payloads and Android32 return."""
import s22plus_native_root_inspect_artifact_v1_h0 as shared


def qualify(namespace,output,*,key_path,build_directory=None):
    return shared.qualify(namespace,output,key_path=key_path,build_directory=build_directory,staged=True)
