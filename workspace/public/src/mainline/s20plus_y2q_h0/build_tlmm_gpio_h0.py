"""Build the post-wake GPIO tracer with the retained TLMM kernel and packaging recipe."""
import argparse
from pathlib import Path

import build_tlmm_flush_h0 as prior
import tlmm_gpio_h0 as reader

EXP = prior.EXP.with_name("s20plus-y2q-tlmm-gpio-h0-20261128")
OUT = EXP / "candidate"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=("kernel", "package"))
    args = parser.parse_args()
    recipe = prior.base.local_adapter(
        Path(prior.__file__), "51246556e40fa5cd1b9cc1c2ce2ec148be3b669ece8a93f2448d08d958b431d4",
        [('    apply("tlmm-flush-hooks.patch")',
          '    apply("tlmm-flush-hooks.patch")\n    apply("tlmm-gpio-hooks.patch")'),
         ('profile="tlmm-flush-h0"', 'profile="tlmm-gpio-h0"')], {})
    recipe.EXP, recipe.OUT, recipe.reader = EXP, OUT, reader
    if args.step == "kernel":
        recipe.build_kernel()
    else:
        recipe.package()


if __name__ == "__main__":
    main()
