
import os
from pathlib import Path
from ccpp_prebuild_config import *

_scm_root = Path(__file__).resolve().parents[2]
_bundled_root = (_scm_root / "ccpp/physics/physics/SFC_Models/Land/NoahmpModular/noahmp").resolve()
_noahmp_root = Path(os.environ.get("NOAHMP_ROOT", _bundled_root)).resolve()
_scheme = _noahmp_root / "drivers/ccpp/noahmp.F90"
if not _scheme.is_file():
    raise RuntimeError(
        f"Modular Noah-MP CCPP driver is missing at {_scheme}; set "
        "NOAHMP_ROOT to a complete Noah-MP checkout or populate the bundled copy"
    )
SCHEME_FILES = [path for path in SCHEME_FILES if not path.endswith("/Noahmp/noahmpdrv.F90")]
SCHEME_FILES.append(_scheme.as_posix())

# Modular generated artifacts must not overwrite the legacy API or documentation.
STATIC_API_DIR = "{build_dir}/modular_api"
STATIC_API_CMAKEFILE = "{build_dir}/modular_api/CCPP_STATIC_API.cmake"
STATIC_API_SOURCEFILE = "{build_dir}/modular_api/CCPP_STATIC_API.sh"
HTML_VARTABLE_FILE = "{build_dir}/CCPP_VARIABLES_SCM.html"
LATEX_VARTABLE_FILE = "{build_dir}/CCPP_VARIABLES_SCM.tex"
