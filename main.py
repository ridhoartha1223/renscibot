import os
import json
import gzip
import random
import string
from io import BytesIO
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputSticker
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")  # @username bot
IS_PREMIUM = os.getenv("BOT_PREMIUM", "false").lower() == "true"  # true jika bot premium

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
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))

# =========================================================
# Telegram Sticker Set
# =========================================================
async def create_user_sticker_set(update: Update, context: ContextTypes.DEFAULT_TYPE, tgs_file: BytesIO):
    user = update.effective_user
    bot = context.bot
    set_name = f"user{user.id}_emoji_{random_suffix()}_by_{BOT_USERNAME.strip('@')}"
    title = f"{user.first_name}'s Emoji Set"

    sticker = InputSticker(sticker=tgs_file)
    stickers = [sticker]

    try:
        await bot.create_new_sticker_set(
            user_id=user.id,
            name=set_name,
            title=title,
            stickers=stickers,
            sticker_format="animated",
            emojis="😀"  # emoji di sini, bukan di InputSticker
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

async def handle_json_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    if mode not in ["convert", "autocompress", "upload"]:
        return

    document = update.message.document
    if not document.file_name.endswith(".json"):
        await update.message.reply_text("❌ Tolong kirim file `.json`.")
        return

    file = await document.get_file()
    json_bytes = await file.download_as_bytearray()
    context.user_data["json_bytes"] = json_bytes

    if mode in ["convert", "autocompress"]:
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
    elif mode == "upload":
        tgs_file, method, size_kb = auto_compress(json_bytes)
        await update.message.reply_sticker(sticker=tgs_file)
        if IS_PREMIUM:
            try:
                link = await create_user_sticker_set(update, context, tgs_file)
                await update.message.reply_text(
                    f"🎉 Kaboom! I've just published your emoji set.\nHere's your link: {link}\n"
                    "You can share it with other Telegram users — they'll be able to add your emoji to their emoji panel!"
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Gagal upload emoji set: {e}")
        else:
            await update.message.reply_text(
                "⚠️ Bot tidak premium. Sticker TGS sudah dikirim, tapi *link shareable custom emoji* tidak tersedia.\n"
                "Upgrade bot ke premium untuk fitur link."
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
        context.user_data["mode"] = "upload"
        await query.edit_message_text("📌 Silakan kirim file `.json` untuk Upload Emoji Set.")

# =========================================================
# Main
# =========================================================
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_json_file))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
