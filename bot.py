import telebot
from telebot import types
from datetime import datetime, timedelta
import random

# --- SOZLAMALAR ---
TOKEN = "7973986790:AAGLvDleKgyUsiRaYyglt0uYEqWKo8UPJBs"   # BotFather'dan
ADMIN_ID = 7060781941                # Admin ID
CARD_NUMBER = "9860356640700114"     # To'lov kartasi

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# --- UC PAKETLARI ---
uc_packages = {
    "30 UC": 9000,
    "60 UC": 13000,
    "120 UC": 25000,
    "180 UC": 37000,
    "325 UC": 59000,
    "355 UC": 67000,
    "385 UC": 74000,
    "415 UC": 80000,
    "565 UC": 109000
}

# --- MA'LUMOTLAR BAZASI ---
balances = {}                 
balance_history = {}          
pending_topups = {}           
pending_orders = {}           
awaiting_pubg_id = {}         
user_orders = {}              
statistics = {"total": 0}     
promo_codes = {"PROMO10": 10} 
vip_users = set()             
user_spent = {}               
uc_sold_stats = {k: 0 for k in uc_packages}  
user_xp = {}                  
referrals = {}                
ref_bonus = 200               
last_spin = {}                

# Aksiya (chegirma)
active_discount = 0           
discount_end = None           

# ------------------ YORDAMCHI FUNKSIYALAR ------------------
def get_balance(user_id):
    return balances.get(user_id, 0)

def update_balance(user_id, amount, action="Balans o‘zgarishi"):
    balances[user_id] = get_balance(user_id) + amount
    balance_history.setdefault(user_id, []).append(
        (amount, action, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )

def user_history(user_id):
    return balance_history.get(user_id, [])

def add_order(user_id, package):
    user_orders.setdefault(user_id, []).append(package)

def apply_discount(price):
    global active_discount, discount_end
    if discount_end and datetime.now() >= discount_end:
        reset_discount()
    if active_discount > 0:
        return int(price * (100 - active_discount) / 100)
    return price

def reset_discount():
    global active_discount, discount_end
    active_discount = 0
    discount_end = None

def generate_graph_ascii():
    bars = []
    maxv = max(uc_sold_stats.values()) if any(uc_sold_stats.values()) else 1
    for k, v in uc_sold_stats.items():
        bar = '█' * int((v / maxv) * 20)
        bars.append(f"{k:7} | {bar} {v}")
    return "\n".join(bars)

# ------------------ HANDLERLAR ------------------

@bot.message_handler(commands=['start'])
def start(message):
    parts = message.text.split()
    if len(parts) > 1:
        try:
            ref_id = int(parts[1])
            if ref_id != message.from_user.id:
                referrals.setdefault(ref_id, [])
                if message.from_user.id not in referrals[ref_id]:
                    referrals[ref_id].append(message.from_user.id)
                    update_balance(ref_id, ref_bonus, "Referal bonusi")
                    bot.send_message(ref_id, f"🎉 Do‘stingiz botga qo‘shildi, sizga *{ref_bonus:,} soʻm* bonus berildi!")
        except:
            pass

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎮 UC Do'kon", "💰 Balansim")
    markup.row("➕ Balans to‘ldirish", "📦 Buyurtmalarim")
    markup.row("📜 Balans tarixi", "🎁 Promo kod")
    markup.row("🏆 TOP 10 xaridorlar", "📊 Statistika")
    markup.row("🎡 Spin", "🔥 Aksiya", "🤝 Referallarim")
    bot.send_message(message.chat.id, "🤖 *Xush kelibsiz!* Kuchli UC do‘kon boti ishga tushdi!", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💰 Balansim")
def balance(message):
    user_id = message.from_user.id
    bal = get_balance(user_id)
    bot.send_message(message.chat.id, f"💰 Balansingiz: *{bal:,} so'm*")

@bot.message_handler(func=lambda m: m.text == "📜 Balans tarixi")
def show_hist(message):
    hist = user_history(message.from_user.id)
    if not hist:
        bot.send_message(message.chat.id, "📜 Balans tarixi bo‘sh.")
        return
    txt = "📜 *Balans tarixi (oxirgi 10 ta):*\n"
    for i, (amount, action, d) in enumerate(hist[-10:], 1):
        txt += f"{i}. {action}: {amount:+,} so‘m ({d})\n"
    bot.send_message(message.chat.id, txt)

@bot.message_handler(func=lambda m: m.text == "🤝 Referallarim")
def referals_info(message):
    user_id = message.from_user.id
    count = len(referrals.get(user_id, []))
    link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    bot.send_message(message.chat.id, f"🤝 Referallaringiz: *{count} ta*\nLink: `{link}`")

@bot.message_handler(func=lambda m: m.text == "➕ Balans to‘ldirish")
def topup(message):
    bot.send_message(message.chat.id, f"💳 Balans to‘ldirish uchun karta: `{CARD_NUMBER}`\n\nTo‘lov summasini yozing (masalan: `50000`).")
    bot.register_next_step_handler(message, get_topup_amount)

def get_topup_amount(message):
    try:
        amount = int(message.text)
        pending_topups[message.from_user.id] = amount
        bot.send_message(message.chat.id, "📸 Endi to‘lov kvitansiyasini (chek) rasm sifatida yuboring.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Noto‘g‘ri format. Faqat son kiriting.")

@bot.message_handler(content_types=['photo'])
def handle_photos(message):
    user_id = message.from_user.id
    if user_id in pending_topups:
        bot.forward_message(ADMIN_ID, user_id, message.message_id)
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"topup_ok_{user_id}"),
            types.InlineKeyboardButton("❌ Bekor qilish", callback_data=f"topup_no_{user_id}")
        )
        bot.send_message(ADMIN_ID, f"💳 Balans to‘ldirish: foydalanuvchi *{user_id}*, summa: *{pending_topups[user_id]:,} so'm*", reply_markup=markup)
        bot.send_message(user_id, "📤 Kvitansiya yuborildi. Admin tasdiqlashini kuting.")
        return

@bot.callback_query_handler(func=lambda call: call.data.startswith("topup_"))
def admin_topup(call):
    if call.message.chat.id != ADMIN_ID:
        return
    _, status, uid = call.data.split("_")
    uid = int(uid)
    if status == "ok":
        amount = pending_topups.pop(uid, 0)
        update_balance(uid, amount, "Balans to‘ldirish")
        bot.send_message(uid, f"✅ Balansingizga *{amount:,} so'm* qo‘shildi!")
    else:
        pending_topups.pop(uid, None)
        bot.send_message(uid, "❌ Balans to‘ldirish rad etildi.")

@bot.message_handler(func=lambda m: m.text == "🎮 UC Do'kon")
def uc_shop(message):
    markup = types.InlineKeyboardMarkup()
    for uc, price in uc_packages.items():
        p = apply_discount(price)
        text = f"{uc} – {p:,} so'm"
        markup.add(types.InlineKeyboardButton(text, callback_data=f"ucbuy_{uc}"))
    bot.send_message(message.chat.id, "🎮 UC paketini tanlang:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ucbuy_"))
def ucbuy(call):
    user_id = call.from_user.id
    uc_type = call.data.split("ucbuy_")[1]
    price = apply_discount(uc_packages[uc_type])

    if get_balance(user_id) < price:
        bot.send_message(user_id, "❌ Balansingiz yetarli emas. Avval balansni to‘ldiring.")
        return

    update_balance(user_id, -price, f"{uc_type} xaridi")
    uc_sold_stats[uc_type] += 1
    add_order(user_id, uc_type)
    user_spent[user_id] = user_spent.get(user_id, 0) + price
    statistics["total"] += 1
    pending_orders[user_id] = {"package": uc_type}
    bot.send_message(user_id, f"✅ {uc_type} uchun *{price:,} so'm* yechildi.\nPUBG ID raqamingizni yuboring:")
    awaiting_pubg_id[user_id] = True

@bot.message_handler(func=lambda m: m.from_user.id in awaiting_pubg_id)
def get_pubg_id(message):
    user_id = message.from_user.id
    pubg_id = message.text.strip()
    package = pending_orders[user_id]["package"]
    del awaiting_pubg_id[user_id]

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Donat yuborildi", callback_data=f"done_{user_id}"))
    bot.send_message(ADMIN_ID, f"🧾 Buyurtma\nFoydalanuvchi: *{user_id}*\nPaket: *{package}*\nPUBG ID: `{pubg_id}`", reply_markup=markup)
    bot.send_message(user_id, "🔄 Admin UC’ni hisobingizga o‘tkazmoqda. Iltimos, kuting.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("done_"))
def donation_done(call):
    if call.message.chat.id != ADMIN_ID:
        return
    _, uid = call.data.split("_")
    uid = int(uid)
    pending_orders.pop(uid, None)
    bot.send_message(uid, "🎉 Donatingiz **muvaffaqiyatli yetkazildi!** Rahmat!")

@bot.message_handler(func=lambda m: m.text == "📦 Buyurtmalarim")
def my_orders(message):
    orders = user_orders.get(message.from_user.id, [])
    if not orders:
        bot.send_message(message.chat.id, "❌ Sizda buyurtma yo‘q.")
    else:
        bot.send_message(message.chat.id, "📦 Sizning buyurtmalaringiz:\n" + "\n".join(orders))

@bot.message_handler(func=lambda m: m.text == "🏆 TOP 10 xaridorlar")
def top_users(message):
    if not user_spent:
        bot.send_message(message.chat.id, "📊 Hali xaridorlar yo‘q.")
        return
    top_list = sorted(user_spent.items(), key=lambda x: x[1], reverse=True)[:10]
    text = "🏆 *TOP 10 xaridorlar:*\n"
    for i, (uid, spent) in enumerate(top_list, 1):
        text += f"{i}. ID `{uid}` — *{spent:,} so'm*\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
def stats(message):
    text = "📊 *UC sotuv statistikasi:*\n"
    for uc, count in uc_sold_stats.items():
        text += f"{uc}: {count} ta\n"
    bot.send_message(message.chat.id, text)
    ascii_graph = generate_graph_ascii()
    bot.send_message(message.chat.id, f"```\n{ascii_graph}\n```")

@bot.message_handler(func=lambda m: m.text == "🎁 Promo kod")
def promo_entry(message):
    bot.send_message(message.chat.id, "🎁 Promo kodni kiriting:")
    bot.register_next_step_handler(message, apply_promo)

def apply_promo(message):
    code = message.text.strip().upper()
    if code in promo_codes:
        bonus = promo_codes[code] * 100
        update_balance(message.from_user.id, bonus, "Promo kod bonus")
        bot.send_message(message.chat.id, f"✅ Promo kod qabul qilindi! Balansingizga *{bonus:,} so'm* qo'shildi.")
    else:
        bot.send_message(message.chat.id, "❌ Noto‘g‘ri promo kod.")

@bot.message_handler(func=lambda m: m.text == "🔥 Aksiya")
def show_discount(message):
    if active_discount > 0 and discount_end and datetime.now() < discount_end:
        left = (discount_end - datetime.now()).seconds // 60
        bot.send_message(message.chat.id, f"🔥 *{active_discount}%* chegirma aktiv! Yana *{left} daqiqa* amal qiladi.")
    else:
        bot.send_message(message.chat.id, "❌ Hozircha aktiv aksiya yo‘q.")

@bot.message_handler(func=lambda m: m.text == "🎡 Spin")
def spin_game(message):
    user_id = message.from_user.id
    now = datetime.now()
    if user_id in last_spin and (now - last_spin[user_id]).days < 1:
        bot.send_message(user_id, "⏳ Bugun spin qildingiz. Ertaga yana urinib ko‘ring.")
        return
    last_spin[user_id] = now
    prize = 100
    update_balance(user_id, prize, "🎡 Spin bonusi")
    bot.send_message(user_id, f"🎉 Tabriklaymiz! Siz *{prize:,} so'm* yutdingiz!")

print("Bot birlashtirilgan va tugmalar to‘liq ishlayapti...")
bot.polling(none_stop=True)
