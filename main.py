import json
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ===================== Fungsi Konversi =====================

def convert_json_to_tgs(json_bytes):
    """Konversi JSON ke TGS tanpa optimasi."""
    return BytesIO(json_bytes)

def optimize_json_to_tgs(json_bytes):
    """Optimasi sederhana: hapus whitespace JSON."""
    data = json.loads(json_bytes.decode("utf-8"))
    optimized = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return BytesIO(optimized)

def simplify_keyframes(json_bytes, step=2):
    """Kurangi jumlah keyframes dengan cara sampling setiap 'step' frame."""
    data = json.loads(json_bytes.decode("utf-8"))

    def reduce_keys(keys):
        if isinstance(keys, list):
            return keys[::step]  # ambil tiap 'step'
        return keys

    # Traverse semua animasi layer
    if "layers" in data:
        for layer in data["layers"]:
            if "ks" in layer:  # transform
                for k in layer["ks"].values():
                    if isinstance(k, dict) and "k" in k and isinstance(k["k"], list):
                        k["k"] = reduce_keys(k["k"])

    optimized = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return BytesIO(optimized)

# ===========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Kirim file .json untuk saya konversi jadi emoji animasi (.tgs)")

async def handle_json(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".json"):
        await update.message.reply_text("❌ Harus kirim file JSON")
        return

    file = await doc.get_file()
    json_bytes = await file.download_as_bytearray()
    context.user_data["json_bytes"] = json_bytes

    keyboard = [
        [InlineKeyboardButton("🔄 JSON ➝ TGS Normal", callback_data="normal")],
        [InlineKeyboardButton("⚡ JSON ➝ TGS Optimized", callback_data="optimize")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Pilih mode konversi:", reply_markup=reply_markup)

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
        elif query.data == "optimize":
            tgs_file = optimize_json_to_tgs(json_bytes)
            mode = "Optimized"
        elif query.data == "reduce_keyframes":
            tgs_file = simplify_keyframes(json_bytes, step=2)
            mode = "Reduced Keyframes"
        else:
            return

        # Hitung size file
        file_size = len(tgs_file.getvalue())
        size_kb = round(file_size / 1024, 2)

        # ✅ Kirim emoji animasi
        await query.message.reply_sticker(
            sticker=InputFile(tgs_file, filename=f"{mode}.tgs")
        )

        if file_size <= 64 * 1024:
            msg = (
                f"✅🟢 Konversi selesai ({mode})\n"
                f"📦 Ukuran file: {size_kb} KB\n\n"
                f"Siap diunggah sebagai **Emoji Premium** 🚀"
            )
            await query.message.reply_text(msg, parse_mode="Markdown")
        else:
            msg = (
                f"❌🔴 Konversi selesai ({mode})\n"
                f"📦 Ukuran file: {size_kb} KB\n\n"
                f"⚠️ Ukuran melebihi batas 64KB.\n"
                f"👉 Pilih opsi optimasi untuk memperkecil file."
            )
            keyboard = [
                [InlineKeyboardButton("✂️ Kurangi Keyframes", callback_data="reduce_keyframes")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        await query.message.reply_text(f"❌ Gagal convert: {e}")

# ===================== MAIN =====================

def main():
    import os
    TOKEN = os.getenv("BOT_TOKEN")  # ambil token dari Railway ENV
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.FileExtension("json"), handle_json))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
