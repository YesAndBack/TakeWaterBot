from sheets import get_service, save_day_results
from datetime import datetime
import json
import logging
import sys
import os
import pickle

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Путь к файлу для сохранения данных пользователей (для целей миграции)
USER_DATA_FILE = "user_data_backup.pkl"

def save_user_data_to_file(user_data, filename=USER_DATA_FILE):
    """Сохраняет данные пользователей в файл для последующей миграции"""
    try:
        with open(filename, 'wb') as f:
            pickle.dump(user_data, f)
        logger.info(f"Данные пользователей сохранены в {filename}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных пользователей: {e}")
        return False

def load_user_data_from_file(filename=USER_DATA_FILE):
    """Загружает данные пользователей из файла"""
    try:
        if not os.path.exists(filename):
            logger.warning(f"Файл {filename} не существует")
            return {}
            
        with open(filename, 'rb') as f:
            user_data = pickle.load(f)
        logger.info(f"Загружены данные пользователей из {filename}, пользователей: {len(user_data)}")
        return user_data
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных пользователей: {e}")
        return {}

def get_bot_user_data():
    """Получает данные пользователей из запущенного бота"""
    try:
        # Импортируем user_data из модуля bot
        from bot import user_data
        
        # Проверяем, есть ли в нем данные
        if user_data and len(user_data) > 0:
            logger.info(f"Получены данные из запущенного бота, пользователей: {len(user_data)}")
            
            # Сохраняем их для последующего использования
            save_user_data_to_file(user_data)
            
            return user_data
        else:
            logger.warning("В боте нет данных пользователей, попробуем загрузить из файла")
            return load_user_data_from_file()
    except ImportError:
        logger.warning("Не удалось импортировать данные из бота, попробуем загрузить из файла")
        return load_user_data_from_file()
    except Exception as e:
        logger.error(f"Ошибка при получении данных из бота: {e}")
        return load_user_data_from_file()

def test_google_sheets_connection():
    """Проверяет подключение к Google Sheets API"""
    try:
        service = get_service()
        logger.info("Успешное подключение к Google Sheets API!")
        return True
    except Exception as e:
        logger.error(f"Ошибка подключения к Google Sheets API: {e}")
        return False

def migrate_user_data(user_id, user_data):
    """Миграция данных одного пользователя в Google Sheets"""
    try:
        # Получаем данные пользователя
        user = user_data.get(user_id)
        if not user:
            logger.warning(f"Данные пользователя {user_id} не найдены")
            return False
        
        # Проверяем наличие данных для миграции
        if not user.get("today_logs") or user.get("total_today", 0) <= 0:
            logger.warning(f"У пользователя {user_id} нет данных для миграции")
            return False
        
        # Получаем сегодняшнюю дату
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Сохраняем данные пользователя
        result = save_day_results(
            user_id,
            today,
            user["total_today"],
            user["today_logs"],
            user.get("daily_norm", 2000)
        )
        
        logger.info(f"Данные пользователя {user_id} успешно мигрированы")
        return True
    except Exception as e:
        logger.error(f"Ошибка при миграции данных пользователя {user_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def migrate_all_users(user_data):
    """Миграция данных всех пользователей в Google Sheets"""
    if not user_data:
        logger.warning("Нет данных пользователей для миграции")
        return 0, 0, 0
        
    logger.info(f"Начинаем миграцию данных для {len(user_data)} пользователей")
    
    # Счетчики для статистики
    success_count = 0
    error_count = 0
    no_data_count = 0
    
    # Проходим по всем пользователям и мигрируем их данные
    for user_id in user_data:
        try:
            logger.info(f"Миграция данных пользователя {user_id}")
            
            # Мигрируем данные пользователя
            result = migrate_user_data(user_id, user_data)
            
            if result:
                success_count += 1
            else:
                no_data_count += 1
        except Exception as e:
            logger.error(f"Критическая ошибка при миграции данных пользователя {user_id}: {e}")
            error_count += 1
    
    # Выводим итоговую статистику
    logger.info(f"Миграция данных завершена")
    logger.info(f"Успешно: {success_count}")
    logger.info(f"Нет данных: {no_data_count}")
    logger.info(f"Ошибки: {error_count}")
    
    return success_count, no_data_count, error_count

def show_usage():
    """Показывает информацию об использовании скрипта"""
    print("Использование скрипта:")
    print(f"python {sys.argv[0]} [опция]")
    print("Опции:")
    print("  --test    - использовать тестовые данные")
    print("  --help    - показать эту справку")
    print("По умолчанию скрипт пытается получить данные из запущенного бота.")

def create_test_users():
    """Создает тестовых пользователей с данными для миграции"""
    # В реальном приложении здесь бы загружались данные из БД или файла
    test_users = {}
    
    # Текущая дата для логов
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Тестовый пользователь 1
    test_users[123456789] = {
        "total_today": 1500,
        "daily_norm": 2000,
        "today_logs": [
            {
                "time": "08:30",
                "date": today,
                "amount": 300,
                "status": "выпил"
            },
            {
                "time": "12:30",
                "date": today,
                "amount": 450,
                "status": "выпил"
            },
            {
                "time": "15:30",
                "date": today,
                "amount": 400,
                "status": "выпил"
            },
            {
                "time": "19:00",
                "date": today,
                "amount": 350,
                "status": "выпил"
            }
        ]
    }
    
    # Тестовый пользователь 2
    test_users[987654321] = {
        "total_today": 2200,
        "daily_norm": 2500,
        "today_logs": [
            {
                "time": "07:45",
                "date": today,
                "amount": 500,
                "status": "выпил"
            },
            {
                "time": "11:20",
                "date": today,
                "amount": 300,
                "status": "выпил"
            },
            {
                "time": "14:00",
                "date": today,
                "amount": 400,
                "status": "выпил"
            },
            {
                "time": "16:30",
                "date": today,
                "amount": 500,
                "status": "выпил"
            },
            {
                "time": "20:00",
                "date": today,
                "amount": 500,
                "status": "выпил"
            }
        ]
    }
    
    logger.info(f"Создано {len(test_users)} тестовых пользователей")
    return test_users

if __name__ == "__main__":
    # Проверяем аргументы командной строки
    use_test_data = False
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            use_test_data = True
        elif sys.argv[1] == "--help":
            show_usage()
            sys.exit(0)
    
    logger.info("Начинаем проверку подключения к Google Sheets и миграцию данных...")
    
    # Тест подключения
    connection_result = test_google_sheets_connection()
    if not connection_result:
        logger.error("Тест подключения не пройден. Проверьте настройки и credentials.json")
        sys.exit(1)
    
    # Получаем данные пользователей
    if use_test_data:
        logger.info("Используем тестовые данные для миграции")
        user_data = create_test_users()
    else:
        logger.info("Пытаемся получить данные пользователей из бота")
        user_data = get_bot_user_data()
    
    # Проверяем, есть ли данные для миграции
    if not user_data:
        logger.warning("Не удалось получить данные пользователей для миграции")
        logger.info("Попробуйте запустить с опцией --test для использования тестовых данных")
        sys.exit(1)
    
    # Миграция данных всех пользователей
    success, no_data, errors = migrate_all_users(user_data)
    
    if errors > 0:
        logger.warning(f"Миграция завершена с ошибками: {errors} пользователей не удалось мигрировать")
    elif success == 0:
        logger.warning("Миграция завершена, но ни одного пользователя не удалось мигрировать")
    else:
        logger.info(f"Миграция успешно завершена! Мигрировано пользователей: {success}")