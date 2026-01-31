import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")

groups = {}

# التحقق إذا كان المستخدم مشرف
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user:
        user_id = update.effective_user.id
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        return any(admin.user and admin.user.id == user_id for admin in admins)
    return False

# دعم الكتابة من اليمين لليسار
def rtl(text: str) -> str:
    return "\u200f" + text

# تنسيق قائمة الأسماء مع علامة ✅
def format_list(items):
    lines = []
    for i, item in enumerate(items, start=1):
        name = item["name"]
        mark = " ✅" if item.get("read") else ""
        lines.append(f"{i}. {rtl(name)}{mark}")
    return "\n".join(lines)

# إنشاء أو استدعاء بيانات المجموعة
def get_group(chat_id):
    if chat_id not in groups:
        groups[chat_id] = {
            "participants": [],
            "listeners": [],
            "active": False,
            "message_id": None
        }
    return groups[chat_id]

# بناء نص الرسالة
def build_text(group):
    text = (
        "\u200f"
        "               📖🌿 أكاديمية رياض الجنان 🌿📖\n\n"
        "        🌼🌿 اللهم اجعل القرآن ربيع قلوبنا 🌼🌿\n\n"
    )

    text += "*👥 المشاركات:*\n"
    text += format_list(group["participants"]) if group["participants"] else "لا يوجد مسجلات بعد"

    text += "\n\n*🎧 المستمعات:*\n"
    text += format_list(group["listeners"]) if group["listeners"] else "لا يوجد مستمعات بعد"

    text += "\n\n⬇️ الرجاء اختيار حالتك من الأسفل"
    return text

# ✅ لوحة الأزرار بعد التعديل
def build_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ المشاركات", callback_data="join"),
            InlineKeyboardButton("🎧 المستمعات", callback_data="listen"),
        ],
        [
            InlineKeyboardButton("❌ إلغاء التسجيل", callback_data="cancel"),
            InlineKeyboardButton("📖 قرأت", callback_data="read"),
        ],
        [
            InlineKeyboardButton("⛔️ إيقاف الإعلان", callback_data="stop"),
            InlineKeyboardButton("🔔 بدأت الحلقة!", callback_data="tag_all"),
        ]
    ])

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except:
        pass

    if not await is_admin(update, context):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ هذا الأمر مخصص للمشرفين فقط"
        )
        return

    chat_id = update.effective_chat.id
    group = get_group(chat_id)

    group["participants"].clear()
    group["listeners"].clear()
    group["active"] = True

    if group["message_id"]:
        try:
            await context.bot.delete_message(chat_id, group["message_id"])
        except:
            pass

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=build_text(group),
        reply_markup=build_keyboard(),
        parse_mode="Markdown"
    )

    group["message_id"] = msg.message_id

# التعامل مع الأزرار
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat.id
    group = get_group(chat_id)

    user_name = query.from_user.full_name or "غير معروف"

    if not group["active"]:
        await query.answer("⛔️ التسجيل مغلق", show_alert=True)
        return

    # إيقاف الإعلان
    if query.data == "stop":
        if not await is_admin(update, context):
            await query.answer("❌ للمشرفين فقط", show_alert=True)
            return
        group["active"] = False
        await query.edit_message_reply_markup(None)
        return

    # مشاركة
    if query.data == "join":
        if not any(p["name"] == user_name for p in group["participants"]):
            group["participants"].append({"name": user_name, "read": False})
        group["listeners"] = [l for l in group["listeners"] if l["name"] != user_name]

    # مستمعة
    elif query.data == "listen":
        if not any(l["name"] == user_name for l in group["listeners"]):
            group["listeners"].append({"name": user_name, "read": False})
        group["participants"] = [p for p in group["participants"] if p["name"] != user_name]

    # إلغاء
    elif query.data == "cancel":
        group["participants"] = [p for p in group["participants"] if p["name"] != user_name]
        group["listeners"] = [l for l in group["listeners"] if l["name"] != user_name]

    # ✅ زر قرأت
    elif query.data == "read":
        for p in group["participants"]:
            if p["name"] == user_name:
                p["read"] = not p["read"]
        for l in group["listeners"]:
            if l["name"] == user_name:
                l["read"] = not l["read"]
        await query.answer("✅ تم تحديث حالتك")

    # 🔔 بدأت الحلقة
    elif query.data == "tag_all":
        if not await is_admin(update, context):
            await query.answer("❌ للمشرفين فقط", show_alert=True)
            return
        msg = await context.bot.send_message(chat_id, "🔔 بدأت الحلقة!")
        await asyncio.sleep(600)
        try:
            await context.bot.delete_message(chat_id, msg.message_id)
        except:
            pass

    await query.edit_message_text(
        build_text(group),
        reply_markup=build_keyboard(),
        parse_mode="Markdown"
    )

# تشغيل البوت
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
