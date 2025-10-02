import os
import random
import re
from io import BytesIO
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputSticker
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")  # @username bot
IS_PREMIUM = os.getenv("BOT_PREMIUM", "false").lower() == "true"

# =========================================================
# States ConversationHandler
# =========================================================
ASK_TGS_FILE, ASK_PACK_NAME, ASK_EMOJI = range(3)

# =========================================================
# Helper
# =========================================================
def random_suffix(n=6):
    import string
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))

async def create_user_sticker_set(update: Update, context: ContextTypes.DEFAULT_TYPE, tgs_file: BytesIO, set_name: str, title: str, emoji_char: str):
    user = update.effective_user
    bot = context.bot

    tgs_file.seek(0)
    sticker = InputSticker(sticker=tgs_file, emoji_list=[emoji_char], format="animated")
    stickers = [sticker]

    original_name = set_name
    attempt = 0
    while True:
        try:
            await bot.create_new_sticker_set(
                user_id=user.id,
                name=set_name,
                title=title,
                stickers=stickers
            )
            link = f"https://t.me/addemoji/{set_name}"
            return link
        except Exception as e:
            if "Name is already occupied" in str(e) and attempt < 5:
                set_name = f"{original_name}_{random_suffix(3)}"
                attempt += 1
            else:
                raise Exception(f"Gagal membuat sticker set: {e}")

# =========================================================
# Handlers
# =========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Selamat datang di *Emoji Converter Bot*\nGunakan /menu untuk membuka dashboard.",
        parse_mode="Markdown"
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎨 Convert JSON", callback_data="menu_convert")],
        [InlineKeyboardButton("⚡ Auto Compress", callback_data="menu_autocompress")],
        [InlineKeyboardButton("📤 Upload Emoji Set", callback_data="menu_upload")],
    ]
    await update.message.reply_text(
        "📋 *Dashboard Emoji Bot*\nPilih menu:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_upload":
        if not IS_PREMIUM:
            await query.edit_message_text("⚠️ Bot tidak premium. Upgrade untuk fitur upload emoji set dengan link shareable.")
            return
        context.user_data["mode"] = "upload"
        await query.edit_message_text("📌 Silakan kirim file `.tgs` untuk sticker pack ini.")
        return ASK_TGS_FILE
    elif data == "menu_convert":
        context.user_data["mode"] = "convert"
        await query.edit_message_text("📌 Silakan kirim file `.json` untuk Convert.")
    elif data == "menu_autocompress":
        context.user_data["mode"] = "autocompress"
        await query.edit_message_text("📌 Silakan kirim file `.json` untuk Auto Compress.")

# ===================== Upload Emoji Set Flow =====================
async def receive_tgs_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("mode") != "upload":
        await update.message.reply_text("⚠️ Klik menu *Upload Emoji Set* dulu sebelum kirim file `.tgs`.", parse_mode="Markdown")
        return ConversationHandler.END

    document = update.message.document
    if not document.file_name.lower().endswith(".tgs"):
        await update.message.reply_text("❌ Tolong kirim file `.tgs`.")
        return ASK_TGS_FILE

    file = await document.get_file()
    tgs_file = BytesIO(await file.download_as_bytearray())
    tgs_file.seek(0)
    context.user_data["tgs_file"] = tgs_file

    await update.message.reply_text(
        "📌 Sekarang masukkan nama pack / sticker set (akan jadi link custom, gunakan huruf kecil, angka, underscore, max 64 karakter)."
    )
    return ASK_PACK_NAME

async def ask_pack_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if not re.match(r"^[a-z0-9_]{1,64}$", text):
        await update.message.reply_text("❌ Nama pack tidak valid. Gunakan huruf kecil, angka, underscore, max 64 karakter.")
        return ASK_PACK_NAME
    context.user_data["custom_pack_name"] = text

    await update.message.reply_text("📌 Sekarang pilih emoji untuk sticker ini (misal: 😀).")
    return ASK_EMOJI

async def ask_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        text = "😀"
    context.user_data["emoji_char"] = text[0]

    tgs_file = context.user_data["tgs_file"]
    pack_name = context.user_data["custom_pack_name"]
    title = f"{update.effective_user.first_name}'s Emoji Set"
    emoji_char = context.user_data["emoji_char"]

    try:
        link = await create_user_sticker_set(update, context, tgs_file, pack_name, title, emoji_char)
        await update.message.reply_text(f"🎉 Kaboom! Emoji set berhasil dibuat.\nLink shareable: {link}")
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal upload emoji set: {e}")

    context.user_data.clear()
    return ConversationHandler.END

# ===================== JSON Handlers =====================
async def handle_json_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    if not mode:
        return
    document = update.message.document
    file_name = document.file_name.lower()
    if mode in ["convert", "autocompress"]:
        if not file_name.endswith(".json"):
            await update.message.reply_text("❌ Tolong kirim file `.json`.")
            return
        await update.message.reply_text("✅ File JSON diterima! Pilih metode convert di menu selanjutnya.")

# =========================================================
# Main
# =========================================================
def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button, pattern="^menu_upload$")],
        states={
            ASK_TGS_FILE: [MessageHandler(filters.Document.FileExtension("tgs"), receive_tgs_file)],
            ASK_PACK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_pack_name)],
            ASK_EMOJI: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_emoji)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_json_file))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(conv_handler)

    app.run_polling()

if __name__ == "__main__":
    main()
