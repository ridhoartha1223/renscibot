import os
import gzip
import json
import logging
import io
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Fungsi konversi normal
def convert_json_to_tgs(json_bytes: bytes) -> bytes:
    data = json.loads(json_bytes.decode("utf-8"))
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="w") as f:
        f.write(json.dumps(data).encode("utf-8"))
    buf.seek(0)
    return buf.read()

# Fungsi konversi optimize
def convert_json_to_tgs_optimize(json_bytes: bytes) -> bytes:
    data = json.loads(json_bytes.decode("utf-8"))
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="w") as f:
        f.write(json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    buf.seek(0)
    return buf.read()

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Kirimkan file `.json` untuk saya convert ke TGS!")

# Handler file
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith(".json"):
        await update.message.reply_text("⚠️ Harap kirim file dengan format `.json`.")
        return

    file = await document.get_file()
    file_bytes = await file.download_as_bytearray()

    # Simpan JSON di memory user
    context.user_data["json_bytes"] = file_bytes

    # Kirim tombol
    keyboard = [
        [
            InlineKeyboardButton("📂 JSON → TGS", callback_data="normal"),
            InlineKeyboardButton("⚡ JSON → TGS Optimize", callback_data="optimize"),
        ]
    ]
    await update.message.reply_text(
        "Pilih mode konversi:", reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Callback tombol
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    json_bytes = context.user_data.get("json_bytes")
    if not json_bytes:
        await query.edit_message_text("❌ File JSON tidak ditemukan. Kirim ulang.")
        return

    try:
        if query.data == "normal":
            tgs_data = convert_json_to_tgs(json_bytes)
            mode = "Normal"
        else:
            tgs_data = convert_json_to_tgs_optimize(json_bytes)
            mode = "Optimize"

        # Preview sebagai sticker
        await query.message.reply_sticker(tgs_data)

        # Kirim juga file .tgs untuk simpan/upload manual
        await query.message.reply_document(
            document=tgs_data,
            filename="result.tgs",
            caption=f"✅ Konversi selesai dengan mode *{mode}*"
        )

    except Exception as e:
        await query.message.reply_text(f"❌ Gagal convert: {e}")

def main():
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN belum di-set di Railway ENV")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))

    app.run_polling()

if __name__ == "__main__":
    main()
