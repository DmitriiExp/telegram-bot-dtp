import telebot
from telebot import types
import csv
from datetime import datetime
import os
from flask import Flask

API_TOKEN = '7658197917:AAEe7pb2kjBJbrpQY75k36aXijBQlmOyklA'
ADMIN_CHAT_ID = 947914394  

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)
user_data = {}

damage_elements = [
    "Бампер передний", "Крыло переднее левое", "Крыло переднее правое",
    "Фара передняя левая", "Фара передняя правая", "Капот",
    "Крыло заднее левое", "Крыло заднее правое", "Крышка багажника",
    "Заднее стекло", "Задняя левая фара", "Задняя правая фара",
    "Другое", "Готово", "Назад"
]

def create_damage_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    row = []
    for i, item in enumerate(damage_elements):
        if item in ["Готово", "Назад"]:
            continue
        row.append(types.KeyboardButton(item))
        if len(row) == 2:
            kb.add(*row)
            row = []
    if row:
        kb.add(*row)
    kb.add(types.KeyboardButton("Другое"))
    kb.add(types.KeyboardButton("Готово"), types.KeyboardButton("Назад"))
    return kb

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_data[message.chat.id] = {}
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("Запустить заново"))
    bot.send_message(message.chat.id, "Привет! Я помогу рассчитать предварительный ущерб после ДТП. Нажми кнопку ниже, чтобы начать.", reply_markup=kb)

@bot.message_handler(func=lambda msg: msg.text == "Запустить заново")
def restart_flow(message):
    user_data[message.chat.id] = {}
    bot.send_message(message.chat.id, "Отправь фото повреждений автомобиля.", reply_markup=types.ReplyKeyboardRemove())

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

    if selected == "Назад":
        bot.send_message(chat_id, "Отправь VIN автомобиля заново.", reply_markup=types.ReplyKeyboardRemove())
        user_data[chat_id].pop('vin', None)
        return

    if selected == "Готово":
        selected_parts = user_data[chat_id].get('parts', [])
        base_price = 5000
        total = base_price * len(selected_parts)
        user_data[chat_id]['total'] = total
        msg = f"Предварительная сумма ущерба: {total} ₽ по базам РСА (Мурманская обл.)\n\n⚠️ Это может быть заниженная сумма. Рекомендуем обратиться к эксперту-технику."
        bot.send_message(chat_id, msg)

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

# ===== Flask для Render =====
app = Flask(__name__)

@app.route('/')
def index():
    return "Бот работает"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

@app.route('/')
def home():
    return "Bot is running"

def run_bot():
    bot.polling(none_stop=True)

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=10000)