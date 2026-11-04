"""EasySalon Telegram Bot Service (Backward-compatible alias for studio.services.telegram_service)."""

import sys
from studio.services import telegram_service as _service
from studio.services.telegram_service import *

sys.modules[__name__] = _service
