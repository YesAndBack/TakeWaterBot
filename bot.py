from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging
import json
from datetime import datetime

from config import BOT_TOKEN, DAILY_WATER_NORM
from sheets import get_weekly_stats, save_day_results

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Определение состояний бота для конечного автомата
class WaterForm(StatesGroup):
    waiting = State()        # Ожидание действий пользователя
    amount = State()         # Ожидание ввода количества выпитой воды
    norm = State()           # Ожидание ввода дневной нормы

# Хранилище данных пользователей (в реальном приложении лучше использовать базу данных)
user_data = {}

# Создание основного меню с кнопками
def get_main_keyboard():
    """Создает основную клавиатуру с кнопками команд"""
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text="💧 Записать выпитую воду"),
                types.KeyboardButton(text="📊 Статистика")
            ],
            [
                types.KeyboardButton(text="⚙️ Изменить норму"),
                types.KeyboardButton(text="ℹ️ Помощь")
            ]
        ],
        resize_keyboard=True,
        persistent=True
    )
    return keyboard

# Функция инициализации данных пользователя
def init_user_data(user_id):
    """Инициализирует структуру данных для нового пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {
            "today_logs": [],
            "total_today": 0,
            "daily_norm": DAILY_WATER_NORM
        }
    
    # Проверяем, не новый ли день
    today = datetime.now().strftime("%Y-%m-%d")
    last_log_date = None
    
    if user_data[user_id]["today_logs"]:
        try:
            # Получаем дату последней записи (если есть)
            last_log = user_data[user_id]["today_logs"][-1]
            if "date" in last_log:
                last_log_date = last_log["date"]
        except (IndexError, KeyError):
            pass
    
    # Если новый день, сбрасываем данные
    if last_log_date != today:
        user_data[user_id]["today_logs"] = []
        user_data[user_id]["total_today"] = 0
    
    return user_data[user_id]

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Инициализация данных пользователя
    init_user_data(user_id)
    user_data = init_user_data(user_id)
    logger.info(f"Инициализированы данные пользователя {user_id}: {user_data}")
    
    await state.set_state(WaterForm.waiting)
    
    logger.info(f"Пользователь {user_name} с ID {user_id} запустил бота")
    
    # Приветственное сообщение с клавиатурой
    await message.answer(
        f"Привет, {user_name}! 👋\n\n"
        f"Я бот-напоминалка о питье воды. Я буду отправлять тебе напоминания "
        f"в течение дня, чтобы ты не забывал(а) пить воду.\n\n"
        f"Твоя дневная норма: {DAILY_WATER_NORM} мл.\n\n"
        f"Используй кнопки меню для управления ботом:\n"
        f"💧 Записать выпитую воду - записать количество выпитой воды\n"
        f"📊 Статистика - посмотреть статистику за неделю\n"
        f"⚙️ Изменить норму - установить свою дневную норму\n"
        f"ℹ️ Помощь - показать это сообщение снова\n\n"
        f"Желаю хорошего дня и правильного водного баланса! 💧",
        reply_markup=get_main_keyboard()
    )

# Обработчик команды для тестирования напоминаний
@dp.message(Command("testreminder"))
async def cmd_testreminder(message: types.Message):
    user_id = message.from_user.id
    current_time = datetime.now().strftime("%H:%M")
    
    try:
        await send_reminder(user_id, current_time)
        await message.answer("Тестовое напоминание отправлено!")
    except Exception as e:
        await message.answer(f"Ошибка при отправке напоминания: {str(e)}")

# Обработчик команды /stats
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    
    # Получаем статистику за неделю из Google Sheets
    weekly_data, total_amount = get_weekly_stats(user_id)
    
    # Добавляем сегодняшние данные, которые еще не записаны в таблицу
    today = datetime.now().strftime("%Y-%m-%d")
    today_amount = 0
    
    if user_id in user_data:
        today_amount = user_data[user_id]["total_today"]
    
    # Проверяем, есть ли уже сегодняшние данные в weekly_data
    today_in_stats = False
    for date, amount in weekly_data:
        if date == today:
            today_in_stats = True
            break
    
    # Если сегодняшних данных еще нет в статистике, добавляем их
    if not today_in_stats and today_amount > 0:
        weekly_data.append((today, today_amount))
        total_amount += today_amount
    
    if not weekly_data:
        await message.answer(
            "У тебя пока нет данных о потреблении воды за последнюю неделю.\n"
            "Начни пить воду и отмечать это в боте!",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Формируем сообщение со статистикой
    stats_text = "📊 *Статистика питья воды за последнюю неделю:*\n\n"
    
    for date, amount in weekly_data:
        # Преобразуем формат даты для лучшей читаемости
        try:
            formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
        except ValueError:
            formatted_date = date
        
        # Добавляем emoji в зависимости от количества выпитой воды
        emoji = "🔴" if amount < 1000 else "🟡" if amount < 1500 else "🟢"
        stats_text += f"{emoji} {formatted_date}: *{amount}* мл\n"
    
    # Средний показатель в день
    avg_daily = total_amount / len(weekly_data) if weekly_data else 0
    
    # Добавляем итоговую статистику
    stats_text += f"\n💧 Всего за неделю: *{total_amount}* мл"
    stats_text += f"\n⚖️ В среднем в день: *{int(avg_daily)}* мл"
    
    # Добавляем оценку водного баланса
    if avg_daily < 1000:
        stats_text += "\n\n⚠️ Ты пьешь слишком мало воды. Рекомендуется увеличить потребление!"
    elif avg_daily < 1500:
        stats_text += "\n\n🔔 Ты пьешь меньше рекомендуемой нормы. Постарайся пить больше!"
    elif avg_daily < 2000:
        stats_text += "\n\n👍 Неплохо! Ты приближаешься к рекомендуемой норме."
    else:
        stats_text += "\n\n🏆 Отлично! Ты поддерживаешь хороший водный баланс."
    
    await message.answer(stats_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

# Обработчик команды /setnorm
@dp.message(Command("setnorm"))
async def cmd_setnorm(message: types.Message):
    args = message.text.split()
    user_id = message.from_user.id
    
    # Инициализация данных пользователя, если они еще не созданы
    init_user_data(user_id)
    
    # Проверяем, указана ли норма в команде
    if len(args) > 1:
        try:
            new_norm = int(args[1])
            if new_norm <= 0:
                await message.answer("Норма должна быть положительным числом!", reply_markup=get_main_keyboard())
                return
            
            # Устанавливаем новую норму
            user_data[user_id]["daily_norm"] = new_norm
            await message.answer(f"Установлена новая дневная норма: {new_norm} мл.", reply_markup=get_main_keyboard())
        except ValueError:
            await message.answer("Пожалуйста, укажите норму в виде числа. Например: /setnorm 2500", reply_markup=get_main_keyboard())
    else:
        # Если норма не указана, показываем текущую и инструкцию
        current_norm = user_data[user_id]["daily_norm"]
        await message.answer(
            f"Текущая дневная норма: {current_norm} мл.\n"
            f"Чтобы изменить, используйте команду /setnorm с числом. Например: /setnorm 2500",
            reply_markup=get_main_keyboard()
        )

# Обработчик команды /drink
@dp.message(Command("drink"))
async def cmd_drink(message: types.Message, state: FSMContext):
    await state.set_state(WaterForm.amount)
    
    # Предлагаем стандартные варианты объема
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="150 мл", callback_data="amount_150"),
            types.InlineKeyboardButton(text="200 мл", callback_data="amount_200"),
            types.InlineKeyboardButton(text="250 мл", callback_data="amount_250")
        ],
        [
            types.InlineKeyboardButton(text="300 мл", callback_data="amount_300"),
            types.InlineKeyboardButton(text="500 мл", callback_data="amount_500"),
            types.InlineKeyboardButton(text="Другое", callback_data="amount_custom")
        ]
    ])
    
    await message.answer("Сколько воды ты выпил(а)?", reply_markup=keyboard)

# Обработчик кнопки "Записать выпитую воду"
@dp.message(lambda message: message.text == "💧 Записать выпитую воду")
async def button_drink(message: types.Message, state: FSMContext):
    await cmd_drink(message, state)

# Обработчик кнопки "Статистика"
@dp.message(lambda message: message.text == "📊 Статистика")
async def button_stats(message: types.Message):
    await cmd_stats(message)

# Обработчик кнопки "Изменить норму"
@dp.message(lambda message: message.text == "⚙️ Изменить норму")
async def button_setnorm(message: types.Message):
    user_id = message.from_user.id
    user = init_user_data(user_id)
    current_norm = user["daily_norm"]
    
    # Создаем инлайн-клавиатуру с вариантами норм
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="1500 мл", callback_data="norm_1500"),
            types.InlineKeyboardButton(text="2000 мл", callback_data="norm_2000"),
            types.InlineKeyboardButton(text="2500 мл", callback_data="norm_2500")
        ],
        [
            types.InlineKeyboardButton(text="3000 мл", callback_data="norm_3000"),
            types.InlineKeyboardButton(text="Другое", callback_data="norm_custom")
        ]
    ])
    
    await message.answer(
        f"Твоя текущая дневная норма: {current_norm} мл.\n"
        f"Выбери новую норму или введи свое значение:",
        reply_markup=keyboard
    )

# Обработчик кнопки "Помощь"
@dp.message(lambda message: message.text == "ℹ️ Помощь")
async def button_help(message: types.Message):
    user_name = message.from_user.first_name
    
    await message.answer(
        f"Привет, {user_name}! 👋\n\n"
        f"Я бот-напоминалка о питье воды. Я буду отправлять тебе напоминания "
        f"в течение дня, чтобы ты не забывал(а) пить воду.\n\n"
        f"Используй кнопки меню для управления ботом:\n"
        f"💧 Записать выпитую воду - записать количество выпитой воды\n"
        f"📊 Статистика - посмотреть статистику за неделю\n"
        f"⚙️ Изменить норму - установить свою дневную норму\n"
        f"ℹ️ Помощь - показать это сообщение снова\n\n"
        f"Ссылка на таблицу с результатами - https://docs.google.com/spreadsheets/d/1fTTRnqbz0rUJ1cdt9TovPkROrYL5bnTUlepKPK9L5tU/edit?usp=sharing \n\n"
        f"Желаю хорошего дня и правильного водного баланса! 💧",
        reply_markup=get_main_keyboard()
    )

# Обработчик нажатия на кнопки с фиксированным объемом
@dp.callback_query(lambda c: c.data.startswith("amount_"))
async def process_amount_button(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    amount_str = callback.data.split("_")[1]
    
    # Инициализация данных пользователя
    user = init_user_data(user_id)
    
    if amount_str == "custom":
        await callback.message.answer("Введи количество выпитой воды в мл (только число):")
        await callback.answer()
        return
    
    # Обработка фиксированного объема
    try:
        amount = int(amount_str)
        current_time = datetime.now()
        time_str = current_time.strftime("%H:%M")
        date_str = current_time.strftime("%Y-%m-%d")
        
        # Записываем информацию о выпитой воде
        user["today_logs"].append({
            "time": time_str,
            "date": date_str,
            "amount": amount,
            "status": "выпил"
        })
        user["total_today"] += amount
        
        # Рассчитываем процент от дневной нормы
        percent = (user["total_today"] / user["daily_norm"]) * 100
        
        await state.set_state(WaterForm.waiting)
        
        await callback.message.answer(
            f"Отлично! Записал {amount} мл.\n\n"
            f"Сегодня ты выпил(а) всего: {user['total_today']} мл.\n"
            f"Это {percent:.1f}% от твоей дневной нормы.",
            reply_markup=get_main_keyboard()
        )
        
        # Если выполнена или превышена дневная норма
        if percent >= 100 and percent < 120:
            await callback.message.answer("🎉 Поздравляю! Ты выполнил(а) дневную норму!")
        elif percent >= 120:
            await callback.message.answer("💪 Вау! Ты превысил(а) свою норму на 20% и более. Отличная работа!")
    
    except ValueError:
        await callback.message.answer("Произошла ошибка. Пожалуйста, попробуй еще раз.")
    
    await callback.answer()

# Обработчик нажатия на кнопки с выбором нормы
@dp.callback_query(lambda c: c.data.startswith("norm_"))
async def process_norm_button(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    norm_str = callback.data.split("_")[1]
    
    # Инициализация данных пользователя
    user = init_user_data(user_id)
    
    if norm_str == "custom":
        await callback.message.answer("Введи желаемую дневную норму в мл (только число):")
        await state.set_state(WaterForm.norm)
        await callback.answer()
        return
    
    # Обработка выбора готовой нормы
    try:
        new_norm = int(norm_str)
        
        # Устанавливаем новую норму
        user["daily_norm"] = new_norm
        
        await callback.message.answer(
            f"Установлена новая дневная норма: {new_norm} мл.",
            reply_markup=get_main_keyboard()
        )
    except ValueError:
        await callback.message.answer("Произошла ошибка. Пожалуйста, попробуй еще раз.")
    
    await callback.answer()

# Обработчик ввода пользовательской нормы
@dp.message(WaterForm.norm)
async def process_custom_norm(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Инициализация данных пользователя
    user = init_user_data(user_id)
    
    try:
        new_norm = int(message.text)
        if new_norm <= 0:
            await message.answer("Норма должна быть положительным числом. Попробуй еще раз.")
            return
        
        # Устанавливаем новую норму
        user["daily_norm"] = new_norm
        
        await state.set_state(WaterForm.waiting)
        
        await message.answer(
            f"Установлена новая дневная норма: {new_norm} мл.",
            reply_markup=get_main_keyboard()
        )
    except ValueError:
        await message.answer("Пожалуйста, введи число (только цифры). Попробуй еще раз.")

# Обработчик ввода произвольного количества
@dp.message(WaterForm.amount)
async def process_custom_amount(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Инициализация данных пользователя
    user = init_user_data(user_id)
    
    try:
        amount = int(message.text)
        if amount <= 0:
            await message.answer("Количество должно быть положительным числом. Попробуй еще раз.")
            return
        
        current_time = datetime.now()
        time_str = current_time.strftime("%H:%M")
        date_str = current_time.strftime("%Y-%m-%d")
        
        # Записываем информацию о выпитой воде
        user["today_logs"].append({
            "time": time_str,
            "date": date_str,
            "amount": amount,
            "status": "выпил"
        })
        user["total_today"] += amount
        
        # Рассчитываем процент от дневной нормы
        percent = (user["total_today"] / user["daily_norm"]) * 100
        
        await state.set_state(WaterForm.waiting)
        
        await message.answer(
            f"Отлично! Записал {amount} мл.\n\n"
            f"Сегодня ты выпил(а) всего: {user['total_today']} мл.\n"
            f"Это {percent:.1f}% от твоей дневной нормы.",
            reply_markup=get_main_keyboard()
        )
        
        # Если выполнена или превышена дневная норма
        if percent >= 100 and percent < 120:
            await message.answer("🎉 Поздравляю! Ты выполнил(а) дневную норму!")
        elif percent >= 120:
            await message.answer("💪 Вау! Ты превысил(а) свою норму на 20% и более. Отличная работа!")
    
    except ValueError:
        await message.answer("Пожалуйста, введи число (только цифры). Попробуй еще раз.")

# Функция для отправки напоминания
async def send_reminder(user_id, time):
    """Отправляет напоминание о питье воды пользователю"""
    
    # Инициализация данных пользователя
    user = init_user_data(user_id)
    
    # Рассчитываем, сколько осталось до нормы
    remaining = max(0, user["daily_norm"] - user["total_today"])
    
    # Создаем клавиатуру для ответа
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="Да, выпил(а)", callback_data=f"drank_{time}"),
            types.InlineKeyboardButton(text="Нет", callback_data=f"not_drank_{time}")
        ]
    ])
    
    # Формируем сообщение с напоминанием
    message_text = f"💧 <b>Время пить воду!</b>\n\nСейчас {time}.\n\n"
    
    if remaining > 0:
        message_text += f"Сегодня ты выпил(а): {user['total_today']} мл.\n"
        message_text += f"Осталось до нормы: {remaining} мл.\n\n"
    else:
        message_text += f"Отлично! Ты уже выпил(а) дневную норму: {user['total_today']} мл.\n\n"
    
    message_text += "Не забудь увлажниться! Выпил(а) воду?"
    
    try:
        await bot.send_message(
            user_id,
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        logger.info(f"Отправлено напоминание пользователю {user_id} в {time}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
        
        # Пробуем отправить без форматирования в случае ошибки
        try:
            plain_text = message_text.replace("<b>", "").replace("</b>", "")
            await bot.send_message(
                user_id,
                plain_text,
                reply_markup=keyboard,
                parse_mode=None
            )
            logger.info(f"Отправлено напоминание без форматирования пользователю {user_id}")
            return True
        except Exception as e2:
            logger.error(f"Повторная ошибка при отправке напоминания: {e2}")
            return False

# Обработчик нажатия на кнопку "Да, выпил(а)" в напоминании
@dp.callback_query(lambda c: c.data.startswith("drank_"))
async def process_reminder_drank(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(reminder_time=callback.data.split("_")[1])
    await state.set_state(WaterForm.amount)
    
    # Предлагаем стандартные варианты объема
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="150 мл", callback_data="amount_150"),
            types.InlineKeyboardButton(text="200 мл", callback_data="amount_200"),
            types.InlineKeyboardButton(text="250 мл", callback_data="amount_250")
        ],
        [
            types.InlineKeyboardButton(text="300 мл", callback_data="amount_300"),
            types.InlineKeyboardButton(text="500 мл", callback_data="amount_500"),
            types.InlineKeyboardButton(text="Другое", callback_data="amount_custom")
        ]
    ])
    
    await callback.message.answer("Отлично! Сколько мл воды ты выпил(а)?", reply_markup=keyboard)
    await callback.answer()

# Обработчик нажатия на кнопку "Нет" в напоминании
@dp.callback_query(lambda c: c.data.startswith("not_drank_"))
async def process_reminder_not_drank(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    time = callback.data.split("_")[1]
    
    # Инициализация данных пользователя
    user = init_user_data(user_id)
    
    # Записываем информацию о пропущенном питье
    current_time = datetime.now()
    date_str = current_time.strftime("%Y-%m-%d")
    
    user["today_logs"].append({
        "time": time,
        "date": date_str,
        "amount": 0,
        "status": "не выпил"
    })
    
    await callback.message.answer(
        "Хорошо, я записал, что ты пропустил(а) этот прием воды.\n"
        "Постарайся не забывать пить воду регулярно для поддержания водного баланса! 💧\n"
        "Следующее напоминание придет по расписанию.",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

@dp.message(Command("save"))
async def cmd_save(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in user_data or not user_data[user_id]["today_logs"]:
        await message.answer("У тебя нет данных для сохранения!")
        return
    
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        save_day_results(
            user_id,
            today,
            user_data[user_id]["total_today"],
            daily_norm=user_data[user_id]["daily_norm"]
        )
        await message.answer("Данные успешно сохранены в Google Sheets!")
    except Exception as e:
        await message.answer(f"Ошибка при сохранении данных: {str(e)}")