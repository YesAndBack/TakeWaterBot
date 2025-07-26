from datetime import datetime
import logging
import json
import sys
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Импортируем функцию сохранения из вашего модуля sheets
from sheets import save_day_results

def save_bot_data_to_sheets():
    """Функция для сохранения реальных данных из бота в Google Sheets"""
    
    try:
        # Импортируем данные из бота
        from bot import user_data
        
        # Проверяем, есть ли данные
        if not user_data:
            logger.error("В боте нет данных пользователей. Нечего сохранять.")
            return False
        
        logger.info(f"Получены данные из бота. Пользователей: {len(user_data)}")
        
        # Выводим информацию о данных каждого пользователя
        for user_id, data in user_data.items():
            logs = data.get("today_logs", [])
            total = data.get("total_today", 0)
            logger.info(f"Пользователь {user_id}: записей - {len(logs)}, всего - {total} мл")
        
        # Счетчик успешно сохраненных записей
        success_count = 0
        
        # Сохраняем данные каждого пользователя
        today = datetime.now().strftime("%Y-%m-%d")
        
        for user_id, data in user_data.items():
            try:
                # Проверяем наличие необходимых данных
                if "today_logs" not in data or "total_today" not in data:
                    logger.warning(f"У пользователя {user_id} отсутствуют необходимые поля данных")
                    continue
                
                logs = data["today_logs"]
                total_today = data["total_today"]
                
                # Проверяем, есть ли у пользователя данные для сохранения
                if not logs or total_today == 0:
                    logger.info(f"У пользователя {user_id} нет данных для сохранения")
                    continue
                
                # Получаем дневную норму
                daily_norm = data.get("daily_norm", 2000)
                
                # Выводим детальную информацию о логах
                logger.info(f"Записи пользователя {user_id}:")
                for i, log in enumerate(logs):
                    logger.info(f"  Запись {i+1}: время {log.get('time', 'н/д')}, "
                                f"количество {log.get('amount', 0)} мл, "
                                f"статус '{log.get('status', 'н/д')}'")
                
                # Сохраняем данные пользователя
                result = save_day_results(
                    user_id,
                    today,
                    total_today,
                    logs,
                    daily_norm
                )
                
                logger.info(f"Данные пользователя {user_id} успешно сохранены: {total_today} мл")
                success_count += 1
            except Exception as e:
                logger.error(f"Ошибка при сохранении данных пользователя {user_id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        if success_count > 0:
            logger.info(f"Всего успешно сохранено записей: {success_count}")
            return True
        else:
            logger.error("Не удалось сохранить ни одной записи из данных бота")
            return False
            
    except (ImportError, AttributeError) as e:
        logger.error(f"Ошибка при импорте данных из бота: {e}")
        logger.error("Убедитесь, что бот запущен и доступен для импорта")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Начинаем сохранение данных из бота в Google Sheets...")
    
    # Запускаем сохранение данных
    success = save_bot_data_to_sheets()
    
    if success:
        logger.info("Данные успешно сохранены в Google Таблицу!")
    else:
        logger.error("Не удалось сохранить данные. Проверьте, запущен ли бот и есть ли в нем данные.")