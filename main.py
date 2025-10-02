import os
import tempfile
import gzip
import json
import logging
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
def convert_json_to_tgs(json_path, tgs_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    with gzip.open(tgs_path, "wt", encoding="utf-8") as f:
        json.dump(data, f)

# Fungsi konversi dengan optimize (misal: buang metadata, rapatkan json)
def convert_json_to_tgs_optimize(json_path, tgs_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # contoh optimize sederhana: sort keys & hilangkan indent
    with gzip.open(tgs_path, "wt", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), sort_keys=True)

# Command start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Kirimkan file JSON ke saya untuk convert jadi TGS!")

# Handler file
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith(".json"):
        await update.message.reply_text("⚠️ Harap kirim file dengan format `.json`.")
        return

    file = await document.get_file()
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, document.file_name)
        await file.download_to_drive(json_path)

        # Simpan path di context agar bisa dipakai callback button
        context.user_data["json_path"] = json_path

        # Inline keyboard pilihan
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

    json_path = context.user_data.get("json_path")
    if not json_path or not os.path.exists(json_path):
        await query.edit_message_text("❌ File JSON tidak ditemukan. Kirim ulang.")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        tgs_path = os.path.join(tmpdir, "output.tgs")

        try:
            if query.data == "normal":
                convert_json_to_tgs(json_path, tgs_path)
                mode = "Normal"
            else:
                convert_json_to_tgs_optimize(json_path, tgs_path)
                mode = "Optimize"

            # Kirim hasil sebagai preview sticker
            with open(tgs_path, "rb") as f:
                await query.message.reply_sticker(f)

            # Kirim juga file TGS as document (untuk simpan / upload emoji)
            with open(tgs_path, "rb") as f:
                await query.message.reply_document(
                    f, filename="result.tgs",
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
