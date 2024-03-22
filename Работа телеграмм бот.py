from aiogram.types import Message, ReplyKeyboardMarkup, InlineKeyboardMarkup, CallbackQuery, InputTextMessageContent, InlineQueryResultArticle, InlineQuery
import logging.handlers
import logging
import os
import aiogram
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
import sqlite3 
from datetime import datetime, date, time

# Логирование.
logger = logging.getLogger(__name__)

# Записываем в переменную результат логирования
os.makedirs("Logs", exist_ok=True)

# Cоздаёт все промежуточные каталоги, если они не существуют.
logging.basicConfig(  # Чтобы бот работал успешно, создаём конфиг с базовыми данными для бота
    level=logging.INFO,
    format="[%(levelname)-8s %(asctime)s at           %(funcName)s]: %(message)s",
    datefmt="%d.%d.%Y %H:%M:%S",
    handlers=[logging.handlers.RotatingFileHandler("Logs/     TGBot.log", maxBytes=10485760, backupCount=0),
    logging.StreamHandler()])

# Создаём Telegram бота и диспетчер:
Bot = aiogram.Bot("5891681954:AAHnkOkVpyRI3oZjwckgHiGwZnmwF_gfk4M")
DP = aiogram.Dispatcher(Bot, storage=MemoryStorage())


def adapt_timeobj(timeobj):
    return ((3600*timeobj.hour + 60*timeobj.minute + timeobj.second)*10**6 
            + timeobj.microsecond)


def convert_timeobj(val):
    val = int(val)
    hour, val = divmod(val, 3600*10**6)
    minute, val = divmod(val, 60*10**6)
    second, val = divmod(val, 10**6)
    microsecond = int(val)
    return time(hour, minute, second, microsecond)


sqlite3.register_adapter(time, adapt_timeobj)
sqlite3.register_converter("timeobj", convert_timeobj)
conn = sqlite3.connect('база_данных.db', detect_types=sqlite3.PARSE_DECLTYPES)
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS user(
id INT,
name TEXT,
join_to_job timeobj,
leave_from_job timeobj,
Scoreboard INT
);""")


@DP.message_handler(commands=["start"])      # КОГДА ПОЛЬЗОВАТЕЛЬ ПИШЕТ /start
async def start(msg: Message):
    keyboard = ReplyKeyboardMarkup()
    keyboard.add(*['Вышел на работу', 'Ушел с работы', 'Админ', 'Получить табель'])

    if (msg.from_user.id,) not in cur.execute("SELECT id FROM user").fetchall():
        cur.execute("INSERT INTO user VALUES (?, ?, ?, ?, ?)",(msg.from_user.id, msg.from_user.full_name, "", "", 0))
        conn.commit()
        await msg.answer("Добавил тебя в бд", reply_markup=keyboard)
    else:
        await msg.answer("Добавил клавиатуру", reply_markup=keyboard)


@DP.message_handler()
async def ReplyKeyboard_handling(msg: Message):  # Обработка запросов с клавиатуры

    if msg.text == 'Вышел на работу':
        cur.execute("UPDATE user SET join_to_job = ? WHERE id = ?", (datetime.now().time().replace(microsecond=0), msg.from_user.id))
        conn.commit()
        await msg.answer("Записал вход в бд")

    if msg.text == 'Ушел с работы':

        cur.execute("UPDATE user SET leave_from_job = ? WHERE id = ?",(datetime.now().time().replace(microsecond=0), msg.from_user.id))
        conn.commit()
        await msg.answer("Записал уход в бд")

    if msg.text == 'Получить табель':
        result = cur.execute("SELECT join_to_job, leave_from_job FROM user WHERE id = ?", (msg.from_user.id,)).fetchone()
        join_to_job = result[0]
        leave_from_job = result[1]
        time = datetime.combine(date.min, leave_from_job) - datetime.combine(date.min, join_to_job)
        time = int(time.total_seconds() / 60)
        scoreboard = int(((1800/22/8/60)*time))
        cur.execute("UPDATE user SET Scoreboard = ? WHERE id = ?",(scoreboard, msg.from_user.id))
        conn.commit()
        await msg.answer("Твоя зп = {} сомони".format(scoreboard))

    if msg.text == 'Админ':
        users = cur.execute("SELECT * FROM user").fetchall()
        for user in users:
            await msg.answer(f'Статистика пользователя "{user[1]}": \nВышел на работу: {user[2]} \nУшёл с работы: {user[3]} \nТабель: {user[4]}')


if __name__ == "__main__":  # Если файл запускается как самостоятельный, а не как модуль
    logger.info("Запускаю бота...")  # В консоле будет отоброжён процесс запуска бота
    executor.start_polling(  # Бот начинает работать
        dispatcher=DP,  # Передаем в функцию диспетчер
        # (диспетчер отвечает за то, чтобы сообщения пользователя доходили до бота)
        on_startup=logger.info("Загрузился успешно!"), skip_updates=True)
    # Если бот успешно загрузился, то в консоль выведется сообщение