"""Actual A/B preflight qualification using the shared Android32 return join."""
import s22plus_native_root_inspect_artifact_v1_h0 as shared


def qualify(namespace, output, *, key_path, build_directory=None):
    return shared.qualify(namespace,output,key_path=key_path,build_directory=build_directory,preflight=True)
