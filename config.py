import os
from dotenv import load_dotenv
from datetime import datetime

# Загрузка переменных окружения из файла .env
load_dotenv()

# Базовые настройки
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
REMINDER_TIMES = os.getenv("REMINDER_TIMES", "10:00,12:00,15:00,18:00,21:00").split(",")

# Функция для получения имени текущего месяца (для названия листа в Google Sheets)
def get_current_sheet_name():
    now = datetime.now()
    return f"{now.strftime('%B_%Y')}"  # Например: "July_2025"

# Минимальная рекомендуемая дневная норма воды (в мл)
DAILY_WATER_NORM = 2000