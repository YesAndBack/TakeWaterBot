from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging
import asyncio
import time

from aiogram import types
from bot import bot, send_reminder, user_data, init_user_data
from sheets import save_day_results
from config import REMINDER_TIMES
from pytz import timezone


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Отладочная информация о времени
logger.info(f"Текущее системное время: {datetime.now()}")
logger.info(f"Текущее время UNIX: {time.time()}")
logger.info(f"Временная зона: {time.tzname}")

tz = timezone('Asia/Almaty') 
scheduler = AsyncIOScheduler(timezone=tz)

# Функция для отправки напоминаний всем пользователям
async def send_reminders(time):
    """Отправляет напоминания всем пользователям"""
    logger.info(f"Отправка напоминаний на время {time}")
    
    if not user_data:
        logger.warning("Нет данных пользователей для отправки напоминаний!")
        return
    
    logger.info(f"Количество пользователей для отправки напоминаний: {len(user_data)}")
    
    for user_id in user_data:
        try:
            logger.info(f"Отправка напоминания пользователю {user_id}")
            await send_reminder(user_id, time)
            logger.info(f"Напоминание успешно отправлено пользователю {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")

# Функция для добавления задач напоминаний
def setup_reminders():
    """Настраивает расписание напоминаний"""
    logger.info(f"Настройка напоминаний для {len(user_data)} пользователей")
    
    for time in REMINDER_TIMES:
        hour, minute = map(int, time.split(':'))
        
        # Добавляем задачу для каждого времени напоминания
        scheduler.add_job(
            send_reminders,
            CronTrigger(hour=hour, minute=minute),
            kwargs={"time": time},
            id=f"reminder_{time}",
            replace_existing=True
        )
        logger.info(f"Установлено напоминание на {time}")

# Функция для сохранения дневных результатов в Google Sheets
async def save_daily_results():
    """Сохраняет дневные результаты пользователей в Google Sheets"""
    logger.info("Сохранение дневных результатов")
    today = datetime.now().strftime("%Y-%m-%d")
    
    for user_id, data in user_data.items():
        try:
            # Проверяем, есть ли данные для сохранения
            if data["today_logs"] and data["total_today"] > 0:
                # Сохраняем результаты в Google Sheets
                save_day_results(
                    user_id,
                    today,
                    data["total_today"],
                    data["today_logs"],
                    data["daily_norm"]
                )
                
                logger.info(f"Результаты пользователя {user_id} сохранены")
            else:
                logger.info(f"Нет данных для сохранения у пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении результатов пользователя {user_id}: {e}")

# Настройка ежедневного сохранения результатов
def setup_daily_save():
    """Настраивает ежедневное сохранение результатов"""
    scheduler.add_job(
        save_daily_results,
        CronTrigger(hour=23, minute=50),  # Сохраняем в 23:50
        id="save_results",
        replace_existing=True
    )
    logger.info("Установлено ежедневное сохранение результатов на 23:50")

# Запуск планировщика
def start_scheduler():
    """Запускает планировщик задач"""
    setup_reminders()
    setup_daily_save()
    
    # Запускаем планировщик ПЕРЕД выводом информации о задачах
    scheduler.start()
    logger.info("Планировщик запущен")
    
    # Теперь, когда планировщик запущен, выводим все запланированные задачи
    jobs = scheduler.get_jobs()
    logger.info(f"Количество запланированных задач: {len(jobs)}")
    for job in jobs:
        logger.info(f"Задача: {job.id}, следующий запуск: {job.next_run_time}")