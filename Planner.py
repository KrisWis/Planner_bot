from aiogram.types import Message, ReplyKeyboardMarkup, InlineKeyboardMarkup, CallbackQuery
import logging.handlers
import logging
import os
import aiogram
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
import datetime
import asyncio
import json
import pytz
import operator
import dotenv

dotenv.load_dotenv()

async def populateDict(user_id: int):  # Функция создания словаря
    """
    Заполняет dict `USERS` стандартными значениями, если ничего не было найдено."""

    if str(user_id) in USERS:
        return

    USERS.update({
        str(user_id): {
        "Username": None,
        "Paragraph_date": [],
        "Paragraph_time": [],
        "Paragraph_text": [],
        "Plan_number": 0,
        'Experience': 0,
        "settings_delete_item": True,
        "settings_time_zone": "Europe/Moscow"
        }
    })


def saveDB(filename = "UsersDB.jsonc"):  # Сохранение словаря в json файл
  """
  Сохраняет содержимое базы данных в файл.
  """

  global USERS

  json.dump(
    USERS,
    open(filename, "w", encoding="utf-8"), ensure_ascii=False
  )


def loadDB(filename = "UsersDB.jsonc", default = {}):  # Загрузка словаря из json файла

    if not os.path.exists(filename):
        return default

    return json.load(open(filename, encoding="utf-8"))


USERS = loadDB()
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
Bot = aiogram.Bot(os.environ["TOKEN"])
DP = aiogram.Dispatcher(Bot, storage=MemoryStorage())
USERS_BGTASKS = {}  # Фоновые задачи для каждого пользователя

class UserState(StatesGroup):  # Создаём состояния
    name = State()  # Состояние имени

    date = State()  # Состояние даты
    time = State()  # Состояние времени
    text = State()  # Состояние текста

async def find_user_plan(user_id):  # Создаем функцию, которая находит план пользователя в таблицах
    # Сохраняем в переменную план пользователя по индексу
    plan = [USERS[user_id][i] for i in USERS[user_id].keys()]
    result = []
    for j in range(0, len(USERS[user_id]["Paragraph_text"])):
        result.append("\n------------------------------------------------------------------"
                        "\nПункт {}\n\nДата: {}\n\nВремя: {}\n\nТекст: {}".format(j + 1, plan[1][j], plan[2][j], plan[3][j]))

    return "".join(result)


async def end_of_filling(user_id, state):
    data = await state.get_data()
    now = datetime.datetime.now(pytz.timezone(USERS[user_id]["settings_time_zone"]))
    user_date = now.replace(year=int(data['date'][0:4]), month=int(data['date'][5:7]), day=int(data['date'][8:10]))
    user_time = now.replace(hour=int(data['time'][0:2]), minute=int(data['time'][3:5]), second=int(data['time'][6:8]))

    if now > user_date and now > user_time:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(aiogram.types.InlineKeyboardButton(
            text='Добавить пункт ➕',
            callback_data='Добавить пункт ➕'
        ))

        await Bot.send_message(user_id, "Ошибка! Введите данные заново! ❌", reply_markup=keyboard)
        await state.finish()

    else:
        keyboard = InlineKeyboardMarkup()
        for i in ['Всё верно✅', 'Редактировать дату 🖊', 'Редактировать время 🖊', "Редактировать текст 🖊"]:
            keyboard.add(aiogram.types.InlineKeyboardButton(
                text=i,
                callback_data=i
            ))
        data = await state.get_data()
        await Bot.send_message(user_id,
                            f"📝 Твой пункт, который будет записан в план: \n\nДата: {data['date']}\n\nВремя: {data['time']}\n\nТекст плана: \n\n{data['text']}",
                            reply_markup=keyboard)
        await state.reset_state(
            with_data=False)  # Очистка всех состояний пользователя без удаления сохранённых данных


async def Bot_sends_message_when_time_comes(user_id):
    time = USERS[user_id]["Paragraph_time"][-1]
    date = USERS[user_id]["Paragraph_date"][-1]
    text = USERS[user_id]["Paragraph_text"][-1]
    user_date = datetime.datetime.now(pytz.timezone(USERS[user_id]["settings_time_zone"])).replace(year=int(date[0:4]), month=int(date[5:7]), day=int(date[8:10]))
    user_time = datetime.datetime.now(pytz.timezone(USERS[user_id]["settings_time_zone"])).replace(hour=int(time[0:2]), minute=int(time[3:5]), second=int(time[6:8]))
    while int(user_id) in USERS_BGTASKS:
        now = datetime.datetime.now(pytz.timezone(USERS[user_id]["settings_time_zone"]))
        if now >= user_date and now >= user_time: 
            await Bot.send_message(user_id, 'Оповещение! 🔔 \nНаступило время пункта {} с текстом: \n{}\n\n{}'.format(USERS[user_id]["Paragraph_text"].index(text) + 1, text, 'Так как сработало оповещение, то пункт удалён из плана.❌\nПри желании, вы можете изменить это, нажав кнопку "Настройки ⚙️"' if USERS[user_id]["settings_delete_item"] else ''))
            USERS[user_id]["Experience"] += 10

            if USERS[user_id]["settings_delete_item"]:
                USERS[user_id]["Paragraph_date"].remove(date)
                USERS[user_id]["Paragraph_time"].remove(time)
                USERS[user_id]["Paragraph_text"].remove(text)
                USERS[user_id]["Plan_number"] -= 1

            saveDB()

            USERS_BGTASKS[user_id][USERS[user_id]["Plan_number"]].cancel()
            del USERS_BGTASKS[user_id][USERS[user_id]["Plan_number"]]

        await asyncio.sleep(5)


@DP.message_handler(commands=["start"])      # КОГДА ПОЛЬЗОВАТЕЛЬ ПИШЕТ /start
async def start(msg: Message):

    if str(msg.from_user.id) not in USERS:  # и проверяем есть ли в этом спике пользователь
        await msg.answer("Привет!👋 \n\nЯ Telegram бот, который поможет тебе установить собственный план на день, неделю или месяц вперёд! 📝"
                         "\nЧтобы начать пользоваться ботом, напиши мне своё имя!")

        await populateDict(msg.from_user.id)
        await UserState.name.set()

    else:
        keyboard = ReplyKeyboardMarkup()
        keyboard.add(*['Показать план 🗓', 'Редактировать план 📝', 'Настройки ⚙️', 'Мой Профиль 👤', 'Таблица Лидеров 🏆'])
        await msg.answer("Привет!👋 \n\nЯ Telegram бот, который поможет тебе установить собственный план на день, неделю или месяц вперёд! 📝", reply_markup=keyboard)


@DP.message_handler(state=UserState.name)  # Когда появляется состояние с name
async def adding_name_to_google_table(msg: Message, state: FSMContext):

    numbers_to_name = {msg.from_user.id: 1}  # В переменную будут записываться цифры, которые будут прибавляться к нику

    names = [USERS[i]['Username'] for i in USERS.keys()] # Берем имена

    # Делаем проверку на то, есть ли его имя в столбце
    while msg.text in names:  # Пока имя все еще не оригинальное, то прибавляем к нему цифры

        msg.text += str(numbers_to_name[msg.from_user.id])
        if msg.text in names:
            msg.text = msg.text[0:-1]  # Отнимаем первую цифру, чтобы прибавить другую
            numbers_to_name[msg.from_user.id] += 1
        else:
            break
        
    USERS[str(msg.from_user.id)]["Username"] = msg.text
    USERS_BGTASKS[msg.from_user.id] = []
    saveDB()

    keyboard = ReplyKeyboardMarkup()
    keyboard.add(*['Показать план 🗓', 'Редактировать план 📝', 'Настройки ⚙️', 'Мой Профиль 👤', 'Таблица Лидеров 🏆'])
    await msg.answer(("Теперь ты зарегистрирован в боте! \nТвоя имя: {}".format(msg.text) if str(numbers_to_name[msg.from_user.id]) != msg.text[-1]
                     else 'Такое имя уже занято, поэтому мы прибавили к нему цифру "{}" !\n\nТвоё имя: {}'.format(numbers_to_name[msg.from_user.id], msg.text[0:3])) + "\n\nНапишите команду /help, чтобы узнать информацию о пользовании ботом.", reply_markup=keyboard)  # Выводим пользователю его имя

    await state.finish()  # Закрываем state


@DP.message_handler(commands=["help"])      # КОГДА ПОЛЬЗОВАТЕЛЬ ПИШЕТ /help
async def help(msg: Message):
    await msg.answer("Инструкция по пользованию: \n\nПоказать план 🗓 - демонстрация полного плана со всеми пунктами. \
    \n\nРедактировать план 📝 - Добавление/Удаление пункта. \n\nНастройки ⚙️ - Настройка определённых параметров бота. \
    \n\nМой Профиль 👤 - Демонстрирование количества опыта на твоём аккаунте, а также твоя позиция в таблице лидеров. \
    \nОпыт - опредёленная единица, которую можно получить за различную активность в боте, например: удаление/добавление пунктов или получение оповещения. \
    \n\nТаблица Лидеров 🏆 - игроки с наибольшим количеством опыта в данном боте.")


@DP.callback_query_handler()
async def callback_worker(call: CallbackQuery, state: FSMContext):

    if call.data == 'Добавить пункт ➕':

        await call.message.edit_text("1/3 🗒 \n\nНапиши дату, на которую нужно создать пункт в формате: 2022-11-14, где первое число - год, второе - месяц, третье - день.")
        await UserState.date.set()  # Делаем set() на значение date

    elif call.data == 'Удалить пункт ➖':

        keyboard = InlineKeyboardMarkup()
        for i in range(1, len(USERS[str(call.from_user.id)]["Paragraph_text"]) + 1):
            keyboard.add(aiogram.types.InlineKeyboardButton(
                text=f"Пункт {i}",
                callback_data=i - 1
            ))
        await call.message.edit_text("Какой пункт удалить? ❌", reply_markup=keyboard)

    elif call.data == 'Редактировать дату 🖊':
        await call.message.edit_text("Напишите новую дату для пункта 🖊")
        await UserState.date.set()  # Делаем set() на значение date

    elif call.data == 'Редактировать время 🖊':
        await call.message.edit_text("Напишите новое время для пункта 🖊")
        await UserState.time.set()  # Делаем set() на значение time

    elif call.data == 'Редактировать текст 🖊':
        await call.message.edit_text("Напишите новый текст для пункта 🖊")
        await UserState.text.set()  # Делаем set() на значение text

    elif call.data == 'Всё верно✅':
        data = await state.get_data()  # data - это словарь со всеми значениями, которые мы сохраняли ранее
        USERS[str(call.from_user.id)]["Paragraph_date"].append(data['date'])
        USERS[str(call.from_user.id)]["Paragraph_time"].append(data['time'])
        USERS[str(call.from_user.id)]["Paragraph_text"].append(data['text'])
        USERS[str(call.from_user.id)]["Plan_number"] += 1
        USERS[str(call.from_user.id)]["Experience"] += 5
        saveDB()

        keyboard = InlineKeyboardMarkup()
        keyboard.add(aiogram.types.InlineKeyboardButton(
                text="Включить оповещение 🔔",
                callback_data="Включить оповещение 🔔"
            ))

        await call.message.edit_text("Отлично! Пункт добавлен в план! ✅", reply_markup=keyboard)

        await state.finish()

    elif call.data == "Включить оповещение 🔔":
        keyboard = InlineKeyboardMarkup()
        keyboard.add(aiogram.types.InlineKeyboardButton(
                text="Выключить оповещение 🔕",
                callback_data="Выключить оповещение 🔕"
            ))

        USERS_BGTASKS[call.from_user.id].append({USERS[str(call.from_user.id)]["Plan_number"]: asyncio.create_task(Bot_sends_message_when_time_comes(str(call.from_user.id)))}) # Запускаем фоновую задачу   
        await call.message.edit_text("Теперь оповещение включено! 🔔", reply_markup=keyboard)
        
    elif call.data == "Выключить оповещение 🔕":
        USERS_BGTASKS[call.from_user.id][USERS[str(call.from_user.id)]["Plan_number"]].cancel()
        del USERS_BGTASKS[call.from_user.id][USERS[str(call.from_user.id)]["Plan_number"]]

        keyboard = InlineKeyboardMarkup()
        keyboard.add(aiogram.types.InlineKeyboardButton(
                text="Включить оповещение 🔔",
                callback_data="Включить оповещение 🔔"
            ))
        await call.message.edit_text("Теперь оповещение выключено! 🔕", reply_markup=keyboard)

    elif call.data == "Удаление пункта":
        keyboard = InlineKeyboardMarkup()
        keyboard.add(aiogram.types.InlineKeyboardButton(
                text="Изменить 📝",
                callback_data="Удаление пункта"
        ))

        if USERS[str(call.from_user.id)]['settings_delete_item'] == True:
            USERS[str(call.from_user.id)]['settings_delete_item'] = False
            saveDB()
            await call.message.edit_text('Теперь пункт не удаляется из плана при отправке, связанного с ним оповещения ❌', reply_markup=keyboard)

        else:
            USERS[str(call.from_user.id)]['settings_delete_item'] = True
            saveDB()
            await call.message.edit_text('Теперь пункт удаляется из плана при отправке, связанного с ним оповещения ✅', reply_markup=keyboard)

    elif call.data == "Часосовой пояс":
        keyboard = InlineKeyboardMarkup()
        for i in ["Europe/Moscow", 'Africa/Abidjan', 'America/Los_Angeles', 'Antarctica/South_Pole', 'Asia/Dubai', 'Australia/Sydney', 'Europe/Kaliningrad', 'Europe/Kiev', 'Europe/London', 'Europe/Berlin', 'Europe/Paris', 'Europe/Rome', 'Egypt', 'Poland', 'Japan', 'Etc/GMT+5']:
            keyboard.add(aiogram.types.InlineKeyboardButton(
                text=i,
                callback_data="zone{}".format(i)
            ))

        await call.message.edit_text("Выбери свой часовой пояс: ", reply_markup=keyboard)

    elif call.data.startswith("zone"):
        USERS[str(call.from_user.id)]["settings_time_zone"] = call.data[4:]
        saveDB()

        await call.message.edit_text("Теперь твой часовой пояс: {} ✅".format(call.data[4:]))

    else:
        USERS[str(call.from_user.id)]["Paragraph_date"].pop(int(call.data))
        USERS[str(call.from_user.id)]["Paragraph_time"].pop(int(call.data))
        USERS[str(call.from_user.id)]["Paragraph_text"].pop(int(call.data))
        USERS[str(call.from_user.id)]["Experience"] += 5
        USERS[str(call.from_user.id)]["Plan_number"] -= 1
        saveDB()

        await call.message.edit_text("Пункт удалён из плана! ❌")

        if call.from_user.id in USERS_BGTASKS:
            USERS_BGTASKS[call.from_user.id][USERS[str(call.from_user.id)]["Plan_number"]].cancel()
            del USERS_BGTASKS[call.from_user.id][USERS[str(call.from_user.id)]["Plan_number"]]


@DP.message_handler(state=UserState.date)  # Когда появляется состояние с date
async def adding_date_to_user_plan(msg: Message, state: FSMContext):

    try:
        now = datetime.datetime.now(pytz.timezone(USERS[str(msg.from_user.id)]["settings_time_zone"])).date()
        user_date = now.replace(year=int(msg.text[0:4]), month=int(msg.text[5:7]), day=int(msg.text[8:10]))
        if now > user_date or int(msg.text[5:7]) > 12 or int(msg.text[8:10]) > 31 or len(msg.text) > 10:
            await Bot.send_message(msg.from_user.id, "Введёная дата была в прошлом или её не существует! Попробуй ещё раз! ❌")
        else:
            data = await state.get_data()
            if 'date' not in data:
                await state.update_data(date=msg.text)
                await Bot.send_message(msg.from_user.id, "2/3 🗒 \n\nНапиши время, на которое нужно создать пункт в формате: 20:58:05, 08:11:43")
                await UserState.time.set()
            else:
                await state.update_data(date=msg.text)
                await end_of_filling(str(msg.from_user.id), state)

    except:
        await Bot.send_message(msg.from_user.id, 'Дата введена неверно! ❌')


@DP.message_handler(state=UserState.time)  # Когда появляется состояние с time
async def adding_time_to_user_plan(msg: Message, state: FSMContext):

    try:
        data = await state.get_data()
        now_time = datetime.datetime.now(pytz.timezone(USERS[str(msg.from_user.id)]["settings_time_zone"])).time()
        user_time = now_time.replace(hour=int(msg.text[0:2]), minute=int(msg.text[3:5]), second=int(msg.text[6:8]))
        if int(data['date'][8:11]) == datetime.datetime.now(pytz.timezone(USERS[str(msg.from_user.id)]["settings_time_zone"])).day and now_time > user_time \
                or int(msg.text[0:2]) > 24 or int(msg.text[3:5]) > 60 or int(msg.text[6:8]) > 60 or len(msg.text) > 8:
            await Bot.send_message(msg.from_user.id,
                                   "Введённое время было в прошлом или его не существует! Попробуй ещё раз! ❌")
        else:
            data = await state.get_data()
            if 'time' not in data:
                await state.update_data(time=msg.text)
                await Bot.send_message(msg.from_user.id, "3/3 🗒 \n\nНапиши текст с описанием, намеченной тобой цели на дату данного пункта. \n\nНапример: Сделать домашнее задание, помочь родителям по домашним делам.")
                await UserState.text.set()
            else:
                await state.update_data(time=msg.text)
                await end_of_filling(str(msg.from_user.id), state)

    except:
        await Bot.send_message(msg.from_user.id, 'Время введено неверно! ❌')


@DP.message_handler(state=UserState.text)  # Когда появляется состояние с text
async def adding_text_to_user_plan(msg: Message, state: FSMContext):
    await state.update_data(text=msg.text)
    await end_of_filling(str(msg.from_user.id), state)


@DP.message_handler()
async def ReplyKeyboard_handling(msg: Message):  # Обработка запросов с клавиатуры

    if str(msg.from_user.id) in USERS:
        if msg.text == 'Показать план 🗓':

            await msg.answer("Твой текущий план:{}".format(await find_user_plan(str(msg.from_user.id))) if USERS[str(msg.from_user.id)]['Paragraph_text'] else "У тебя ещё нету плана!")

        elif msg.text == 'Редактировать план 📝' and str(msg.from_user.id) in USERS:

            keyboard = InlineKeyboardMarkup()

            keyboard.add(aiogram.types.InlineKeyboardButton(
                text='Добавить пункт ➕',
                callback_data='Добавить пункт ➕'
            ))

            if USERS[str(msg.from_user.id)]['Paragraph_text']:
                keyboard.add(aiogram.types.InlineKeyboardButton(
                    text='Удалить пункт ➖',
                    callback_data='Удалить пункт ➖'
                ))

            await msg.answer("{}".format(f"Твой текущий план:{await find_user_plan(str(msg.from_user.id))}\n\nКак ты хочешь изменить свой план?"
                                if USERS[str(msg.from_user.id)]['Paragraph_text'] else "У тебя ещё нету плана! \n\nСоздай же его!"), reply_markup=keyboard)

        elif msg.text == 'Настройки ⚙️' or msg.text == '/settings':

            keyboard = InlineKeyboardMarkup()
            keyboard.add(aiogram.types.InlineKeyboardButton(
                text='1️⃣ Удаление пункта',
                callback_data='Удаление пункта'
            ))
            keyboard.add(aiogram.types.InlineKeyboardButton(
                text= '2️⃣ Изменить часовой пояс',
                callback_data='Часосовой пояс'
            ))

            await msg.answer(
                "Настройки ⚙️ \n\n1️⃣ Удаление пункта - {} \nЕсли включено: \nПункт удаляется из плана, если бот прислал оповещение. \nЕсли выключено: \
                \nПри отправке оповещения ботом, пункт не удаляется из плана\n\n2️⃣ Твой текущий часовой пояс - {} \nВыберите из предложенного списка часовой пояс, соответствующий вашему региону."
                .format("Включено ✅" if USERS[str(msg.from_user.id)]["settings_delete_item"] else 'Выключено ❌', USERS[str(msg.from_user.id)]["settings_time_zone"]), reply_markup=keyboard)
        
        elif msg.text == 'Мой Профиль 👤' or msg.text == '/profile':
            await msg.answer(
                "Твой профиль 👤 \n\nИмя: {}\n\nУровень {}\n{}{}"
                .format(USERS[str(msg.from_user.id)]["Username"], 
                (USERS[str(msg.from_user.id)]["Experience"] // 20) + 1, 
                "🟦" * ((USERS[str(msg.from_user.id)]["Experience"] - 20 * (USERS[str(msg.from_user.id)]["Experience"] // 20)) if USERS[str(msg.from_user.id)]["Experience"] >= 20 else USERS[str(msg.from_user.id)]["Experience"]), 
                "⬜️" * ((20 - (USERS[str(msg.from_user.id)]["Experience"] - 20 * (USERS[str(msg.from_user.id)]["Experience"] // 20))) if USERS[str(msg.from_user.id)]["Experience"] >= 20 else 20 - USERS[str(msg.from_user.id)]["Experience"])
            ))

        elif msg.text == 'Таблица Лидеров 🏆' or msg.text == '/leaderboard':
            res = []
            dct = sorted({USERS[i]["Username"]: USERS[i]["Experience"] for i in USERS.keys()}.items(), key=operator.itemgetter(1))

            for i in dct:
                for index, j in enumerate(i):
                    res.append("{} - {} опыта".format(("🥇 " if dct[0] == i else ("🥈 " if dct[1] == i else ("🥉 " if dct[2] == i else ''))) + j, i[index + 1]))
                    break

            await msg.answer(
                "Таблица Лидеров 🏆\n\n{}".format("".join(res))
            )

    else:
        await msg.answer("Ты не можешь использовать данную команду! ❌")




if __name__ == "__main__":  # Если файл запускается как самостоятельный, а не как модуль
    logger.info("Запускаю бота...")  # В консоле будет отоброжён процесс запуска бота
    executor.start_polling(  # Бот начинает работать
        dispatcher=DP,  # Передаем в функцию диспетчер
        # (диспетчер отвечает за то, чтобы сообщения пользователя доходили до бота)
        on_startup=logger.info("Загрузился успешно!"), skip_updates=True)
    # Если бот успешно загрузился, то в консоль выведется сообщение