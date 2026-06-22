import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class TelegramAlertService:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    async def send_alert(self, message: str) -> bool:
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram bot token or chat ID not set. Skipping alert.")
            return False
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    json={
                        "chat_id": self.chat_id,
                        "text": message,
                        "parse_mode": "Markdown"
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False
