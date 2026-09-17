#!/usr/bin/env python3
"""Check that an offline CCPP-SCM copy contains its modular Noah-MP inputs.

This check reads only the CCPP-SCM tree. It does not require an HRLDAS
checkout, a Git repository, or a configured build directory.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


DEFAULT_SCM_ROOT = Path(__file__).resolve().parents[2]
NOAHMP_RELATIVE = Path("ccpp/physics/physics/SFC_Models/Land/NoahmpModular/noahmp")
SNICAR_FILES = (
    "snicar_drdt_bst_fit_60_c070416.nc",
    "snicar_optics_5bnd_c013122.nc",
    "snicar_optics_480bnd_c012422.nc",
)


def check(scm_root: Path) -> None:
    noahmp_root = scm_root / NOAHMP_RELATIVE
    driver = noahmp_root / "drivers/ccpp"
    required_files = (
        "ccpp/config/ccpp_prebuild_config_modular_noahmp.py",
        "ccpp/physics/physics/hooks/machine.F",
        "ccpp/physics_namelists/input_GFS_v17_p8_ugwpv1_modular_noahmp.nml",
        "ccpp/suites/suite_SCM_GFS_v17_p8_ugwpv1_modular_noahmp.xml",
        "scm/data/processed_case_input/gabls3_noahmp_nospinup_SCM_driver.nc",
        "scm/etc/case_config/gabls3_noahmp_nospinup.nml",
        "scm/etc/tracer_config/tracers_GFS_v17_p8_ugwpv1.txt",
        "scm/src/GFS_typedefs.F90",
        "scm/src/GFS_typedefs.meta",
        "scm/src/run_scm.py",
    )
    required_noahmp_files = (
        "drivers/ccpp/ccpp_sources.py",
        "drivers/ccpp/generate_noahmp_meta.py",
        "drivers/ccpp/noahmp.F90",
        "drivers/ccpp/noahmp.meta",
        "parameters/NoahmpTable.TBL",
        *(f"parameters/{name}" for name in SNICAR_FILES),
    )
    missing = [str(scm_root / name) for name in required_files
               if not (scm_root / name).is_file()]
    missing += [str(noahmp_root / name) for name in required_noahmp_files
                if not (noahmp_root / name).is_file()]
    for name in ("src", "utility"):
        if not (noahmp_root / name).is_dir():
            missing.append(str(noahmp_root / name))
    for name in ("scm/data/physics_input_data", "scm/data/vert_coord_data"):
        if not (scm_root / name).is_dir():
            missing.append(str(scm_root / name))
    if missing:
        raise RuntimeError("Missing peer-copy inputs:\n  " + "\n  ".join(missing))

    # External or broken links would make a copied checkout dependent on the
    # developer's filesystem even if the regular files were all transferred.
    bad_links = []
    case_input = scm_root / "scm/data/processed_case_input/gabls3_noahmp_nospinup_SCM_driver.nc"
    for path in (*noahmp_root.rglob("*"), case_input):
        if path.is_symlink():
            target = path.resolve()
            if (Path(os.readlink(path)).is_absolute() or not target.exists() or
                    not target.is_relative_to(scm_root)):
                bad_links.append(str(path))
    if bad_links:
        raise RuntimeError("Broken, absolute, or external peer-copy symlinks:\n  " +
                           "\n  ".join(bad_links))

    result = subprocess.run(
        [sys.executable, str(driver / "ccpp_sources.py")],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError("Cannot resolve modular CCPP source closure:\n" +
                           result.stderr.strip())
    sources = [Path(name).resolve() for name in result.stdout.strip().split(";") if name]
    if not sources or (driver / "noahmp.F90").resolve() not in sources:
        raise RuntimeError("CCPP source closure does not include noahmp.F90")
    outside = [str(path) for path in sources
               if not path.is_file() or not path.is_relative_to(noahmp_root)]
    if outside:
        raise RuntimeError("Missing or external CCPP Fortran sources:\n  " +
                           "\n  ".join(outside))

    result = subprocess.run(
        [sys.executable, str(driver / "generate_noahmp_meta.py"), "--check"],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError("Modular CCPP metadata check failed:\n" +
                           result.stderr.strip())
    print(result.stdout.strip())
    print(f"Peer copy is self-contained: {len(sources)} CCPP Fortran sources, "
          "metadata, table, and SNICAR data are present under "
          f"{scm_root}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scm-root", type=Path, default=DEFAULT_SCM_ROOT)
    args = parser.parse_args()
    try:
        check(args.scm_root.resolve())
    except RuntimeError as error:
        parser.exit(1, f"Peer-copy check failed: {error}\n")


if __name__ == "__main__":
    main()
