"""EasySalon Jira Operations (Backward-compatible alias for studio.services.jira_service)."""

import sys
from studio.services import jira_service as _service
from studio.services.jira_service import *

sys.modules[__name__] = _service
