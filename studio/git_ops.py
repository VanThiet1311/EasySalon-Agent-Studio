"""EasySalon Git Operations (Backward-compatible alias for studio.services.git_service)."""

import sys
from studio.services import git_service as _service
from studio.services.git_service import *

sys.modules[__name__] = _service
