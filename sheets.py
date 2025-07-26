from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import logging

from config import GOOGLE_SHEET_ID, get_current_sheet_name

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка доступа к Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'credentials.json'

def get_service():
    """Создает и возвращает сервис для работы с Google Sheets API"""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=credentials)
    return service

def apply_conditional_formatting(sheet_name):
    """Применяет условное форматирование к колонке статуса выполнения"""
    service = get_service()
    
    # Получаем ID листа
    sheet_id = get_sheet_id_by_name(sheet_name)
    
    try:
        # Пытаемся удалить существующие правила условного форматирования
        # Это может вызвать ошибку, если правил нет, поэтому используем try-except
        service.spreadsheets().batchUpdate(
            spreadsheetId=GOOGLE_SHEET_ID,
            body={"requests": [{"deleteConditionalFormatRule": {"sheetId": sheet_id, "index": 0}}]}
        ).execute()
    except:
        pass
    
    try:
        # Удаляем еще раз, если было два правила
        service.spreadsheets().batchUpdate(
            spreadsheetId=GOOGLE_SHEET_ID,
            body={"requests": [{"deleteConditionalFormatRule": {"sheetId": sheet_id, "index": 0}}]}
        ).execute()
    except:
        pass
    
    # Добавляем новые правила условного форматирования
    add_rules_request = {
        "requests": [
            # Добавить правило для "Выполнил" - зеленый цвет
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,  # Начиная с первой строки данных (после заголовка)
                            "endRowIndex": 100,
                            "startColumnIndex": 5,  # Колонка F (нумерация с 0)
                            "endColumnIndex": 6
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": "Выполнил"}]
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 0.27,
                                    "green": 0.8,
                                    "blue": 0.4
                                }
                            }
                        }
                    },
                    "index": 0
                }
            },
            # Добавить правило для "Не выполнил" - красный цвет
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": 100,
                            "startColumnIndex": 5,
                            "endColumnIndex": 6
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": "Не выполнил"}]
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 0.95,
                                    "green": 0.45,
                                    "blue": 0.45
                                }
                            }
                        }
                    },
                    "index": 1
                }
            }
        ]
    }
    
    service.spreadsheets().batchUpdate(
        spreadsheetId=GOOGLE_SHEET_ID,
        body=add_rules_request
    ).execute()
    
    logger.info(f"Условное форматирование для листа {sheet_name} обновлено")

def ensure_monthly_sheet_exists():
    """
    Проверяет наличие листа для текущего месяца
    Если лист не существует - создает его и добавляет формулы для расчетов
    """
    service = get_service()
    sheet_name = get_current_sheet_name()
    
    # Получение информации о существующих листах
    sheet_metadata = service.spreadsheets().get(spreadsheetId=GOOGLE_SHEET_ID).execute()
    sheets = sheet_metadata.get('sheets', [])
    sheet_names = [sheet.get("properties", {}).get("title", "") for sheet in sheets]
    
    # Если лист для текущего месяца не существует, создаем его
    if sheet_name not in sheet_names:
        logger.info(f"Создание нового листа для {sheet_name}")
        
        # Запрос на добавление нового листа
        body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': sheet_name,
                        'gridProperties': {
                            'rowCount': 100,
                            'columnCount': 10
                        }
                    }
                }
            }]
        }
        
        service.spreadsheets().batchUpdate(
            spreadsheetId=GOOGLE_SHEET_ID,
            body=body
        ).execute()
        
        # Установка заголовков и формул
        # Убрали поле "Детализация" и добавили "Статус выполнения"
        headers = [
            ["Дата", "ID пользователя", "Общее количество (мл)", 
             "Норма дня", "% от нормы", "Статус выполнения", "", "Статистика месяца", "", ""]
        ]
        
        service.spreadsheets().values().update(
            spreadsheetId=GOOGLE_SHEET_ID,
            range=f"{sheet_name}!A1:J1",
            valueInputOption="USER_ENTERED",
            body={"values": headers}
        ).execute()
        
        # Добавление формул для расчета среднего и общего количества
        formulas = [
            ["Среднее за день:", "=IFERROR(AVERAGE(C2:C);\"Нет данных\")", ""],
            ["Общее за месяц:", "=SUM(C2:C)", ""]
        ]

        service.spreadsheets().values().update(
            spreadsheetId=GOOGLE_SHEET_ID,
            range=f"{sheet_name}!H2:J3",
            valueInputOption="USER_ENTERED",
            body={"values": formulas}
        ).execute()
        
        # Форматирование заголовков
        format_request = {
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": get_sheet_id_by_name(sheet_name),
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 10
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.7,
                                    "green": 0.7,
                                    "blue": 1.0
                                },
                                "horizontalAlignment": "CENTER",
                                "textFormat": {
                                    "bold": True
                                }
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                    }
                }
            ]
        }
        
        service.spreadsheets().batchUpdate(
            spreadsheetId=GOOGLE_SHEET_ID,
            body=format_request
        ).execute()
        
        # Применяем условное форматирование для нового листа
        apply_conditional_formatting(sheet_name)
        
        logger.info(f"Лист {sheet_name} создан и настроен")
    else:
        # Если лист уже существует, убедимся, что условное форматирование применено
        apply_conditional_formatting(sheet_name)
        # Обновляем формулы для существующего листа
        update_monthly_formulas(sheet_name)
    
    return sheet_name

def get_sheet_id_by_name(sheet_name):
    """Получает ID листа по его имени"""
    service = get_service()
    sheet_metadata = service.spreadsheets().get(spreadsheetId=GOOGLE_SHEET_ID).execute()
    sheets = sheet_metadata.get('sheets', [])
    
    for sheet in sheets:
        if sheet.get("properties", {}).get("title", "") == sheet_name:
            return sheet.get("properties", {}).get("sheetId", 0)
    
    return 0

def update_monthly_formulas(sheet_name):
    """Обновляет формулы для расчета статистики месяца"""
    service = get_service()
    
    # Получаем текущие данные, чтобы определить правильный диапазон
    result = service.spreadsheets().values().get(
        spreadsheetId=GOOGLE_SHEET_ID,
        range=f"{sheet_name}!A:C"
    ).execute()
    
    rows = result.get('values', [])
    
    # Определяем начальную строку данных (обычно это 2, т.е. после заголовка)
    start_row = 2  # Значение по умолчанию
    
    # Используем динамический диапазон для формул
    # Формулы будут работать со всеми данными в столбце C
    formulas = [
        ["Среднее за день:", f"=IFERROR(AVERAGE(C{start_row}:C);\"Нет данных\")", ""],
        ["Общее за месяц:", f"=SUM(C{start_row}:C)", ""]
    ]

    service.spreadsheets().values().update(
        spreadsheetId=GOOGLE_SHEET_ID,
        range=f"{sheet_name}!H2:J3",
        valueInputOption="USER_ENTERED",
        body={"values": formulas}
    ).execute()
    
    logger.info(f"Формулы для листа {sheet_name} обновлены")

def save_day_results(user_id, date_str, total_amount, logs=None, daily_norm=2000):
    """Сохраняет результаты дня в Google Sheets"""
    # Убедимся, что лист для текущего месяца существует
    sheet_name = ensure_monthly_sheet_exists()
    
    service = get_service()
    
    # Проверяем, есть ли уже данные в таблице
    result = service.spreadsheets().values().get(
        spreadsheetId=GOOGLE_SHEET_ID,
        range=f"{sheet_name}!A:F"
    ).execute()
    
    rows = result.get('values', [])
    
    # Подготовка данных для записи
    percent_of_norm = (total_amount / daily_norm) * 100 if daily_norm > 0 else 0
    
    # Определяем статус выполнения
    status = "Выполнил" if total_amount >= daily_norm else "Не выполнил"
    
    new_row = [
        date_str,
        str(user_id),
        total_amount,
        daily_norm,
        f"{percent_of_norm:.1f}%",
        status
    ]
    
    # Если таблица пустая (кроме заголовка) - добавляем данные прямо в строку 2
    if len(rows) <= 1:
        body = {
            'values': [new_row]
        }
        result = service.spreadsheets().values().update(
            spreadsheetId=GOOGLE_SHEET_ID,
            range=f"{sheet_name}!A2:F2",
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        logger.info(f"Данные добавлены в строку 2")
    else:
        # Иначе добавляем в конец таблицы
        body = {
            'values': [new_row]
        }
        result = service.spreadsheets().values().append(
            spreadsheetId=GOOGLE_SHEET_ID,
            range=f"{sheet_name}!A:F",
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        logger.info(f"Данные добавлены в конец таблицы")
    
    # Применяем условное форматирование
    apply_conditional_formatting(sheet_name)
    
    # Обновляем формулы для статистики
    update_monthly_formulas(sheet_name)
    
    logger.info(f"Данные пользователя {user_id} за {date_str} сохранены")
    return result

def get_weekly_stats(user_id):
    """Получает статистику за последнюю неделю"""
    service = get_service()
    
    # Получаем текущий и предыдущий месяц (для поиска данных)
    current_sheet = get_current_sheet_name()
    
    # Текущий месяц
    today = datetime.now()
    current_month_data = get_stats_from_sheet(service, current_sheet, user_id)
    
    # Если текущий месяц только начался, возможно, нам нужны данные из предыдущего месяца
    if today.day <= 7:
        # Вычисляем имя листа для предыдущего месяца
        previous_month = today.month - 1 if today.month > 1 else 12
        previous_year = today.year if today.month > 1 else today.year - 1
        previous_sheet = f"{datetime.strptime(f'{previous_month}', '%m').strftime('%B')}_{previous_year}"
        
        # Получаем данные из предыдущего месяца
        previous_month_data = get_stats_from_sheet(service, previous_sheet, user_id)
        
        # Объединяем данные
        all_data = previous_month_data + current_month_data
    else:
        all_data = current_month_data
    
    # Фильтруем только данные за последние 7 дней
    week_ago = today.replace(day=today.day-7) if today.day > 7 else today.replace(
        month=previous_month,
        year=previous_year,
        day=today.day-7+30  # Приблизительно
    )
    
    weekly_data = []
    total_amount = 0
    
    for date_str, amount in all_data:
        try:
            row_date = datetime.strptime(date_str, "%Y-%m-%d")
            if week_ago <= row_date <= today:
                weekly_data.append((date_str, amount))
                total_amount += amount
        except (ValueError, TypeError):
            continue
    
    return weekly_data, total_amount

def get_stats_from_sheet(service, sheet_name, user_id):
    """Вспомогательная функция для получения данных с конкретного листа"""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=GOOGLE_SHEET_ID,
            range=f"{sheet_name}!A:C"
        ).execute()
        
        rows = result.get('values', [])
        
        if not rows or len(rows) <= 1:  # Если только заголовки или пусто
            return []
        
        data = []
        
        # Пропускаем заголовок
        for row in rows[1:]:
            if len(row) >= 3 and row[1] == str(user_id):
                try:
                    date_str = row[0]
                    amount = int(row[2])
                    data.append((date_str, amount))
                except (ValueError, IndexError):
                    continue
        
        return data
    except Exception as e:
        logger.error(f"Ошибка при получении данных из листа {sheet_name}: {e}")
        return []