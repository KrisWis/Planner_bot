from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
start_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
start_keyboard.add(*["Посмотреть меню 🧾", "Сделать заказ 🖊"])
next_keyboard = InlineKeyboardMarkup()
next_keyboard.add(InlineKeyboardButton(
    text='Самовывоз 🚶',
    callback_data='Самовывоз'
))
next_keyboard.add(InlineKeyboardButton(
    text='Доставка 🚚',
    callback_data='Доставка'
))
end_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
end_keyboard.add(*["✅", "❌"])
admin_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
admin_keyboard.add(*["Добавить карточку 🖊", "Удалить заказ 🖍", "Меню 🧾"])
end_admin_keyboard = InlineKeyboardMarkup()
end_admin_keyboard.add(InlineKeyboardButton(
    text="Добавить карточку ✅",
    callback_data='"Добавить карточку'
))
end_admin_keyboard.add(InlineKeyboardButton(
    text="Не добавлять ❌",
    callback_data="Не добавлять"
))
