import logging
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

BOT_TOKEN = "8797834602:AAGpI1YHey_RgkO-eZuIJ2hks_AP2w2xcyM"
ADMIN_ID  = 8294795125

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

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

def register_user(user):
    users = load("users.json")
    uid = str(user.id)
    if uid not in users:
        users[uid] = {"id": user.id, "name": user.full_name, "username": user.username or "",
                      "joined": datetime.now().isoformat(), "messages": 0, "banned": False}
    else:
        users[uid]["messages"] = users[uid].get("messages", 0) + 1
    save("users.json", users)

def is_banned(user_id):
    return load("users.json").get(str(user_id), {}).get("banned", False)

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
        f"👋 স্বাগতম {user.first_name}!\n\n🤖 আমি *Shapps Bot*\n\nনিচের বাটন থেকে অপশন বেছে নাও 👇",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Commands:*\n\n/start — শুরু করো\n/products — products দেখো\n/myorders — আমার orders\n/help — সাহায্য",
        parse_mode="Markdown")

async def products_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    prods = load("products.json")
    if not prods:
        await update.message.reply_text("😔 এখন কোনো product নেই।")
        return
    text = "🛍️ *Products:*\n\n"
    kb = []
    for pid, p in prods.items():
        if p.get("active", True):
            text += f"• *{p['name']}* — ৳{p['price']}\n{p.get('desc','')}\n\n"
            kb.append([InlineKeyboardButton(f"🛒 {p['name']}", callback_data=f"order_{pid}")])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb) if kb else None)

async def my_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    orders = load("orders.json")
    my = [o for o in orders.values() if str(o.get("user_id")) == str(update.effective_user.id)]
    if not my:
        await update.message.reply_text("📦 তোমার কোনো order নেই।")
        return
    text = "📦 *তোমার Orders:*\n\n"
    for o in my[-10:]:
        e = {"pending":"⏳","confirmed":"✅","cancelled":"❌"}.get(o.get("status","pending"),"⏳")
        text += f"{e} *{o['product_name']}*\nStatus: {o.get('status','pending')}\n\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_start")]])

    if d == "products":
        prods = load("products.json")
        if not prods:
            await q.edit_message_text("😔 কোনো product নেই।", reply_markup=back_kb)
            return
        text = "🛍️ *Products:*\n\n"
        kb = []
        for pid, p in prods.items():
            if p.get("active", True):
                text += f"• *{p['name']}* — ৳{p['price']}\n{p.get('desc','')}\n\n"
                kb.append([InlineKeyboardButton(f"🛒 {p['name']}", callback_data=f"order_{pid}")])
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_start")])
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("order_"):
        pid = d.replace("order_", "")
        prods = load("products.json")
        p = prods.get(pid)
        if not p:
            await q.edit_message_text("❌ Product পাওয়া যায়নি।")
            return
        orders = load("orders.json")
        oid = str(len(orders) + 1)
        orders[oid] = {"id": oid, "user_id": q.from_user.id, "user_name": q.from_user.full_name,
                       "product_id": pid, "product_name": p["name"], "price": p["price"],
                       "status": "pending", "date": datetime.now().isoformat()}
        save("orders.json", orders)
        try:
            await ctx.bot.send_message(ADMIN_ID,
                f"🛒 *নতুন Order!*\n\n👤 {q.from_user.full_name}\n🆔 `{q.from_user.id}`\n📦 {p['name']}\n💰 ৳{p['price']}\n🔢 #{oid}",
                parse_mode="Markdown")
        except Exception: pass
        await q.edit_message_text(
            f"✅ *Order Confirmed!*\n\n📦 {p['name']}\n💰 ৳{p['price']}\n🔢 #{oid}\n\nAdmin শীঘ্রই যোগাযোগ করবে! 🙏",
            parse_mode="Markdown")

    elif d == "my_orders":
        orders = load("orders.json")
        my = [o for o in orders.values() if str(o.get("user_id")) == str(q.from_user.id)]
        if not my:
            await q.edit_message_text("📦 কোনো order নেই।", reply_markup=back_kb)
            return
        text = "📦 *তোমার Orders:*\n\n"
        for o in my[-10:]:
            e = {"pending":"⏳","confirmed":"✅","cancelled":"❌"}.get(o.get("status","pending"),"⏳")
            text += f"{e} *{o['product_name']}* — ৳{o['price']}\nStatus: {o.get('status','pending')}\n\n"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=back_kb)

    elif d == "help":
        await q.edit_message_text("📋 *Help:*\n\n/start /products /myorders /help",
            parse_mode="Markdown", reply_markup=back_kb)

    elif d == "contact":
        await q.edit_message_text("📞 Admin-কে সরাসরি message করো।", reply_markup=back_kb)

    elif d == "back_start":
        kb = [
            [InlineKeyboardButton("🛍️ Products", callback_data="products"),
             InlineKeyboardButton("📦 My Orders", callback_data="my_orders")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help"),
             InlineKeyboardButton("📞 Contact Admin", callback_data="contact")]
        ]
        await q.edit_message_text("🏠 *Main Menu*\n\nঅপশন বেছে নাও 👇",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

def admin_only(func):
    async def wrapper(update, ctx):
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ তুমি admin না!")
            return
        await func(update, ctx)
    return wrapper

@admin_only
async def admin_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users = load("users.json")
    orders = load("orders.json")
    prods = load("products.json")
    pending = [o for o in orders.values() if o.get("status") == "pending"]
    await update.message.reply_text(
        f"👑 *Admin Panel*\n\n👥 Users: {len(users)}\n📦 Orders: {len(orders)}\n⏳ Pending: {len(pending)}\n🛍️ Products: {len(prods)}\n\n"
        f"/addproduct Name|Price|Desc\n/delproduct id\n/listproducts\n/listorders\n/confirm id\n/cancel id\n/broadcast msg\n/users\n/ban id\n/unban id",
        parse_mode="Markdown")

@admin_only
async def add_product(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("⚠️ `/addproduct Name | Price | Desc`", parse_mode="Markdown")
        return
    parts = " ".join(ctx.args).split("|")
    prods = load("products.json")
    pid = str(len(prods) + 1)
    prods[pid] = {"id": pid, "name": parts[0].strip(), "price": parts[1].strip() if len(parts)>1 else "0",
                  "desc": parts[2].strip() if len(parts)>2 else "", "active": True, "added": datetime.now().isoformat()}
    save("products.json", prods)
    await update.message.reply_text(f"✅ Product যোগ হয়েছে!\n#{pid} {prods[pid]['name']} — ৳{prods[pid]['price']}")

@admin_only
async def del_product(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("⚠️ `/delproduct id`", parse_mode="Markdown")
        return
    prods = load("products.json")
    pid = ctx.args[0]
    if pid in prods:
        name = prods.pop(pid)["name"]
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
    text = "🛍️ *Products:*\n\n" + "\n".join(f"[{pid}] *{p['name']}* — ৳{p['price']}" for pid, p in prods.items())
    await update.message.reply_text(text, parse_mode="Markdown")

@admin_only
async def list_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    orders = load("orders.json")
    if not orders:
        await update.message.reply_text("📦 কোনো order নেই।")
        return
    text = "📋 *Orders:*\n\n"
    for o in list(orders.values())[-20:]:
        e = {"pending":"⏳","confirmed":"✅","cancelled":"❌"}.get(o.get("status","pending"),"⏳")
        text += f"{e} #{o['id']} {o['product_name']} — {o['user_name']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

@admin_only
async def confirm_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("⚠️ `/confirm id`", parse_mode="Markdown")
        return
    orders = load("orders.json")
    oid = ctx.args[0]
    if oid in orders:
        orders[oid]["status"] = "confirmed"
        save("orders.json", orders)
        try: await ctx.bot.send_message(orders[oid]["user_id"], f"✅ Order #{oid} Confirm হয়েছে! ধন্যবাদ 🙏")
        except Exception: pass
        await update.message.reply_text(f"✅ Order #{oid} confirmed!")
    else:
        await update.message.reply_text("❌ Order পাওয়া যায়নি।")

@admin_only
async def cancel_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("⚠️ `/cancel id`", parse_mode="Markdown")
        return
    orders = load("orders.json")
    oid = ctx.args[0]
    if oid in orders:
        orders[oid]["status"] = "cancelled"
        save("orders.json", orders)
        try: await ctx.bot.send_message(orders[oid]["user_id"], f"❌ Order #{oid} Cancel হয়েছে।")
        except Exception: pass
        await update.message.reply_text(f"✅ Order #{oid} cancelled.")
    else:
        await update.message.reply_text("❌ Order পাওয়া যায়নি।")

@admin_only
async def broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("⚠️ `/broadcast message`", parse_mode="Markdown")
        return
    msg = " ".join(ctx.args)
    users = load("users.json")
    sent = failed = 0
    for uid, u in users.items():
        if not u.get("banned"):
            try:
                await ctx.bot.send_message(int(uid), f"📢 *Broadcast:*\n\n{msg}", parse_mode="Markdown")
                sent += 1
            except Exception: failed += 1
    await update.message.reply_text(f"📢 Done!\n✅ Sent: {sent}\n❌ Failed: {failed}")

@admin_only
async def list_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    users = load("users.json")
    if not users:
        await update.message.reply_text("👥 কোনো user নেই।")
        return
    text = f"👥 *Users ({len(users)}):*\n\n"
    for uid, u in list(users.items())[-20:]:
        text += f"{'🚫' if u.get('banned') else '✅'} {u['name']} — `{uid}`\n"
    await update.message.reply_text(text, parse_mode="Markdown")

@admin_only
async def ban_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("⚠️ `/ban id`", parse_mode="Markdown")
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
        await update.message.reply_text("⚠️ `/unban id`", parse_mode="Markdown")
        return
    users = load("users.json")
    uid = ctx.args[0]
    if uid in users:
        users[uid]["banned"] = False
        save("users.json", users)
        await update.message.reply_text(f"✅ User {uid} unbanned!")
    else:
        await update.message.reply_text("❌ User পাওয়া যায়নি।")

async def auto_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_banned(user.id): return
    register_user(user)
    text = update.message.text.lower() if update.message.text else ""
    for rule in load("auto_replies.json").values():
        if rule.get("keyword", "").lower() in text:
            await update.message.reply_text(rule["reply"])
            return
    kb = [[InlineKeyboardButton("🏠 Main Menu", callback_data="back_start")]]
    await update.message.reply_text("🤖 /start দিয়ে menu দেখো 👇", reply_markup=InlineKeyboardMarkup(kb))

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("products", products_cmd))
    app.add_handler(CommandHandler("myorders", my_orders))
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
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))
    print("🤖 Shapps Bot চালু! ২৪/৭ running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
