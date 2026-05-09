import logging
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ============================================================
# ⚙️ CONFIG — এখানে তোমার TOKEN ও ADMIN ID বসাও
# ============================================================
BOT_TOKEN = "8797834602:AAEmzPZSo1zxc6KT3U-9R3stqYDNP3LCA5k"   # ← BotFather থেকে নতুন token বসাও
ADMIN_ID  = 8294795125                # ← তোমার Telegram numeric ID বসাও
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Data storage (JSON files) ──────────────────────────────
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def load(filename):
    path = f"{DATA_DIR}/{filename}"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save(filename, data):
    with open(f"{DATA_DIR}/{filename}", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── Helper: register user ──────────────────────────────────
def register_user(user):
    users = load("users.json")
    uid = str(user.id)
    if uid not in users:
        users[uid] = {
            "id": user.id,
            "name": user.full_name,
            "username": user.username or "",
            "joined": datetime.now().isoformat(),
            "messages": 0,
            "banned": False
        }
    else:
        users[uid]["messages"] = users[uid].get("messages", 0) + 1
    save("users.json", users)
    return users[uid]

def is_banned(user_id):
    users = load("users.json")
    return users.get(str(user_id), {}).get("banned", False)

# ══════════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_banned(user.id):
        await update.message.reply_text("❌ তুমি ban হয়েছ।")
        return
    register_user(user)

    kb = [
        [InlineKeyboardButton("🛍️ Products", callback_data="products"),
         InlineKeyboardButton("📦 My Orders", callback_data="my_orders")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help"),
         InlineKeyboardButton("📞 Contact Admin", callback_data="contact")]
    ]
    await update.message.reply_text(
        f"👋 স্বাগতম {user.first_name}!\n\n"
        "🤖 আমি *Shapps Bot* — তোমাকে সাহায্য করতে এসেছি।\n\n"
        "নিচের বাটন থেকে যেকোনো অপশন বেছে নাও 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ══════════════════════════════════════════════════════════
#  /help
# ══════════════════════════════════════════════════════════
async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Available Commands:*\n\n"
        "/start — শুরু করো\n"
        "/products — সব product দেখো\n"
        "/order — order করো\n"
        "/myorders — তোমার orders\n"
        "/help — সাহায্য\n\n"
        "❓ যেকোনো সমস্যায় admin-কে message করো।",
        parse_mode="Markdown"
    )

# ══════════════════════════════════════════════════════════
#  /products
# ══════════════════════════════════════════════════════════
async def products_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    prods = load("products.json")
    if not prods:
        await update.message.reply_text("😔 এখন কোনো product নেই।")
        return

    text = "🛍️ *Available Products:*\n\n"
    kb = []
    for pid, p in prods.items():
        if p.get("active", True):
            text += f"• *{p['name']}* — ৳{p['price']}\n  {p.get('desc','')}\n\n"
            kb.append([InlineKeyboardButton(
                f"🛒 Order: {p['name']}", callback_data=f"order_{pid}"
            )])

    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb) if kb else None
    )

# ══════════════════════════════════════════════════════════
#  /myorders
# ══════════════════════════════════════════════════════════
async def my_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    orders = load("orders.json")
    my = [o for o in orders.values() if str(o.get("user_id")) == user_id]

    if not my:
        await update.message.reply_text("📦 তোমার কোনো order নেই।")
        return

    text = "📦 *তোমার Orders:*\n\n"
    for o in my[-10:]:
        status_emoji = {"pending":"⏳","confirmed":"✅","cancelled":"❌"}.get(o.get("status","pending"),"⏳")
        text += f"{status_emoji} *{o['product_name']}*\nStatus: {o.get('status','pending')}\nDate: {o['date'][:10]}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")

# ══════════════════════════════════════════════════════════
#  Callback buttons
# ══════════════════════════════════════════════════════════
async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "products":
        prods = load("products.json")
        if not prods:
            await q.edit_message_text("😔 এখন কোনো product নেই।")
            return
        text = "🛍️ *Available Products:*\n\n"
        kb = []
        for pid, p in prods.items():
            if p.get("active", True):
                text += f"• *{p['name']}* — ৳{p['price']}\n  {p.get('desc','')}\n\n"
                kb.append([InlineKeyboardButton(f"🛒 Order: {p['name']}", callback_data=f"order_{pid}")])
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_start")])
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("order_"):
        pid = data.replace("order_", "")
        prods = load("products.json")
        p = prods.get(pid)
        if not p:
            await q.edit_message_text("❌ Product পাওয়া যায়নি।")
            return
        orders = load("orders.json")
        oid = str(len(orders) + 1)
        orders[oid] = {
            "id": oid,
            "user_id": q.from_user.id,
            "user_name": q.from_user.full_name,
            "product_id": pid,
            "product_name": p["name"],
            "price": p["price"],
            "status": "pending",
            "date": datetime.now().isoformat()
        }
        save("orders.json", orders)

        # Admin-কে notify করো
        try:
            await ctx.bot.send_message(
                ADMIN_ID,
                f"🛒 *নতুন Order!*\n\n"
                f"👤 User: {q.from_user.full_name} (@{q.from_user.username or 'N/A'})\n"
                f"🆔 User ID: `{q.from_user.id}`\n"
                f"📦 Product: {p['name']}\n"
                f"💰 Price: ৳{p['price']}\n"
                f"🔢 Order ID: #{oid}",
                parse_mode="Markdown"
            )
        except Exception:
            pass

        await q.edit_message_text(
            f"✅ *Order Confirmed!*\n\n"
            f"📦 Product: {p['name']}\n"
            f"💰 Price: ৳{p['price']}\n"
            f"🔢 Order ID: #{oid}\n\n"
            f"Admin শীঘ্রই যোগাযোগ করবে। ধন্যবাদ! 🙏",
            parse_mode="Markdown"
        )

    elif data == "my_orders":
        user_id = str(q.from_user.id)
        orders = load("orders.json")
        my = [o for o in orders.values() if str(o.get("user_id")) == user_id]
        if not my:
            await q.edit_message_text("📦 তোমার কোনো order নেই।",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_start")]]))
            return
        text = "📦 *তোমার Orders:*\n\n"
        for o in my[-10:]:
            status_emoji = {"pending":"⏳","confirmed":"✅","cancelled":"❌"}.get(o.get("status","pending"),"⏳")
            text += f"{status_emoji} *{o['product_name']}* — ৳{o['price']}\nStatus: {o.get('status','pending')}\n\n"
        await q.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_start")]]))

    elif data == "help":
        await q.edit_message_text(
            "📋 *Help:*\n\n"
            "/start — শুরু করো\n"
            "/products — products দেখো\n"
            "/myorders — তোমার orders\n\n"
            "❓ সমস্যায় admin-কে জানাও।",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_start")]]))

    elif data == "contact":
        await q.edit_message_text(
            "📞 *Admin Contact:*\n\nAdmin-কে সরাসরি message করো।\nতোমার সমস্যা জানাও — উত্তর পাবে।",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_start")]]))

    elif data == "back_start":
        kb = [
            [InlineKeyboardButton("🛍️ Products", callback_data="products"),
             InlineKeyboardButton("📦 My Orders", callback_data="my_orders")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help"),
             InlineKeyboardButton("📞 Contact Admin", callback_data="contact")]
        ]
        await q.edit_message_text(
            "🏠 *Main Menu*\n\nনিচের বাটন থেকে অপশন বেছে নাও 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb))

# ══════════════════════════════════════════════════════════
#  ADMIN COMMANDS
# ══════════════════════════════════════════════════════════
def admin_only(func):
    async def wrapper(update, ctx):
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ তুমি admin না!")
            return
        await func(update, ctx)
    return wrapper

@admin_only
async def admin_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users   = load("users.json")
    orders  = load("orders.json")
    prods   = load("products.json")
    pending = [o for o in orders.values() if o.get("status") == "pending"]

    await update.message.reply_text(
        f"👑 *Admin Panel*\n\n"
        f"👥 Total Users: {len(users)}\n"
        f"📦 Total Orders: {len(orders)}\n"
        f"⏳ Pending Orders: {len(pending)}\n"
        f"🛍️ Products: {len(prods)}\n\n"
        f"*Admin Commands:*\n"
        f"/addproduct — product যোগ করো\n"
        f"/delproduct — product মুছো\n"
        f"/listproducts — products দেখো\n"
        f"/listorders — orders দেখো\n"
        f"/confirm <id> — order confirm করো\n"
        f"/cancel <id> — order cancel করো\n"
        f"/broadcast — সবাইকে message দাও\n"
        f"/users — user list\n"
        f"/ban <id> — user ban করো\n"
        f"/unban <id> — user unban করো",
        parse_mode="Markdown"
    )

@admin_only
async def add_product(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Usage: /addproduct Name | Price | Description
    if not ctx.args:
        await update.message.reply_text(
            "⚠️ Format:\n`/addproduct Name | Price | Description`",
            parse_mode="Markdown")
        return
    parts = " ".join(ctx.args).split("|")
    if len(parts) < 2:
        await update.message.reply_text("⚠️ কমপক্ষে Name এবং Price দাও।")
        return
    prods = load("products.json")
    pid = str(len(prods) + 1)
    prods[pid] = {
        "id": pid,
        "name": parts[0].strip(),
        "price": parts[1].strip(),
        "desc": parts[2].strip() if len(parts) > 2 else "",
        "active": True,
        "added": datetime.now().isoformat()
    }
    save("products.json", prods)
    await update.message.reply_text(f"✅ Product যোগ হয়েছে!\n🆔 ID: {pid}\n📦 {prods[pid]['name']} — ৳{prods[pid]['price']}")

@admin_only
async def del_product(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("⚠️ Usage: `/delproduct <id>`", parse_mode="Markdown")
        return
    prods = load("products.json")
    pid = ctx.args[0]
    if pid in prods:
        name = prods[pid]["name"]
        del prods[pid]
        save("products.json", prods)
        await update.message.reply_text(f"✅ '{name}' মুছে ফেলা হয়েছে।")
    else:
        await update.message.reply_text("❌ Product পাওয়া যায়নি।")

@admin_only
async def list_products(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    prods = load("products.json")
    if not prods:
        await update.message.reply_text("😔 কোনো product নেই।")
        return
    text = "🛍️ *Product List:*\n\n"
    for pid, p in prods.items():
        status = "✅" if p.get("active") else "❌"
        text += f"{status} [{pid}] *{p['name']}* — ৳{p['price']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

@admin_only
async def list_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    orders = load("orders.json")
    if not orders:
        await update.message.reply_text("📦 কোনো order নেই।")
        return
    text = "📋 *Orders (last 20):*\n\n"
    for o in list(orders.values())[-20:]:
        emoji = {"pending":"⏳","confirmed":"✅","cancelled":"❌"}.get(o.get("status","pending"),"⏳")
        text += f"{emoji} #{o['id']} — {o['product_name']}\n👤 {o['user_name']} | {o['date'][:10]}\n\n"
    await update.message.reply_text(text, parse_mode="Markdown")

@admin_only
async def confirm_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("⚠️ Usage: `/confirm <order_id>`", parse_mode="Markdown")
        return
    orders = load("orders.json")
    oid = ctx.args[0]
    if oid in orders:
        orders[oid]["status"] = "confirmed"
        save("orders.json", orders)
        # User-কে notify করো
        try:
            await ctx.bot.send_message(
                orders[oid]["user_id"],
                f"✅ তোমার Order #{oid} Confirm হয়েছে!\n📦 {orders[oid]['product_name']}\nধন্যবাদ! 🙏"
            )
        except Exception:
            pass
        await update.message.reply_text(f"✅ Order #{oid} confirmed!")
    else:
        await update.message.reply_text("❌ Order পাওয়া যায়নি।")

@admin_only
async def cancel_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("⚠️ Usage: `/cancel <order_id>`", parse_mode="Markdown")
        return
    orders = load("orders.json")
    oid = ctx.args[0]
    if oid in orders:
        orders[oid]["status"] = "cancelled"
        save("orders.json", orders)
        try:
            await ctx.bot.send_message(
                orders[oid]["user_id"],
                f"❌ তোমার Order #{oid} Cancel হয়েছে।\n📦 {orders[oid]['product_name']}\nযোগাযোগ করো।"
            )
        except Exception:
            pass
        await update.message.reply_text(f"✅ Order #{oid} cancelled.")
    else:
        await update.message.reply_text("❌ Order পাওয়া যায়নি।")

@admin_only
async def broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("⚠️ Usage: `/broadcast Your message here`", parse_mode="Markdown")
        return
    msg = " ".join(ctx.args)
    users = load("users.json")
    sent = 0
    failed = 0
    for uid, u in users.items():
        if not u.get("banned"):
            try:
                await ctx.bot.send_message(int(uid), f"📢 *Broadcast:*\n\n{msg}", parse_mode="Markdown")
                sent += 1
            except Exception:
                failed += 1
    await update.message.reply_text(f"📢 Broadcast শেষ!\n✅ Sent: {sent}\n❌ Failed: {failed}")

@admin_only
async def list_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users = load("users.json")
    if not users:
        await update.message.reply_text("👥 কোনো user নেই।")
        return
    text = f"👥 *Users ({len(users)}):*\n\n"
    for uid, u in list(users.items())[-20:]:
        banned = "🚫" if u.get("banned") else "✅"
        text += f"{banned} {u['name']} (@{u.get('username','N/A')})\n🆔 `{uid}`\n\n"
    await update.message.reply_text(text, parse_mode="Markdown")

@admin_only
async def ban_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("⚠️ Usage: `/ban <user_id>`", parse_mode="Markdown")
        return
    users = load("users.json")
    uid = ctx.args[0]
    if uid in users:
        users[uid]["banned"] = True
        save("users.json", users)
        await update.message.reply_text(f"🚫 User {uid} banned!")
    else:
        await update.message.reply_text("❌ User পাওয়া যায়নি।")

@admin_only
async def unban_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("⚠️ Usage: `/unban <user_id>`", parse_mode="Markdown")
        return
    users = load("users.json")
    uid = ctx.args[0]
    if uid in users:
        users[uid]["banned"] = False
        save("users.json", users)
        await update.message.reply_text(f"✅ User {uid} unbanned!")
    else:
        await update.message.reply_text("❌ User পাওয়া যায়নি।")

# ══════════════════════════════════════════════════════════
#  Auto-reply for normal messages
# ══════════════════════════════════════════════════════════
async def auto_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_banned(user.id):
        return
    register_user(user)

    # Auto-reply rules
    auto_replies = load("auto_replies.json")
    text = update.message.text.lower() if update.message.text else ""

    for rule in auto_replies.values():
        if rule.get("keyword", "").lower() in text:
            await update.message.reply_text(rule["reply"])
            return

    # Default reply
    kb = [[InlineKeyboardButton("🏠 Main Menu", callback_data="back_start")]]
    await update.message.reply_text(
        "🤖 তোমার message পেয়েছি!\n\n/start দিয়ে menu দেখো অথবা নিচের বাটন চাপো।",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ══════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("products", products_cmd))
    app.add_handler(CommandHandler("myorders", my_orders))

    # Admin commands
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("addproduct", add_product))
    app.add_handler(CommandHandler("delproduct", del_product))
    app.add_handler(CommandHandler("listproducts", list_products))
    app.add_handler(CommandHandler("listorders", list_orders))
    app.add_handler(CommandHandler("confirm", confirm_order))
    app.add_handler(CommandHandler("cancel", cancel_order))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("users", list_users))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))

    # Buttons & messages
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))

    print("🤖 Shapps Bot চালু হয়েছে! ২৪/৭ running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
