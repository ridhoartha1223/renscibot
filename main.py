import os
import json
import gzip
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ========= Konversi JSON ke TGS =========
def convert_json_to_tgs(json_bytes: bytes) -> BytesIO:
    """Convert JSON -> TGS tanpa optimasi"""
    data = json.loads(json_bytes.decode("utf-8"))
    compact = json.dumps(data, separators=(',', ':')).encode("utf-8")

    buffer = BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="w", compresslevel=9) as f:
        f.write(compact)
    buffer.seek(0)
    buffer.name = "result.tgs"
    return buffer

def optimize_json_to_tgs(json_bytes: bytes) -> BytesIO:
    """Convert JSON -> TGS optimized (target <64KB untuk emoji premium)"""
    data = json.loads(json_bytes.decode("utf-8"))

    # Turunkan framerate jika terlalu tinggi
    if "fr" in data and data["fr"] > 30:
        data["fr"] = 30

    # Hapus metadata tidak penting
    for key in ["meta"]:
        if key in data:
            del data[key]

    # Serialize JSON dengan compact (tanpa spasi)
    compact = json.dumps(data, separators=(',', ':')).encode("utf-8")

    # Gzip ke TGS
    buffer = BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="w", compresslevel=9) as f:
        f.write(compact)
    buffer.seek(0)
    buffer.name = "result_optimized.tgs"
    return buffer

# ========= Handler =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Kirim file JSON hasil export Bodymovin (AE).")

async def handle_json(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith(".json"):
        await update.message.reply_text("❌ Hanya mendukung file .json dari Bodymovin.")
        return

    file = await doc.get_file()
    json_bytes = await file.download_as_bytearray()

    # Simpan ke user_data untuk tombol
    context.user_data["json_bytes"] = json_bytes

    # Kirim tombol pilihan
    keyboard = [
        [
            InlineKeyboardButton("📦 JSON → TGS Normal", callback_data="normal"),
            InlineKeyboardButton("⚡ JSON → TGS Optimized", callback_data="optimize"),
        ]
    ]
    await update.message.reply_text(
        "Pilih mode konversi:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    json_bytes = context.user_data.get("json_bytes")
    if not json_bytes:
        await query.edit_message_text("❌ File JSON tidak ditemukan. Kirim ulang.")
        return

    try:
        if query.data == "normal":
            tgs_file = convert_json_to_tgs(json_bytes)
            mode = "Normal"
        else:
            tgs_file = optimize_json_to_tgs(json_bytes)
            mode = "Optimized"

        # ✅ Kirim sebagai animasi sticker (bukan dokumen!)
        await query.message.reply_sticker(sticker=InputFile(tgs_file, filename=tgs_file.name))

        # Opsional: kirim juga file .tgs (backup)
        await query.message.reply_document(
            document=InputFile(tgs_file, filename=tgs_file.name),
            caption=f"✅ Konversi selesai ({mode})"
        )

    except Exception as e:
        await query.message.reply_text(f"❌ Gagal convert: {e}")

# ========= Main =========
def main():
    token = os.getenv("BOT_TOKEN")  # set di Railway sebagai env var
    app = Appl
