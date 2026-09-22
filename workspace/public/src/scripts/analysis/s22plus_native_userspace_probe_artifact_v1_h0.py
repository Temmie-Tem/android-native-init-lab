"""Qualify actual userspace-probe bytes and the retained P402 root/Android proof."""
import s22plus_native_root_inspect_artifact_v1_h0 as inspector


def qualify(namespace, output, *, key_path, build_directory=None):
    return inspector.qualify(namespace, output, key_path=key_path,
        build_directory=build_directory, userspace=True)
