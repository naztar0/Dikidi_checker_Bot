#!/usr/bin/env python
from aiogram import Bot, Dispatcher, executor, types, utils
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import mysql.connector
import re
import req_test as r
import constants as c
import asyncio


bot = Bot(c.token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class Form(StatesGroup):
    master = State()
    service = State()
    date = State()
    time = State()


def start_button():
    key = types.ReplyKeyboardMarkup(resize_keyboard=True)
    but_1 = types.KeyboardButton("Поиск свободного времени")
    but_2 = types.KeyboardButton("Список мониторинга")
    key.add(but_1)
    key.add(but_2)
    return key


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    key = start_button()
    await message.answer("Выберите нужную функцию", reply_markup=key)


@dp.callback_query_handler(lambda callback_query: True, state=Form.master)
async def callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    master = []
    for key in callback_query.message.reply_markup.inline_keyboard:
        if key[0]["callback_data"] == callback_query.data:
            master.append(callback_query.data)
            master.append(key[0]["text"])
            break
    async with state.proxy() as data:
        data['master'] = master

    services = r.services(master[0])
    key = types.InlineKeyboardMarkup()
    for service in services:
        key.add(types.InlineKeyboardButton(services[service], callback_data=service))

    await Form.next()
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    await bot.send_message(callback_query.message.chat.id,
                           f"*Специалист:* _{master[1]}_\n\nВыбери услугу", parse_mode="Markdown", reply_markup=key)


@dp.callback_query_handler(lambda callback_query: True, state=Form.service)
async def callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    service = []
    for key in callback_query.message.reply_markup.inline_keyboard:
        if key[0]["callback_data"] == callback_query.data:
            service.append(callback_query.data)
            service.append(key[0]["text"])
            break
    async with state.proxy() as data:
        data['service'] = service

    dates = r.get_date(service[0], data["master"][0])
    time_text = ""
    for date in dates:
        times = r.get_time(date, data["service"][0], data["master"][0])
        for time in times:
            tm, td, tt = time[5:7], time[8:10], time[11:16]
            time_text += f"{td}.{tm} {tt}\n"

    await Form.next()
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    await bot.send_message(callback_query.message.chat.id,
                           f"*Специалист:* _{data['master'][1]}_\n*Услуга*: _{service[1]}_\n\n"
                           f"*Доступное врямя:*\n{time_text}\n[Онлайн-запись](https://beauty.dikidi.net/ru/record/{c.service})",
                           parse_mode="Markdown", disable_web_page_preview=True)

    await bot.send_message(callback_query.message.chat.id, "*Укажите нужную дату*\n\nНапример, если вы хотите записаться __30 июня__, "
                                                           "то отправьте следующее сообщение:\n`2020.06.30`", parse_mode="MarkdownV2")


@dp.message_handler(state=Form.date)
async def message_handler(message: types.Message, state: FSMContext):
    dt = str(message.text)
    if dt == "⬅ Назад":
        await state.finish()
        key = start_button()
        await message.answer("Отменено, можете начать новый поиск", reply_markup=key)
        return
    if not re.search(r"^(\d{4}\.\d{2}\.\d{2})$", dt):
        await message.reply("Неправильный формат! Проверьте вводимые данные и попробуйте еще раз.")
        await state.finish()
        return
    date = dt.replace('.', '-')
    async with state.proxy() as data:
        data['date'] = date
    key = types.InlineKeyboardMarkup()
    but_1 = types.InlineKeyboardButton("8:00 — 14:00", callback_data="1")
    but_2 = types.InlineKeyboardButton("10:00 — 20:00", callback_data="2")
    but_3 = types.InlineKeyboardButton("16:00 — 22:00", callback_data="3")
    but_4 = types.InlineKeyboardButton("Любое время", callback_data="4")
    key.add(but_1)
    key.add(but_2)
    key.add(but_3)
    key.add(but_4)
    await Form.next()
    await message.answer("Выберите временной диапазон", reply_markup=key)


@dp.callback_query_handler(lambda callback_query: True, state=Form.time)
async def callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "1":
        time_1, time_2 = "8", "14"
    elif callback_query.data == "2":
        time_1, time_2 = "10", "20"
    elif callback_query.data == "3":
        time_1, time_2 = "16", "22"
    elif callback_query.data == "4":
        time_1, time_2 = "8", "22"
    else:
        return
    async with state.proxy() as data:
        data['time'] = time_1
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    selectExistQuery = "SELECT EXISTS (SELECT ID FROM users WHERE user_id=(%s) AND date=(%s) AND time_1=(%s) AND time_2=(%s) AND master_id=(%s) AND service_id=(%s))"
    insertQuery = "INSERT INTO users (user_id, date, time_1, time_2, master, service, master_id, service_id) VALUES ((%s), (%s), (%s), (%s), (%s), (%s), (%s), (%s))"
    cursor.executemany(selectExistQuery, [(callback_query.message.chat.id, data['date'], time_1, time_2, data['master'][0], data['service'][0])])
    exist = cursor.fetchone()[0]
    if exist == 1:
        await bot.send_message(callback_query.message.chat.id, "Запись с такими данными уже существует!")
        await state.finish()
        conn.close()
        return
    cursor.executemany(insertQuery, [(callback_query.message.chat.id, data['date'], time_1, time_2, data['master'][1], data['service'][1], data['master'][0], data['service'][0])])
    conn.commit()
    conn.close()
    await state.finish()
    key = start_button()
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    await bot.send_message(callback_query.message.chat.id, "Мониторинг успешно создан!", reply_markup=key)


async def monitor_list(message):
    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    selectQuery = "SELECT ID, date, time_1, time_2, master, service FROM users WHERE user_id=(%s)"
    cursor.execute(selectQuery, [message.chat.id])
    result = cursor.fetchall()
    conn.close()
    text = ""
    for res in result:
        tm = res[1][5:7]
        td = res[1][8:]
        text = "{}\\[/{}] — _нажмите для удаления_\n*Дата:* {}.{} с {} до {} часов\n*Специалист:* {}\n*Услуга:* {}\n\n"\
               .format(text, res[0], td, tm, res[2], res[3], res[4], res[5])
    if text: await message.answer(text, parse_mode="Markdown")
    else: await message.answer("У вас пока ничего не мониторится!")


@dp.message_handler()
async def get(message: types.Message):
    if message.text == "Поиск свободного времени":
        cancel_key = types.ReplyKeyboardMarkup(resize_keyboard=True)
        cancel_key.add(types.KeyboardButton("⬅ Назад"))
        await message.answer("Выберите нужный вариант", reply_markup=cancel_key)
        masters = r.masters()
        key = types.InlineKeyboardMarkup()
        for master in masters:
            key.add(types.InlineKeyboardButton(masters[master], callback_data=master))
        await message.answer("Выберите специалиста", reply_markup=key)
        await Form.master.set()
    elif message.text == "Список мониторинга":
        await monitor_list(message)
    elif message.text == "⬅ Назад":
        key = start_button()
        await message.answer("Отменено, можете начать новый поиск", reply_markup=key)
    elif re.search(r"^/\d+$", message.text):
        conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
        cursor = conn.cursor(buffered=True)
        existsQuery = "SELECT EXISTS (SELECT ID FROM users WHERE ID=(%s) AND user_id=(%s))"
        deleteQuery = "DELETE FROM users WHERE ID=(%s)"
        cursor.executemany(existsQuery, [(message.text[1:], message.chat.id)])
        exist = cursor.fetchone()[0]
        if exist == 0:
            await message.reply("Неправильный номер записи!")
            conn.close()
            return
        cursor.execute(deleteQuery, [message.text[1:]])
        conn.commit()
        conn.close()
        await message.answer("Мониторинг успешно удалён!")


@dp.message_handler(state=Form)
async def cancel(message: types.Message, state: FSMContext):
    if message.text == "⬅ Назад":
        await state.finish()
        key = start_button()
        await message.answer("Отменено, можете начать новый поиск", reply_markup=key)


# check_updates
async def get_updates(res):
    ID, user_id, date, time_1, time_2, master, service, master_id, service_id = \
        res[0], res[1], res[2], res[3], res[4], res[5], res[6], res[7], res[8]
    get_dates = r.get_date(service_id, master_id)
    if not get_dates:
        return
    dates = []
    for datee in get_dates:
        times = r.get_time(datee, service_id, master_id)
        for time in times:
            dates.append(time[:-3])

    conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
    cursor = conn.cursor(buffered=True)
    deleteQuery = "DELETE FROM users WHERE ID=(%s)"
    text = "*Доступна запись!*\n\n"
    send = False
    for datee in dates:
        for hour in range(time_1, time_2 + 1):
            if date == datee[:10] and hour == int(datee[-5:-3]):
                tm, td, tt = datee[5:7], datee[8:10], datee[11:16]
                text += f"*Дата:* `{td}.{tm}` в `{tt}`\n"
                cursor.execute(deleteQuery, [ID])
                conn.commit()
                send = True
    conn.close()
    key = types.InlineKeyboardMarkup()
    key.add(types.InlineKeyboardButton("Онлайн-запись", f"https://beauty.dikidi.net/ru/record/{c.service}"))
    if send:
        try: await bot.send_message(user_id, f"{text}\n*Специалист:* {master}\n*Услуга:* {service}\n\n",
                                    parse_mode="Markdown", reply_markup=key)
        except utils.exceptions.BotBlocked: pass


async def check_updates_loop():
    while True:
        conn = mysql.connector.connect(host=c.host, user=c.user, passwd=c.password, database=c.db)
        cursor = conn.cursor(buffered=True)
        selectQuery = "SELECT * FROM users"
        cursor.execute(selectQuery)
        results = cursor.fetchall()
        conn.close()
        for res in results:
            await get_updates(res)

        await asyncio.sleep(300)


if __name__ == '__main__':
    dp.loop.create_task(check_updates_loop())
    executor.start_polling(dp, skip_updates=True)
