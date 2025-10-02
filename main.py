import os
import json
import gzip
import random
import re
from io import BytesIO
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputSticker
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")  # @username bot
IS_PREMIUM = os.getenv("BOT_PREMIUM", "false").lower() == "true"

# =========================================================
# States untuk ConversationHandler
# =========================================================
ASK_PACK_NAME, ASK_TGS_FILE = range(2)

# =========================================================
# Helper: JSON -> gzip TGS
# =========================================================
def gzip_bytes(data: bytes) -> BytesIO:
    out = BytesIO()
    with gzip.GzipFile(fileobj=out, mode="w") as f:
        f.write(data)
    out.seek(0)
    out.name = "emoji.tgs"
    return out

def json_to_tgs(json_bytes: bytes) -> BytesIO:
    return gzip_bytes(json_bytes)

def optimize_json_to_tgs(json_bytes: bytes) -> BytesIO:
    data = json.loads(json_bytes.decode("utf-8"))
    def round_numbers(obj):
        if isinstance(obj, dict):
            return {k: round_numbers(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [round_numbers(v) for v in obj]
        elif isinstance(obj, float):
            return round(obj, 3)
        return obj
    data = round_numbers(data)
    compact = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return gzip_bytes(compact)

def reduce_keyframes_json(json_bytes: bytes) -> BytesIO:
    data = json.loads(json_bytes.decode("utf-8"))
    def simplify_keyframes(obj):
        if isinstance(obj, dict):
            if "k" in obj and isinstance(obj["k"], list) and len(obj["k"]) > 2:
                obj["k"] = obj["k"][::2]
            for v in obj.values():
                simplify_keyframes(v)
        elif isinstance(obj, list):
            for item in obj:
                simplify_keyframes(item)
    simplify_keyframes(data)
    compact = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return gzip_bytes(compact)

def auto_compress(json_bytes: bytes):
    methods = [
        ("Normal", json_to_tgs),
        ("Optimized Safe", optimize_json_to_tgs),
        ("Reduce Keyframes", reduce_keyframes_json),
    ]
    for name, func in methods:
        tgs_file = func(json_bytes)
        size_kb = len(tgs_file.getvalue()) / 1024
        if size_kb <= 64:
            return tgs_file, name, size_kb
    return tgs_file, name, size_kb

def random_suffix(n=6):
    import string
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))

# =========================================================
# Telegram Sticker Set (PTB v23+)
# =========================================================
async def create_user_sticker_set(update: Update, context: ContextTypes.DEFAULT_TYPE, tgs_file: BytesIO, set_name: str, title: str):
    user = update.effective_user
    bot = context.bot

    tgs_file.seek(0)
    sticker = InputSticker(sticker=tgs_file, emoji_list=["😀"], format="animated")
    stickers = [sticker]

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
    if data == "menu_convert":
        context.user_data["mode"] = "convert"
        await query.edit_message_text("📌 Silakan kirim file `.json` untuk Convert.")
    elif data == "menu_autocompress":
        context.user_data["mode"] = "autocompress"
        await query.edit_message_text("📌 Silakan kirim file `.json` untuk Auto Compress.")
    elif data == "menu_upload":
        if not IS_PREMIUM:
            await query.edit_message_text("⚠️ Bot tidak premium. Upgrade untuk fitur upload emoji set dengan link shareable.")
            return
        context.user_data["mode"] = "upload"
        await query.edit_message_text("📌 Silakan masukkan *nama pack/sticker set* untuk link custom:")
        return ASK_PACK_NAME

# ===================== ConversationHandler untuk upload =====================
async def ask_pack_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    # validasi nama: hanya huruf, angka, underscore, max 64
    if not re.match(r"^[a-z0-9_]{1,64}$", text):
        await update.message.reply_text("❌ Nama pack tidak valid. Gunakan huruf kecil, angka, underscore, max 64 karakter.")
        return ASK_PACK_NAME
    context.user_data["custom_pack_name"] = text
    await update.message.reply_text("📌 Sekarang kirim file `.tgs` untuk sticker pack ini.")
    return ASK_TGS_FILE

async def receive_tgs_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.lower().endswith(".tgs"):
        await update.message.reply_text("❌ Tolong kirim file `.tgs`.")
        return ASK_TGS_FILE
    file = await document.get_file()
    tgs_file = BytesIO(await file.download_as_bytearray())
    tgs_file.seek(0)

    pack_name = context.user_data["custom_pack_name"]
    title = f"{update.effective_user.first_name}'s Emoji Set"

    try:
        link = await create_user_sticker_set(update, context, tgs_file, pack_name, title)
        await update.message.reply_text(f"🎉 Kaboom! Emoji set berhasil dibuat.\nLink shareable: {link}")
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal upload emoji set: {e}")

    return ConversationHandler.END

# ===================== Handler untuk JSON (.json) =====================
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
        file = await document.get_file()
        json_bytes = await file.download_as_bytearray()
        context.user_data["json_bytes"] = json_bytes

        if mode == "convert":
            keyboard = [
                [InlineKeyboardButton("🎨 Normal", callback_data="normal")],
                [InlineKeyboardButton("⚡ Optimized Safe", callback_data="optimize")],
                [InlineKeyboardButton("✂️ Reduce Keyframes", callback_data="reduce")],
            ]
            await update.message.reply_text(
                "✅ File JSON diterima! Pilih metode:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            tgs_file, method, size_kb = auto_compress(json_bytes)
            await update.message.reply_sticker(sticker=tgs_file)
            await update.message.reply_text(f"✅ Mode: *{method}*\n📦 Size: {size_kb:.2f} KB", parse_mode="Markdown")

# =========================================================
# Main
# =========================================================
def main():
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button, pattern="^menu_upload$")],
        states={
            ASK_PACK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_pack_name)],
            ASK_TGS_FILE: [MessageHandler(filters.Document.ALL, receive_tgs_file)],
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
