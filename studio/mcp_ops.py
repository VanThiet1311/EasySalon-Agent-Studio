"""EasySalon MCP Operations (Backward-compatible alias for studio.services.mcp_service)."""

import sys
from studio.services import mcp_service as _service
from studio.services.mcp_service import *

sys.modules[__name__] = _service
