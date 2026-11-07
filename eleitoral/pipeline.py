"""Pipeline completo da V2: download -> ingestão -> reconciliação -> dimensões -> fatos.

Uso:
    python -m eleitoral.pipeline [--years 2022 2024 2026] [--no-download]

Falha (exit 1) se a reconciliação com o resultado oficial tiver divergência.
"""
from __future__ import annotations

import argparse
import sys

from eleitoral.ingest import reconcile, tse
from eleitoral.ingest.download import DATASETS, download_zip
from eleitoral.transform import build_dims, build_facts

YEARS = (2022, 2024, 2026)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--years", type=int, nargs="+", default=list(YEARS))
    p.add_argument("--no-download", action="store_true")
    a = p.parse_args(argv)
    if not a.no_download:
        for y in a.years:
            for ds in DATASETS:
                print(f"download {ds} {y}: {download_zip(y, dataset=ds).name}")
    for y in a.years:
        tse.run(y)
        if reconcile.main(["--year", str(y)]) != 0:
            print(f"Reconciliação {y} falhou; abortando.")
            return 1
    build_dims.main(["--years", *map(str, a.years)])
    build_facts.main(["--years", *map(str, a.years)])
    return 0


if __name__ == "__main__":
    sys.exit(main())
