import os
import json
import gzip
from io import BytesIO
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# =========================================================
# Helper: convert JSON -> gzip TGS
# =========================================================
def gzip_bytes(data: bytes) -> BytesIO:
    out = BytesIO()
    with gzip.GzipFile(fileobj=out, mode="w") as f:
        f.write(data)
    out.seek(0)
    out.name = "emoji.tgs"
    return out

def json_to_tgs(json_bytes: bytes) -> BytesIO:
    """Normal convert (raw json -> tgs)"""
    return gzip_bytes(json_bytes)

def optimize_json_to_tgs(json_bytes: bytes) -> BytesIO:
    """Safe optimize: minify + round float, tetap animasi"""
    data = json.loads(json_bytes.decode("utf-8"))

    # round angka dengan aman
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
    """Kurangi keyframes untuk size reduction"""
    data = json.loads(json_bytes.decode("utf-8"))

    def simplify_keyframes(obj):
        if isinstance(obj, dict):
            if "k" in obj and isinstance(obj["k"], list) and len(obj["k"]) > 2:
                obj["k"] = obj["k"][::2]  # buang setengah keyframes
            for v in obj.values():
                simplify_keyframes(v)
        elif isinstance(obj, list):
            for item in obj:
                simplify_keyframes(item)

    simplify_keyframes(data)
    compact = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return gzip_bytes(compact)

# =========================================================
# Handlers
# =========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 Selamat datang di *Emoji Converter Bot*\n\n"
        "Aku bisa mengubah file **JSON (AE/Bodymovin)** jadi animasi **TGS** untuk Emoji Premium Telegram.\n\n"
        "📌 Cara pakai:\n"
        "1️⃣ Kirim file `.json` hasil export dari After Effects\n"
        "2️⃣ Pilih metode konversi:\n"
        "   • 🎨 Normal → langsung jadi TGS\n"
        "   • ⚡ Optimized Safe → lebih kecil, tetap animasi\n"
        "3️⃣ Kalau file >64KB → akan muncul opsi ✂️ Reduce Keyframes otomatis\n\n"
        "🚀 Ayo coba kirim file JSON-mu sekarang!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith(".json"):
        await update.message.reply_text("❌ Tolong kirim file dengan format `.json`.")
        return

    file = await document.get_file()
    json_bytes = await file.download_as_bytearray()
    context.user_data["json_bytes"] = json_bytes

    keyboard = [
        [InlineKeyboardButton("🎨 JSON → TGS", callback_data="normal")],
        [InlineKeyboardButton("⚡ JSON → TGS (Optimized Safe)", callback_data="optimize")]
    ]
    await update.message.reply_text(
        "✅ File JSON diterima!\nPilih metode konversi:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if "json_bytes" not in context.user_data:
        await query.edit_message_text("❌ File JSON tidak ditemukan. Kirim ulang.")
        return

    json_bytes = context.user_data["json_bytes"]

    try:
        # tampilkan loading
        loading = await query.message.reply_text("⏳ Sedang memproses konversi...")

        if query.data == "normal":
            tgs_file = json_to_tgs(json_bytes)
            mode = "Normal"
        elif query.data == "optimize":
            tgs_file = optimize_json_to_tgs(json_bytes)
            mode = "Optimized Safe"
        elif query.data == "reduce":
            tgs_file = reduce_keyframes_json(json_bytes)
            mode = "Reduce Keyframes"
        else:
            return

        size_kb = len(tgs_file.getvalue()) / 1024
        if size_kb <= 64:
            indicator = "🟢"
            note = "Ukuran aman untuk Emoji Premium!"
        else:
            indicator = "🔴"
            note = "File terlalu besar, coba Reduce Keyframes!"

        # hapus pesan loading
        await loading.delete()

        # kirim animasi sebagai sticker
        await query.message.reply_sticker(
            sticker=tgs_file,
        )
        await query.message.reply_text(
            f"✅ Konversi *{mode}* selesai!\n"
            f"📦 Size: {size_kb:.2f} KB\n"
            f"{indicator} {note}",
            parse_mode="Markdown"
        )

        # kalau kegedean, kasih opsi reduce keyframes
        if size_kb > 64 and query.data != "reduce":
            keyboard = [[InlineKeyboardButton("✂️ Reduce Keyframes", callback_data="reduce")]]
            await query.message.reply_text(
                "⚠️ File terlalu besar, mau coba kurangi keyframes?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    except Exception as e:
        await query.message.reply_text(f"❌ Gagal convert: {str(e)}")

# =========================================================
# Main
# =========================================================
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
