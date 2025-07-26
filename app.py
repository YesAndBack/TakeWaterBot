from fastapi import FastAPI
import uvicorn
import asyncio
import logging
from contextlib import asynccontextmanager

from bot import bot, dp
from scheduler import start_scheduler

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Определение контекстного менеджера для управления жизненным циклом приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, который выполняется при запуске
    logger.info("Запуск планировщика...")
    start_scheduler()
    
    logger.info("Запуск бота...")
    bot_task = asyncio.create_task(dp.start_polling(bot))
    logger.info("Бот запущен")
    
    yield  # Здесь FastAPI обрабатывает запросы
    
    # Код, который выполняется при завершении
    logger.info("Останавливаем бота...")
    bot_task.cancel()
    logger.info("Бот остановлен")

# Инициализация FastAPI с контекстным менеджером жизненного цикла
app = FastAPI(lifespan=lifespan)

# Маршрут для проверки работоспособности
@app.get("/")
async def root():
    return {"status": "working", "message": "Water Reminder Bot is running"}

# Запуск приложения
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)