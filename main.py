import os
import json
import gzip
from io import BytesIO
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
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

    def clean(obj):
        if isinstance(obj, dict):
            new_obj = {}
            for k, v in obj.items():
                if v in [0, 0.0, False, None, "", [], {}]:
                    continue
                if k in ["ix", "a", "ddd", "bm", "mn", "hd", "cl", "ln", "tt"]:
                    continue
                new_obj[k] = clean(v)
            return new_obj
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
                obj["k"] = obj["k"][::2]
            for key in obj:
                simplify_keyframes(obj[key])
        elif isinstance(obj, list):
            for item in obj:
                simplify_keyframes(item)

    simplify_keyframes(data)
    compact = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return gzip_bytes(compact)

def compress_json_bytes(json_bytes: bytes) -> BytesIO:
    data = json.loads(json_bytes.decode("utf-8"))

    def round_numbers(obj):
        if isinstance(obj, dict):
            return {k: round_numbers(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [round_numbers(item) for item in obj]
        elif isinstance(obj, float):
            return round(obj, 3)
        return obj

    data = round_numbers(data)
    compact = json.dumps(data, separators=(",", ":")).encode("utf-8")
    out = BytesIO(compact)
    out.name = "compressed.json"
    out.seek(0)
    return out

# =========================================================
# Info & Keyframe Detection
# =========================================================
def extract_json_info(json_bytes: bytes) -> str:
    try:
        data = json.loads(json_bytes.decode("utf-8"))
        layers = len(data.get("layers", []))
        assets = len(data.get("assets", []))
        name = data.get("nm", "Tanpa Nama")
        duration = data.get("op", 0) / data.get("fr", 1)
        return (
            f"📄 *Preview JSON*\n"
            f"• Nama: `{name}`\n"
            f"• Layer: `{layers}`\n"
            f"• Asset: `{assets}`\n"
            f"• Durasi: `{duration:.2f}` detik"
        )
    except Exception:
        return "❌ Gagal membaca isi JSON."

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
        [InlineKeyboardButton("🌘 Convert JSON → TGS", callback_data="menu_convert")],
        [InlineKeyboardButton("🖤 Compress JSON → JSON kecil", callback_data="menu_compress_json")],
        [InlineKeyboardButton("🧨 Reset / Cancel", callback_data="menu_reset")]
    ]
    await update.message.reply_text(
        "🌑 *Dark Dashboard*\nPilih aksi yang kamu mau:",
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

    preview = extract_json_info(json_bytes)
    await update.message.reply_text(preview, parse_mode="Markdown")

    mode_selected = context.user_data.get("mode", "manual")

    if mode_selected == "convert":
        keyboard = [
            [InlineKeyboardButton("🎨 Normal", callback_data="normal")],
            [InlineKeyboardButton("⚡ Optimized Safe", callback_data="optimize")],
            [InlineKeyboardButton("✂️ Reduce Keyframes", callback_data="reduce")],
            [InlineKeyboardButton("❌ Batal", callback_data="menu_reset")]
        ]
        await update.message.reply_text(
            "✅ File JSON diterima!\nPilih metode konversi TGS:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif mode_selected == "compress_json":
        compressed_file = compress_json_bytes(json_bytes)
        await update.message.reply_document(document=InputFile(compressed_file, filename="compressed.json"))
        await update.message.reply_text("✅ JSON berhasil dikompres!")
        del context.user_data["json_bytes"]

    else:
        await update.message.reply_text(
            "✅ File JSON diterima!\nGunakan tombol untuk memilih mode konversi."
        )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if "last_bot_msg" in context.user_data:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=context.user_data["last_bot_msg"])
        except:
            pass

    if query.data == "menu_reset":
        context.user_data.clear()
        await query.edit_message_text("✅ Semua data direset. Mulai lagi dengan /menu.")
        return

    if query.data == "menu_convert":
        context.user_data["mode"] = "convert"
        await query.edit_message_text("📌 Silakan kirim file `.json` untuk *Convert → TGS*.")
        return

    if query.data == "menu_compress_json":
        context.user_data["mode"] = "compress_json"
        await query.edit_message_text("📌 Silakan kirim file `.json` untuk *Compress JSON → JSON kecil*.")
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
        result_msg = await query.message.reply_text(
           
        result_msg = await query.message.reply_text(
            f"✅ Mode: *{mode}*\n📦 Size: {size_kb:.2f} KB",
            parse_mode="Markdown"
        )
        context.user_data["last_bot_msg"] = result_msg.message_id

        if size_kb > 64 and keyframes > 100:
            warning = (
                f"⚠️ File terlalu besar ({size_kb:.2f} KB) dan punya banyak keyframe ({keyframes}).\n"
                "Pilih metode untuk mengurangi ukuran:"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔧 Compress", callback_data="optimize")],
                [InlineKeyboardButton("✂️ Reduce Keyframes", callback_data="reduce")]
            ])
            warn_msg = await query.message.reply_text(warning, reply_markup=keyboard)
            context.user_data["last_bot_msg"] = warn_msg.message_id

        del context.user_data["json_bytes"]

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

