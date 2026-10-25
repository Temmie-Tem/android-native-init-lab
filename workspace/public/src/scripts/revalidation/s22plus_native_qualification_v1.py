"""Owner-local reuse of complete immutable automatic-boot image qualification.

Never caches authority, target/health, journal, grant, ownership or transfer
admission. Changed inputs invalidate the owner ticket without refreshing it.
"""
from copy import deepcopy
from pathlib import Path

from device_action_read_dependencies_v1 import ReadSet
from s22plus_native_records_v3 import canonical, require, verify


class Qualification:
    def __init__(self):
        self.key = None
        self.dependencies = None
        self.value = None
        self.failed = False

    def binding(self, image, validator):
        require(not self.failed, 'immutable qualification ticket is invalid')
        try:
            key = canonical(image)
            if self.dependencies is not None:
                require(key == self.key, 'owner qualification image changed')
                self.dependencies.check()
                return deepcopy(self.value)
            import s22plus_debian_handoff_profile_v1 as handoff
            import s22plus_debian_autoboot_phase_v1 as phases
            # These pure caches can otherwise hide archive reads in a warm
            # process. Every new ticket must observe their complete inputs.
            handoff.payloads.cache_clear()
            phases.original_scripts.cache_clear()
            with ReadSet() as dependencies:
                # Includes direct-read templates and implementation sources that
                # the image's full qualification compares with this declaration.
                for name, receipt in image['runtime_sources'].items():
                    path = Path(handoff.ROOT) / name
                    require(path.is_relative_to(handoff.ROOT), 'runtime source escaped repository')
                    verify(dict(path=str(path), **receipt))
                value = validator(image)
            require(dependencies.files, 'qualification has no verified dependencies')
            dependencies.check()
            self.key, self.value, self.dependencies = key, deepcopy(value), dependencies
            return value
        except Exception:
            self.failed = True
            raise
