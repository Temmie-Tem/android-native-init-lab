"""Resident INFO-v2 on the shared fixed-health baseline observer.

This profile selects wire parsing and the bounded optional HUD export only.
The baseline owner supplies all device authority and descriptor operations.
"""
import s22plus_native_baseline_observer_v1 as baseline
import s22plus_native_resident_protocol_v1 as resident
import s22plus_native_resident_observer_v1 as checkpoints


class IO(resident.IO):
    HUD_BODY = checkpoints.HUD_BODY

    @staticmethod
    def decode_hud(raw, run_id):
        return checkpoints.decode_probe(raw)


class Observer(baseline.Observer):
    io_class = IO
    PROOF_SCOPE = 'fixed-resident-native-health-and-clean-reauthentication'
