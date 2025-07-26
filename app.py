from fastapi import FastAPI
import uvicorn
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from bot import bot, dp
from scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск планировщика...")
    start_scheduler()
    
    logger.info("Запуск бота...")
    bot_task = asyncio.create_task(dp.start_polling(bot))
    logger.info("Бот запущен")
    
    yield
    
    logger.info("Останавливаем бота...")
    bot_task.cancel()
    logger.info("Бот остановлен")

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "working", "message": "Water Reminder Bot is running"}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)