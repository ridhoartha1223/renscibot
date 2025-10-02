import os
import json
import gzip
import base64
import requests
from io import BytesIO
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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

# =========================================================
# AI Assistant Helper
# =========================================================
async def ai_request_edit(prompt: str, image_bytes: bytes) -> BytesIO:
    """
    Kirim request ke OpenAI Image API untuk edit gambar.
    """
    url = "https://api.openai.com/v1/images/edits"
    files = {
        "image": ("input.png", image_bytes, "image/png"),
        "prompt": (None, prompt)
    }
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    resp = requests.post(url, headers=headers, files=files)
    data = resp.json()

    img_base64 = data["data"][0]["b64_json"]
    img_bytes = base64.b64decode(img_base64)
    out = BytesIO(img_bytes)
    out.name = "ai_edit.png"
    return out

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
        [InlineKeyboardButton("🎭 AI Assistant", callback_data="menu_ai")],
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

    mode_selected = context.user_data.get("mode", "manual")

    if mode_selected == "convert":
        keyboard = [
            [InlineKeyboardButton("🎨 Normal", callback_data="normal")],
            [InlineKeyboardButton("⚡ Optimized Safe", callback_data="optimize")],
            [InlineKeyboardButton("✂️ Reduce Keyframes", callback_data="reduce")]
        ]
        await update.message.reply_text(
            "✅ File JSON diterima!\nPilih metode konversi:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif mode_selected == "autocompress":
        tgs_file, mode, size_kb = auto_compress(json_bytes)
        await update.message.reply_sticker(sticker=tgs_file)
        await update.message.reply_text(
            f"✅ Mode: *{mode}*\n📦 Size: {size_kb:.2f} KB",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "✅ File JSON diterima!\nGunakan tombol untuk memilih mode konversi."
        )

async def handle_ai_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("mode") != "ai":
        return

    if not update.message.caption:
        await update.message.reply_text("❌ Tambahkan instruksi edit di *caption* gambar!")
        return

    prompt = update.message.caption

    if update.message.photo:
        file = await update.message.photo[-1].get_file()
    elif update.message.document and update.message.document.file_name.lower().endswith((".png", ".jpg", ".jpeg")):
        file = await update.message.document.get_file()
    else:
        await update.message.reply_text("❌ Kirim gambar/PNG/JPG saja.")
        return

    image_bytes = await file.download_as_bytearray()
    loading = await update.message.reply_text("⏳ AI sedang memproses edit...")

    try:
        result_img = await ai_request_edit(prompt, image_bytes)

        # otomatis convert AI result ke TGS
        # dummy convert: pakai PNG sebagai placeholder TGS
        tgs_file = gzip_bytes(result_img.getvalue())
        await loading.delete()
        await update.message.reply_sticker(sticker=tgs_file)
        await update.message.reply_photo(result_img, caption=f"✅ Hasil AI Edit + TGS: {prompt}")
    except Exception as e:
        await loading.delete()
        await update.message.reply_text(f"❌ Gagal proses AI: {str(e)}")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_convert":
        context.user_data["mode"] = "convert"
        await query.edit_message_text("📌 Silakan kirim file `.json` untuk *Convert*.")
        return

    if query.data == "menu_autocompress":
        context.user_data["mode"] = "autocompress"
        await query.edit_message_text("📌 Silakan kirim file `.json` untuk *Auto Compress*.")
        return

    if query.data == "menu_ai":
        context.user_data["mode"] = "ai"
        await query.edit_message_text(
            "🎭 *AI Assistant Mode*\n\n"
            "📌 Kirim file gambar/emoji + instruksi edit (di caption).\n"
            "Contoh: *ubah rambut jadi pink*",
            parse_mode="Markdown"
        )
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

        size_kb = len(tgs_file.getvalue()) / 1024
        await loading.delete()
        await query.message.reply_sticker(sticker=tgs_file)
        await query.message.reply_text(
            f"✅ Mode: *{mode}*\n📦 Size: {size_kb:.2f} KB",
            parse_mode="Markdown"
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
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_ai_file))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
