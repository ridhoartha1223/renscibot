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

# =========================================================
# Auto Compress Helper
# =========================================================
def auto_compress(json_bytes: bytes) -> (BytesIO, str, float):
    """Coba berbagai level sampai <64KB"""
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

    # fallback: kembalikan hasil terakhir
    return tgs_file, name, size_kb

# =========================================================
# Handlers
# =========================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 Selamat datang di *Emoji Converter Bot*\n\n"
        "Aku bisa mengubah file **JSON (AE/Bodymovin)** jadi animasi **TGS**.\n\n"
        "📌 Gunakan /menu untuk membuka dashboard."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎨 Convert JSON", callback_data="menu_convert")],
        [InlineKeyboardButton("⚡ Auto Compress", callback_data="menu_autocompress")],
        [InlineKeyboardButton("📦 History (soon)", callback_data="menu_history")],
        [InlineKeyboardButton("➕ Add to Pack (soon)", callback_data="menu_addpack")]
    ]
    await update.message.reply_text(
        "📋 *Dashboard Emoji Bot*\nPilih menu yang kamu mau:",
        parse_mode="Markdown",
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

    keyboard = [
        [InlineKeyboardButton("🎨 Normal", callback_data="normal")],
        [InlineKeyboardButton("⚡ Optimized Safe", callback_data="optimize")],
        [InlineKeyboardButton("🤖 Auto Compress", callback_data="autocompress")]
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
        loading = await query.message.reply_text("⏳ Sedang memproses...")

        if query.data == "normal":
            tgs_file = json_to_tgs(json_bytes)
            mode = "Normal"
            size_kb = len(tgs_file.getvalue()) / 1024
        elif query.data == "optimize":
            tgs_file = optimize_json_to_tgs(json_bytes)
            mode = "Optimized Safe"
            size_kb = len(tgs_file.getvalue()) / 1024
        elif query.data == "reduce":
            tgs_file = reduce_keyframes_json(json_bytes)
            mode = "Reduce Keyframes"
            size_kb = len(tgs_file.getvalue()) / 1024
        elif query.data in ["autocompress", "menu_autocompress"]:
            tgs_file, mode, size_kb = auto_compress(json_bytes)
        elif query.data == "menu_convert":
            await query.edit_message_text("📌 Kirim file `.json` untuk convert.")
            return
        else:
            return

        if size_kb <= 64:
            indicator = "🟢"
            note = "Ukuran aman untuk Emoji Premium!"
        else:
            indicator = "🔴"
            note = "Masih terlalu besar!"

        await loading.delete()
        await query.message.reply_sticker(sticker=tgs_file)
        await query.message.reply_text(
            f"✅ Mode: *{mode}*\n"
            f"📦 Size: {size_kb:.2f} KB\n"
            f"{indicator} {note}",
            parse_mode="Markdown"
        )

        if size_kb > 64 and query.data not in ["reduce", "autocompress"]:
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
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
