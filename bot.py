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

# تنسيق قائمة الأسماء
def format_list(items):
    return "\n".join(f"{i}. {rtl(name)}" for i, name in enumerate(items, start=1))

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
        "*📖🌿 أكاديمية رياض الجنان 🌿📖*\n"
        "*📖🌿 Riyad Al-Jenan Academy 🌿📖*\n\n"
        "🌿🌼 بإدارة نجلاء درابسة 🌼🌿\n\n"
    )
    text += "*👥 المشاركون:*\n"
    text += format_list(group["participants"]) if group["participants"] else "لا يوجد مسجلون بعد"

    text += "\n\n*🎧 المستمعون:*\n"
    text += format_list(group["listeners"]) if group["listeners"] else "لا يوجد مستمعون بعد"

    text += (
        "\n\n*📖 القرآن شفاء للقلوب ونور للحياة*\n"
        "جددي نيتك وابدئي، والله ييسّر 🤲🌸\n\n"
        "⬇️ الرجاء اختيار حالتك من الأسفل"
    )
    return text

# بناء لوحة الأزرار
def build_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ مشاركة", callback_data="join"),
            InlineKeyboardButton("🎧 مستمع", callback_data="listen"),
        ],
        [
            InlineKeyboardButton("❌ إلغاء التسجيل", callback_data="cancel"),
        ],
        [
            InlineKeyboardButton("⛔️ إيقاف الإعلان", callback_data="stop"),
            InlineKeyboardButton("📢 تاغ المجموعة", callback_data="tag_all"),
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

    if not group["active"]:
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

    user = query.from_user.full_name or "غير معروف"

    # إيقاف الإعلان
    if query.data == "stop":
        if not await is_admin(update, context):
            await query.answer("❌ للمشرفين فقط", show_alert=True)
            return

        group["active"] = False
        group["message_id"] = None
        await query.edit_message_reply_markup(None)
        await query.answer("✅ تم إيقاف الإعلان", show_alert=True)
        return

    # التأكد أن التسجيل مفتوح
    if not group["active"]:
        await query.answer("⛔️ التسجيل مغلق", show_alert=True)
        return

    # تسجيل مشارك
    if query.data == "join":
        if user not in group["participants"]:
            group["participants"].append(user)
        if user in group["listeners"]:
            group["listeners"].remove(user)

    # تسجيل مستمع
    elif query.data == "listen":
        if user not in group["listeners"]:
            group["listeners"].append(user)
        if user in group["participants"]:
            group["participants"].remove(user)

    # إلغاء التسجيل
    elif query.data == "cancel":
        if user in group["participants"]:
            group["participants"].remove(user)
        if user in group["listeners"]:
            group["listeners"].remove(user)

    # تاغ جميع أعضاء المجموعة (للمشرفين فقط)
    elif query.data == "tag_all":
        if not await is_admin(update, context):
            await query.answer("❌ للمشرفين فقط", show_alert=True)
            return

        msg = await context.bot.send_message(
            chat_id=chat_id,
            text="📢 @everyone جميع أعضاء المجموعة!",  # يمكنك تعديل النص حسب الحاجة
        )
        await query.answer("✅ تم تاغ جميع أعضاء المجموعة مؤقتًا", show_alert=True)

        # حذف الرسالة بعد 20 دقيقة
        await asyncio.sleep(1200)
        try:
            await context.bot.delete_message(chat_id, msg.message_id)
        except:
            pass

    # تحديث الرسالة الرئيسية بعد أي تغيير
    await query.edit_message_text(
        build_text(group),
        reply_markup=build_keyboard(),
        parse_mode="Markdown"
    )

# التشغيل الرئيسي للبوت
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
