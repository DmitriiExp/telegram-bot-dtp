import telebot
from telebot import types
import csv
from datetime import datetime

API_TOKEN = '7658197917:AAEe7pb2kjBJbrpQY75k36aXijBQlmOyklA'
ADMIN_CHAT_ID = 947914394  # замените на ваш Telegram ID

bot = telebot.TeleBot(API_TOKEN)
user_data = {}

rsa_prices = {
    "Мурманская область": {
        "нормо_час": 1800,
        "детали": {
            "Бампер передний": {"цена": 9200, "норма_часов": 2.0},
            "Крыло переднее левое": {"цена": 6800, "норма_часов": 1.5},
            "Крыло переднее правое": {"цена": 6900, "норма_часов": 1.5},
            "Фара передняя левая": {"цена": 8700, "норма_часов": 1.0},
            "Фара передняя правая": {"цена": 8800, "норма_часов": 1.0},
            "Капот": {"цена": 9900, "норма_часов": 2.0},
            "Крыло заднее левое": {"цена": 7300, "норма_часов": 2.0},
            "Крыло заднее правое": {"цена": 7400, "норма_часов": 2.0},
            "Крышка багажника": {"цена": 8500, "норма_часов": 1.8},
            "Заднее стекло": {"цена": 6100, "норма_часов": 1.2},
            "Задняя левая фара": {"цена": 5600, "норма_часов": 1.0},
            "Задняя правая фара": {"цена": 5700, "норма_часов": 1.0}
        }
    }
}

damage_elements = list(rsa_prices["Мурманская область"]["детали"].keys()) + ["Готово"]

def create_damage_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    row = []
    for i, item in enumerate(damage_elements):
        row.append(types.KeyboardButton(item))
        if len(row) == 2:
            kb.add(*row)
            row = []
    if row:
        kb.add(*row)
    return kb

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_data[message.chat.id] = {}
    bot.send_message(message.chat.id, "Привет! Отправь фото повреждений автомобиля.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_data[message.chat.id]['photo'] = message.photo[-1].file_id
    bot.send_message(message.chat.id, "Теперь отправь VIN автомобиля.")

@bot.message_handler(func=lambda msg: 'photo' in user_data.get(msg.chat.id, {}) and 'vin' not in user_data.get(msg.chat.id, {}))
def handle_vin(message):
    user_data[message.chat.id]['vin'] = message.text.strip()
    user_data[message.chat.id]['parts'] = []
    bot.send_message(message.chat.id, "Выбери повреждённые детали. Когда закончишь — нажми 'Готово'.", reply_markup=create_damage_keyboard())

@bot.message_handler(func=lambda msg: msg.text in damage_elements)
def handle_part_selection(message):
    chat_id = message.chat.id
    selected = message.text
    region = "Мурманская область"
    normo_price = rsa_prices[region]["нормо_час"]

    if selected == "Готово":
        total = 0
        summary = []
        for part in user_data[chat_id].get("parts", []):
            data = rsa_prices[region]["детали"].get(part)
            if data:
                part_total = data["цена"] + data["норма_часов"] * normo_price
                total += part_total
                summary.append(f"{part}: {data['цена']} + ({data['норма_часов']}×{normo_price}) = {int(part_total)} ₽")
        user_data[chat_id]['total'] = int(total)
        summary_text = "\n".join(summary)
        response = f"📋 Расчёт по методике РСА (Мурманская область):\n\n{summary_text}\n\n💰 Итог: {int(total)} ₽\n\n⚠️ Это может быть заниженная сумма. Рекомендуем обратиться к эксперту."
        bot.send_message(chat_id, response)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("Да"), types.KeyboardButton("Нет"))
        bot.send_message(chat_id, "Хотите связаться с экспертом для более точной оценки?", reply_markup=markup)
        return

    if 'parts' not in user_data[chat_id]:
        user_data[chat_id]['parts'] = []

    if selected not in user_data[chat_id]['parts']:
        user_data[chat_id]['parts'].append(selected)
        bot.send_message(chat_id, f"Добавлено: {selected}\nВы можете выбрать ещё или нажмите 'Готово'.", reply_markup=create_damage_keyboard())
    else:
        bot.send_message(chat_id, f"{selected} уже выбрано. Выберите другой элемент или нажмите 'Готово'.", reply_markup=create_damage_keyboard())

@bot.message_handler(func=lambda msg: msg.text.lower() in ['да', 'нет'] and 'total' in user_data.get(msg.chat.id, {}) and 'contact_choice' not in user_data[msg.chat.id])
def handle_contact_choice(message):
    chat_id = message.chat.id
    user_data[chat_id]['contact_choice'] = message.text.lower()
    if message.text.lower() == 'да':
        bot.send_message(chat_id, "Пожалуйста, укажи своё имя:", reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(chat_id, "Спасибо за использование бота! Если понадобится помощь — обращайтесь.", reply_markup=types.ReplyKeyboardRemove())
        user_data.pop(chat_id, None)

@bot.message_handler(func=lambda msg: 'contact_choice' in user_data.get(msg.chat.id, {}) and user_data[msg.chat.id]['contact_choice'] == 'да' and 'name' not in user_data[msg.chat.id])
def handle_name(message):
    user_data[message.chat.id]['name'] = message.text.strip()
    bot.send_message(message.chat.id, "Теперь введи номер телефона:")

@bot.message_handler(func=lambda msg: 'name' in user_data.get(msg.chat.id, {}) and 'phone' not in user_data[msg.chat.id])
def handle_phone(message):
    data = user_data[message.chat.id]
    data['phone'] = message.text.strip()
    photo_id = data['photo']
    vin = data['vin']
    parts = ', '.join(data.get('parts', []))
    total = data['total']
    name = data['name']
    phone = data['phone']

    summary = f"📩 Новая заявка:\nИмя: {name}\nТелефон: {phone}\nVIN: {vin}\nДетали: {parts}\nСумма: {total} ₽"
    bot.send_photo(ADMIN_CHAT_ID, photo_id, caption=summary)

    with open("заявки.csv", "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now(), name, phone, vin, parts, total])

    bot.send_message(message.chat.id, "Спасибо! Ваша заявка отправлена эксперту.")
    user_data.pop(message.chat.id, None)

bot.polling(none_stop=True)

import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return 'Бот работает'

port = int(os.environ.get("PORT", 5000))
app.run(host='0.0.0.0', port=port)
