import os
import tempfile
import gzip
import json
import logging
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, MessageHandler, filters, InlineQueryHandler, ContextTypes

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token dari Railway ENV
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Fungsi konversi JSON -> TGS
def convert_json_to_tgs(json_path, tgs_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with gzip.open(tgs_path, "wt", encoding="utf-8") as f:
        json.dump(data, f)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Halo! Kirimkan file JSON (Lottie) ke saya, "
        "nanti otomatis saya convert jadi file .TGS.\n\n"
        "💡 Inline mode juga tersedia: ketik `@YourBot` di chat."
    )

# Handler untuk file JSON
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if not document.file_name.endswith(".json"):
        await update.message.reply_text("⚠️ Harap kirim file dengan format `.json`.")
        return

    file = await document.get_file()
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, document.file_name)
        tgs_path = os.path.join(tmpdir, "output.tgs")

        await file.download_to_drive(json_path)

        try:
            convert_json_to_tgs(json_path, tgs_path)

            # 1. Preview sebagai sticker
            with open(tgs_path, "rb") as f:
                await update.message.reply_sticker(f)

            # 2. Kirim file .tgs untuk diupload manual ke Emoji
            with open(tgs_path, "rb") as f:
                await update.message.reply_document(f, filename="emoji.tgs",
                                                    caption="📂 Ini file TGS kamu.\n"
                                                            "➡️ Upload ke menu *Emoji Kustom* di Telegram.")

        except Exception as e:
            await update.message.reply_text(f"❌ Gagal convert: {e}")

# Inline query handler
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query

    if not query:
        return

    results = [
        InlineQueryResultArticle(
            id="1",
            title="Convert JSON → TGS",
            description="Gunakan bot ini untuk convert file JSON jadi TGS",
            input_message_content=InputTextMessageContent(
                "📂 Kirim file JSON ke bot ini, nanti otomatis dikonversi jadi TGS."
            ),
        )
    ]

    await update.inline_query.answer(results, cache_time=1)

def main():
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN belum di-set di Railway ENV")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(InlineQueryHandler(inline_query))

    app.run_polling()

if __name__ == "__main__":
    main()

