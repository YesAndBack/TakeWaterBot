import asyncio
import logging
from bot import bot, send_reminder
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_direct_reminder():
    # Замените на свой Telegram ID
    user_id = 8442555440  
    current_time = datetime.now().strftime("%H:%M")
    
    logger.info(f"Отправка прямого тестового напоминания пользователю {user_id}")
    try:
        await send_reminder(user_id, current_time)
        logger.info("Напоминание успешно отправлено!")
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_direct_reminder())