"""Instrument a disposable private copy of the selected g0q kernel for H0."""
import argparse
import hashlib
from pathlib import Path
import secrets
import shutil

HERE = Path(__file__).resolve().parent
OUTPUTS = (HERE.parents[3] / 'private/outputs').resolve()
CONFIGFS = 'drivers/usb/gadget/configfs.c'
CORE = 'drivers/usb/gadget/udc/core.c'
PINS = {
    CONFIGFS: 'a11ceb5965526674ce75fccbfdf0ecb54c644987ec94f4172d2a54ab437c1d5a',
    CORE: '17d0d78f3de3d3dbf28d7136496a1a92c5e3744791b3221269b58c0aecd91041',
}
WRAPPER = """
/* Record the original configfs callback's actual result, including errors. */
extern void g0q_udc_bind_observed(bool done, ssize_t result);
static ssize_t gadget_dev_desc_UDC_store(struct config_item *item,
		const char *page, size_t len)
{
	bool selected = !strcmp(config_item_name(item), "g0q-canary") &&
		len == sizeof("a600000.usb") - 1 && !memcmp(page, "a600000.usb", len);
	ssize_t result;

	if (selected)
		g0q_udc_bind_observed(false, 0);
	result = g0q_original_UDC_store(item, page, len);
	if (selected)
		g0q_udc_bind_observed(true, result);
	return result;
}
"""


def prepare(directory):
    directory = directory.resolve(strict=True)
    if not directory.is_relative_to(OUTPUTS) or directory.name != 'udc-kernel':
        raise ValueError('expected private disposable udc-kernel directory')
    source = directory / 'kernel-source'
    for rel, pin in PINS.items():
        f = source / rel
        if not f.resolve().is_relative_to(directory) or f.stat().st_nlink != 1:
            raise ValueError('source must be an independent private copy')
        if hashlib.sha256(f.read_bytes()).hexdigest() != pin:
            raise ValueError('selected source differs: ' + rel)
    configfs = (source / CONFIGFS).read_text()
    original = 'static ssize_t gadget_dev_desc_UDC_store('
    following = 'static ssize_t gadget_dev_desc_max_speed_show('
    if configfs.count(original) != 1 or configfs.count(following) != 1:
        raise ValueError('configfs callback layout differs')
    configfs = configfs.replace(original, 'static ssize_t g0q_original_UDC_store(')
    candidate = secrets.token_bytes(16)
    key = secrets.token_bytes(32)
    build_dir = (source / CORE).parent
    seal = build_dir / 'g0q-udc-key.h'
    with seal.open('x') as f:
        for name, value in [('candidate', candidate), ('key', key)]:
            f.write(f'static const u8 g0q_{name}[] = {{' + ','.join(map(str, value)) + '};\n')
    with (directory / 'observation.key').open('xb') as f:
        f.write(key)
    with (directory / 'observation.id').open('xb') as f:
        f.write(candidate)
    shutil.copyfile(HERE / 'retained-udc.h', build_dir / 'retained-udc.h')
    (source / CONFIGFS).write_text(configfs.replace(following, WRAPPER + '\n' + following))
    with (source / CORE).open('a') as f:
        f.write('\n#include "retained-udc.h"\n')


if __name__ == '__main__':
    import os
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    prepare(parser.parse_args().directory)
