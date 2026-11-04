"""EasySalon Architecture Diagram (Backward-compatible alias for studio.services.diagram_service)."""

import sys
from studio.services import diagram_service as _service
from studio.services.diagram_service import *

sys.modules[__name__] = _service
