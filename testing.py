from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
import os
import sqlite3 
import keyboards as kb
import logging.handlers
import logging
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
import random

bot = Bot(token="5304965757:AAH7-0otuTLbWBDFjalcg99MNu7qVWm7ihA")
dp = Dispatcher(bot,storage=MemoryStorage())
conn = sqlite3.connect('lukianov.db')
cur = conn.cursor()

admin_id=[1979922062]
#1741261245
#1979922062

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


cur.execute("""CREATE TABLE IF NOT EXISTS user(
name TEXT,
user_id INT);""")

cur.execute("""CREATE TABLE IF NOT EXISTS menu(
card_id INT,
food_name TEXT,
description TEXT,
prise INT,
photo_id TEXT);""")

cur.execute("""CREATE TABLE IF NOT EXISTS efemer(
id TEXT,
product TEXT,
price INT,
address TEXT,
mobile_phone TEXT);""")


class States(StatesGroup):  # Создаём состояния
    DEFOLT_STATE = State()
    ADMIN_DEFOLT_STATE = State()
 
    ID_ORDER = State() #запрос id карточки 
    SEND_STATE = State() #отправить или нет юзер
    ADDRESS_STATE = State() #адрес
    MOBILE_PHONE_STATE = State() #номер телефона
    """Машины состояний для админа"""
    ADMIN_PRODUCT_NAME = State()
    ADMIN_PRODUCT_DESCRIPTION = State()
    ADMIN_PRODUCT_PRICE = State()
    ADMIN_PRODUCT_PHOTO = State()
    ADMIN_END = State()


@dp.message_handler(commands=["start"])
async def start(message: Message):
    
    if cur.execute(f"SELECT user_id FROM user WHERE user_id='{message.from_user.id}'").fetchone() is None:
        cur.execute(f"INSERT INTO user VALUES(?,?)",(message.from_user.full_name,message.from_user.id))
        conn.commit()

        cur.execute(f"INSERT INTO efemer VALUES(?,?,?,?,?)",(message.from_user.id,None,None,None,None))
        conn.commit()

    if message.from_user.id in admin_id:
        await message.answer("Вы администратор",reply_markup=kb.admin_keyboard)
        await States.ADMIN_DEFOLT_STATE.set()
    else:
        await message.answer("Здравствуйте, я чат бот шашлычного теремка. Вы можете оформить заказ на доставку или самовывоз.", reply_markup=kb.start_keyboard)
        await States.DEFOLT_STATE.set()
        



@dp.message_handler(state=States.DEFOLT_STATE)
async def ReplyKeyboard_handling(message: Message):  # Обработка запросов с клавиатуры для обычного пользователя
    if message.text == "Сделать заказ 🖊":
        for i in cur.execute("SELECT * FROM menu;"):

            await bot.send_photo(photo=i[4], caption=f"""Айди карточки: {i[0]}
Название еды: {i[1]}
{i[2]}
Цена: {i[3]}""")
        await message.answer("Как вы хотите получить заказ?", reply_markup=kb.next_keyboard)
        
    elif message.text == "Посмотреть меню 🧾":
        for i in cur.execute("SELECT * FROM menu;"):
            id = i[0]
            food_name = i[1]
            food_description = i[2]
            food_price = i[3]
            food_photo = i[4]
            
        await bot.send_photo(photo=food_photo, caption=f"""Айди карточки: {id}
    Название еды: {food_name}
    {food_description}
    Цена: {food_price}
    """)



@dp.message_handler(state=States.ADMIN_DEFOLT_STATE)
async def Admin_ReplyKeyboard_handling(message: Message, state: FSMContext):  # Обработка запросов с клавиатуры для админа
    if message.text == "Добавить карточку 🖊":
        await message.answer("1/4 🗒 \n\nДля начала напишите название карточки, который хотите добавить")
        await States.ADMIN_PRODUCT_NAME.set()


@dp.message_handler(state=States.ADMIN_PRODUCT_NAME)
async def adding_name_to_menu(message: Message, state: FSMContext):
    await state.update_data(product_name=message.text)
    await message.answer("2/4 🗒 \n\nНапишите описание карточки, который хотите добавить")
    await States.ADMIN_PRODUCT_DESCRIPTION.set()

    
@dp.message_handler(state=States.ADMIN_PRODUCT_DESCRIPTION)
async def adding_description_to_menu(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("3/4 🗒 \n\nНапишите цену карточки, который хотите добавить")
    await States.ADMIN_PRODUCT_PRICE.set()
    

@dp.message_handler(state=States.ADMIN_PRODUCT_PRICE)
async def adding_price_to_menu(message: Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("4/4 🗒 \n\nПришлите фото карточки, который хотите добавить")
    await States.ADMIN_PRODUCT_PHOTO.set()
    

@dp.message_handler(content_types=['photo'], state=States.ADMIN_PRODUCT_PHOTO)
async def end_to_adding_menu(message: Message, state: FSMContext):
    data = await state.get_data()
    await bot.send_photo(message.from_user.id, photo=message.photo[-1].file_id, caption=f'Название: {data["product_name"]}\nОписание: {data["description"]}\nЦена: {data["price"]}')
    await bot.answer("Добавить карточку? ", reply_markup=kb.end_admin_keyboard)
    await States.ADMIN_END.set()


@dp.callback_query_handler(lambda c: c.data == "Добавить карточку", state=States.DEFOLT_STATE)
async def save_card(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cur.execute("INSERT INTO menu VALUES(?, ?, ?, ?, ?);", (random.choice([i for i in range(100000)]), data["product_name"], data["description"], data["price"], call.photo.id))
    conn.commit()
    await call.edit_text("Карточка успешна добавлена в меню ✅")

    
@dp.callback_query_handler(lambda c: c.data == "Не добавлять", state=States.DEFOLT_STATE)
async def return_admin(call: types.CallbackQuery, state: FSMContext):
    await call.edit_text("Вы отменили добавление карточки ❌", reply_markup=kb.admin_keyboard)
    await state.finish()
    
    
@dp.callback_query_handler(lambda c: c.data == 'Самовывоз', state=States.DEFOLT_STATE) #если выбран самовывоз
async def order_call(call: types.CallbackQuery):
    await call.edit_text("Отправь ID из меню того блюда которое хочешь заказать")
    await States.ID_ORDER.set()


@dp.callback_query_handler(lambda c: c.data == 'Доставка', state=States.DEFOLT_STATE) #если выбран самовывоз
async def call_addres(call: types.CallbackQuery):
    await call.answer("Какой ваш адрес?")
    await States.ADDRESS_STATE.set()
    
@dp.message_handler(state=States.ADDRESS_STATE)
async def inp_addr(message: Message):  #получение адреса
    try:
        cur.execute(f"UPDATE efemer SET address = '{message.text}'")
        conn.commit()
    except:
        await message.answer("Знак ковычек запрещен. Попробуйте еще раз без них")
    else:
        await message.answer("Адрес получен")
        await message.answer("Отправте свой контактный номер телефона. Что бы мы могли с вами связаться")
        await States.MOBILE_PHONE_STATE.set()

        
@dp.message_handler(state=States.MOBILE_PHONE_STATE)
async def mobile_phone(message: Message):
    try:
        cur.execute(f"UPDATE efemer SET mobile_phone = '{message.text}'")
        conn.commit()
    except:
        await message.answer("Знак ковычек запрещен. Попробуйте еще раз без них")
    else:
        await message.answer("Номер телефона получен")
        
        await message.answer("")
        await States.MOBILE_PHONE_STATE.set()
    


    
@dp.message_handler(state=States.ID_ORDER)
async def inp_id_order(message: Message):  #получение id блюд
    if message.text == "✅":
        await message.answer("Ваш заказ отправлен")
        













    
if __name__ == "__main__":  # Если файл запускается как самостоятельный, а не как модуль
    logger.info("Запускаю бота...")  # В консоле будет отоброжён процесс запуска бота
    executor.start_polling(  # Бот начинает работать
        dispatcher=dp,  # Передаем в функцию диспетчер
        # (диспетчер отвечает за то, чтобы сообщения пользователя доходили до бота)
        on_startup=logger.info("Загрузился успешно!"), skip_updates=True)
    # Если бот успешно загрузился, то в консоль выведется сообщение
    