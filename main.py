import os
import json
import gzip
from io import BytesIO
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# -------------------- UTILITIES --------------------
def gzip_bytes(data: bytes) -> BytesIO:
    out = BytesIO()
    with gzip.GzipFile(fileobj=out, mode="w", compresslevel=9) as f:
        f.write(data)
    out.seek(0)
    out.name = "emoji.tgs"
    return out

def json_to_tgs(json_bytes: bytes) -> BytesIO:
    return gzip_bytes(json_bytes)

def optimize_json_to_tgs(json_bytes: bytes) -> BytesIO:
    data = json.loads(json_bytes.decode("utf-8"))
    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items() 
                    if v not in [0, 0.0, False, None, "", [], {}] 
                    and k not in ["ix", "a", "ddd", "bm", "mn", "hd", "cl", "ln", "tt"]}
        elif isinstance(obj, list):
            return [clean(item) for item in obj if item not in [None, {}, []]]
        elif isinstance(obj, float):
            return round(obj, 3)
        return obj
    cleaned = clean(data)
    compact = json.dumps(cleaned, separators=(",", ":")).encode("utf-8")
    return gzip_bytes(compact)

def reduce_keyframes_json(json_bytes: bytes) -> BytesIO:
    data = json.loads(json_bytes.decode("utf-8"))
    def simplify_keyframes(obj):
        if isinstance(obj, dict):
            if "k" in obj and isinstance(obj["k"], list) and len(obj["k"]) > 2:
                # Hanya hapus keyframe jika ada waktu 't'
                if all(isinstance(kf, dict) and "t" in kf for kf in obj["k"]):
                    obj["k"] = obj["k"][::2]
            for key in obj:
                simplify_keyframes(obj[key])
        elif isinstance(obj, list):
            for item in obj:
                simplify_keyframes(item)
    simplify_keyframes(data)
    compact = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return gzip_bytes(compact)

def count_keyframes(json_bytes: bytes) -> int:
    try:
        data = json.loads(json_bytes.decode("utf-8"))
        count = 0
        for layer in data.get("layers", []):
            for prop in layer.get("ks", {}).values():
                if isinstance(prop, dict) and isinstance(prop.get("k"), list):
                    count += len(prop["k"])
        return count
    except Exception:
        return 0

def extract_json_info(json_bytes: bytes) -> str:
    try:
        data = json.loads(json_bytes.decode("utf-8"))
        layers = len(data.get("layers", []))
        assets = len(data.get("assets", []))
        name = data.get("nm", "Tanpa Nama")
        duration = data.get("op", 0) / data.get("fr", 1)
        size_kb = len(json_bytes) / 1024
        return (
            f"📄 *Preview JSON*\n"
            f"• Nama: `{name}`\n"
            f"• Layer: `{layers}`\n"
            f"• Asset: `{assets}`\n"
            f"• Durasi: `{duration:.2f}` detik\n"
            f"• Ukuran file: `{size_kb:.2f} KB`"
        )
    except Exception:
        return "❌ Gagal membaca isi JSON."

# -------------------- HANDLERS --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📄 Kirim JSON", callback_data="send_json")],
        [InlineKeyboardButton("ℹ️ Bantuan", callback_data="help")]
    ]
    await update.message.reply_text(
        "👋 Hai! Aku bot untuk mengubah file JSON menjadi TGS (Telegram Sticker).\n\n"
        "Klik tombol di bawah untuk mulai!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith(".json"):
        await update.message.reply_text("❌ Tolong kirim file dengan format `.json`.")
        return

    file = await document.get_file()
    json_bytes = await file.download_as_bytearray()
    context.user_data["json_bytes"] = json_bytes

    preview = extract_json_info(json_bytes)
    await update.message.reply_text(preview, parse_mode="Markdown")

    keyboard = [
        [InlineKeyboardButton("🎨 Normal", callback_data="normal")],
        [InlineKeyboardButton("⚡ Optimized Safe", callback_data="optimize")],
        [InlineKeyboardButton("✂️ Reduce Keyframes", callback_data="reduce")],
        [InlineKeyboardButton("❌ Batal", callback_data="reset")]
    ]
    await update.message.reply_text(
        "✅ File JSON diterima!\nPilih metode konversi TGS:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "reset":
        context.user_data.clear()
        await query.edit_message_text("✅ Semua data direset. Kirim file baru untuk mulai lagi.")
        return
    if query.data in ["help", "send_json"]:
        if query.data == "help":
            text = (
                "ℹ️ *Panduan Penggunaan*\n\n"
                "1. Kirim file `.json` animasi Lottie.\n"
                "2. Pilih mode konversi:\n"
                "   • Normal → Konversi standar\n"
                "   • Optimized Safe → Hapus data tidak penting\n"
                "   • Reduce Keyframes → Kurangi jumlah keyframe\n"
                "3. Terima hasil `.tgs` siap pakai sebagai stiker Telegram."
            )
            await query.edit_message_text(text, parse_mode="Markdown")
        elif query.data == "send_json":
            await query.edit_message_text("📤 Silakan kirim file `.json` untuk dikonversi.")
        return

    if "json_bytes" not in context.user_data:
        await query.edit_message_text("❌ File JSON tidak ditemukan. Kirim ulang.")
        return

    json_bytes = context.user_data["json_bytes"]

    try:
        loading = await query.message.reply_text("⏳ Sedang memproses...")

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

        await loading.delete()

        size_kb = len(tgs_file.getvalue()) / 1024
        keyframes = count_keyframes(json_bytes)

        await query.message.reply_sticker(sticker=InputFile(tgs_file, filename="emoji.tgs"))
        await query.message.reply_text(
            f"✅ Mode: *{mode}*\n📦 Size: {size_kb:.2f} KB\n🔑 Keyframes: {keyframes}",
            parse_mode="Markdown"
        )

        del context.user_data["json_bytes"]

    except Exception as e:
        await query.message.reply_text(f"❌ Gagal convert: {str(e)}")

# -------------------- MAIN --------------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
