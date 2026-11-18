"""The single declaration of module report versions and their compile modes.

Report v3 has no explicit return; v4 adds it; v5 is the HCI-snapshot side
branch; every mode from v6 on is cumulative. Builders, the guest observer,
candidate reproduction and the host decoder derive their choices from here.
"""

LATEST = 13
# (first report version, builder keyword, C define), in Kbuild/compiler order.
CHAIN = (
    (6, 'hce_handoff', 'G0Q_HCE_HANDOFF'),
    (7, 'reset_config', 'G0Q_RESET_CONFIG'),
    (8, 'disabled_ucrdy', 'G0Q_DISABLED_UCRDY'),
    (9, 'stale_uccs_ack', 'G0Q_STALE_UCCS_ACK'),
    (10, 'cfg1_diagnostics', 'G0Q_CFG1_DIAGNOSTICS'),
    (11, 'cfg1_ordered_selection', 'G0Q_CFG1_ORDERED_SELECTION'),
    (12, 'link_irq_diagnostics', 'G0Q_LINK_IRQ_DIAGNOSTICS'),
    (13, 'upstream_link', 'G0Q_UPSTREAM_LINK'),
)
KEYWORDS = ('pre_effect_return', 'hci_snapshot', *(kw for _, kw, _ in CHAIN))
# Decimal fields in each report version's status line (host decoder schema).
FIELDS = {1: 19, 2: 21, 3: 23, 4: 23, 5: 30, 6: 30, 7: 30, 8: 30, 9: 30,
          10: 33, 11: 33, 12: 33, 13: 38}
FIRST = {kw: first for first, kw, _ in CHAIN}


def modes(version):
    """Builder keywords selected by one report version."""
    if type(version) is not int or not 3 <= version <= LATEST:
        raise ValueError('unselected module report version')
    out = dict(pre_effect_return=version >= 4, hci_snapshot=version == 5)
    out.update({kw: version >= first for first, kw, _ in CHAIN})
    return out


def version_of(**keywords):
    """The unique report version for a complete or partial keyword set."""
    if set(keywords) - set(KEYWORDS) or any(type(v) is not bool for v in keywords.values()):
        raise ValueError('unknown or non-boolean module mode keyword')
    chosen = dict.fromkeys(KEYWORDS, False) | keywords
    for version in range(3, LATEST + 1):
        if modes(version) == chosen:
            return version
    raise ValueError('inconsistent module mode keywords')


def defines(version, *, observer=False):
    """C defines in their historical order; the observer arms recovery with handoff."""
    selected = modes(version)
    out = [name for kw, name in (('pre_effect_return', 'G0Q_PRE_EFFECT_RETURN'),
                                 ('hci_snapshot', 'G0Q_HCI_SNAPSHOT')) if selected[kw]]
    for _, kw, name in CHAIN:
        if selected[kw]:
            out.append(name)
            if observer and kw == 'hce_handoff':
                out.append('G0Q_AUTOMATIC_RECOVERY')
    return out
