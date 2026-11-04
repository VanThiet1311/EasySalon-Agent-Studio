"""EasySalon Background Terminals & Queue (Backward-compatible alias for studio.services.terminal_service)."""

import sys
from studio.services import terminal_service as _service
from studio.services.terminal_service import *

sys.modules[__name__] = _service
