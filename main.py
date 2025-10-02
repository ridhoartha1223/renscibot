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

def optimize_json_level(json_bytes: bytes, level_percent: int) -> BytesIO:
    data = json.loads(json_bytes.decode("utf-8"))

    def clean(obj, level):
        if isinstance(obj, dict):
            new_obj = {}
            for k, v in obj.items():
                if k in ["layers", "assets", "fr", "op", "ip", "nm"]:
                    new_obj[k] = clean(v, level)
                    continue
                if k == "ks" and isinstance(v, dict):
                    new_obj[k] = {}
                    for prop, val in v.items():
                        if isinstance(val, dict) and "k" in val and isinstance(val["k"], list):
                            step = max(1, int(100 / level))
                            new_obj[k][prop] = val.copy()
                            new_obj[k][prop]["k"] = val["k"][::step]
                        else:
                            new_obj[k][prop] = val
                    continue
                if k in ["hd", "a", "bm", "mn", "ix", "cl", "ln", "tt"]:
                    if level >= 25:
                        continue
                new_obj[k] = clean(v, level)
            return new_obj
        elif isinstance(obj, list):
            return [clean(item, level) for item in obj]
        elif isinstance(obj, float):
            if level >= 75:
                return round(obj, 1)
            elif level >= 50:
                return round(obj, 2)
            else:
                return round(obj, 3)
        return obj

    cleaned = clean(data, level_percent)
    compact = json.dumps(cleaned, separators=(",", ":")).encode("utf-8")
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
            f"─────────────────────────\n"
            f"• 🏷️ Nama: `{name}`\n"
            f"• 🎞️ Layer: `{layers}`\n"
            f"• 🗂️ Asset: `{assets}`\n"
            f"• ⏱️ Durasi: `{duration:.2f}` detik\n"
            f"• 💾 Ukuran file: `{size_kb:.2f} KB`\n"
            f"─────────────────────────"
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
        "✨ *Selamat datang di Emoji Creator Bot!* ✨\n\n"
        "Ubah file JSON animasi menjadi *emoji Telegram* 🎉\n"
        "Klik tombol di bawah untuk memulai!",
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
keyboard = [
        [
            InlineKeyboardButton("🎨 Normal", callback_data="normal"),
            InlineKeyboardButton("⚡ Optimize", callback_data="optimize")
        ],
        [InlineKeyboardButton("❌ Batal", callback_data="reset")]
    ]
    await update.message.reply_text(
        preview,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        help_text = (
            "ℹ️ *Panduan Penggunaan*\n\n"
            "1. Kirim file `.json` animasi Lottie.\n"
            "2. Pilih metode konversi:\n"
            "   • Normal → konversi langsung\n"
            "   • Optimize → optimasi JSON\n"
            "3. Jika pilih Optimize, pilih level % optimasi.\n"
            "4. Terima hasil `.tgs` sebagai *emoji* Telegram."
        )
        keyboard = [[InlineKeyboardButton("🔙 Kembali ke Menu Utama", callback_data="main")]]
        await query.edit_message_text(help_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    elif query.data == "main":
        keyboard = [
            [InlineKeyboardButton("📄 Kirim JSON", callback_data="send_json")],
            [InlineKeyboardButton("ℹ️ Bantuan", callback_data="help")]
        ]
        await query.edit_message_text(
            "👋 Kembali ke Menu Utama. Klik tombol di bawah untuk mulai!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    elif query.data == "send_json":
    await query.edit_message_text(
        "✨ *Siap Mengubah JSON-mu Menjadi Emoji!* ✨\n\n"
        "📤 Kirim file JSON animasi Lottie di bawah ini. \n"
        "Bot akan memberikan preview dan pilihan mode convert.",
        parse_mode="Markdown"
    )
    return


    if query.data == "reset":
        context.user_data.clear()
        await query.edit_message_text("✅ Semua data direset. Kirim file baru untuk mulai lagi.")
        return

    if "json_bytes" not in context.user_data:
        await query.edit_message_text("❌ File JSON tidak ditemukan. Kirim ulang.")
        return

    for msg in context.user_data.get("last_messages", []):
        try:
            await msg.delete()
        except:
            continue
    context.user_data["last_messages"] = []

    json_bytes = context.user_data["json_bytes"]

    if query.data == "normal":
        tgs_file = json_to_tgs(json_bytes)
        size_kb = len(tgs_file.getvalue()) / 1024
        keyframes = count_keyframes(json_bytes)
        mode = "Normal"

        if size_kb > 64:
            info_msg = await query.message.reply_text(
                f"⚠️ Ukuran emoji terlalu besar ({size_kb:.2f} KB). "
                "Silakan pilih optimize atau potong animasi.",
                parse_mode="Markdown"
            )
            context.user_data["last_messages"] = [info_msg]
        else:
            emoji_msg = await query.message.reply_sticker(
                sticker=InputFile(tgs_file, filename="emoji.tgs")
            )
            context.user_data["last_messages"] = [emoji_msg]

        keyboard = [
            [
                InlineKeyboardButton("🎨 Normal", callback_data="normal"),
                InlineKeyboardButton("⚡ Optimize", callback_data="optimize")
            ],
            [InlineKeyboardButton("❌ Batal", callback_data="reset")]
        ]
        info_msg = await query.message.reply_text(
            f"✅ Mode: *{mode}*\n📦 Size: {size_kb:.2f} KB\n🔑 Keyframes: {keyframes}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data["last_messages"].append(info_msg)

    if query.data == "optimize":
        keyboard = [
            [
                InlineKeyboardButton("25%", callback_data="level_25"),
                InlineKeyboardButton("50%", callback_data="level_50")
            ],
            [
                InlineKeyboardButton("75%", callback_data="level_75"),
                InlineKeyboardButton("100%", callback_data="level_100")
            ],
            [InlineKeyboardButton("🔙 Kembali", callback_data="back_optimize")]
        ]
        await query.edit_message_text(
            "⚡ *Optimize JSON*\nPilih level optimasi:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if query.data == "back_optimize":
        keyboard = [
            [
                InlineKeyboardButton("🎨 Normal", callback_data="normal"),
                InlineKeyboardButton("⚡ Optimize", callback_data="optimize")
            ],
            [InlineKeyboardButton("❌ Batal", callback_data="reset")]
        ]
        await query.edit_message_text("Pilih metode konversi:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if query.data.startswith("level_"):
        level_percent = int(query.data.split("_")[1])
        tgs_file = optimize_json_level(json_bytes, level_percent)
        size_kb = len(tgs_file.getvalue()) / 1024
        keyframes = count_keyframes(json_bytes)
        mode = "Optimize"

        if size_kb > 64:
            info_msg = await query.message.reply_text(
                f"⚠️ Ukuran emoji terlalu besar ({size_kb:.2f} KB). "
                "Silakan pilih level optimize lebih tinggi atau potong animasi.",
                parse_mode="Markdown"
            )
            context.user_data["last_messages"].append(info_msg)
        else:
            emoji_msg = await query.message.reply_sticker(
                sticker=InputFile(tgs_file, filename="emoji.tgs")
            )
            context.user_data["last_messages"].append(emoji_msg)

        keyboard = [
            [
                InlineKeyboardButton("🎨 Normal", callback_data="normal"),
                InlineKeyboardButton("⚡ Optimize", callback_data="optimize")
            ],
            [InlineKeyboardButton("❌ Batal", callback_data="reset")]
        ]
        info_msg = await query.message.reply_text(
            f"✅ Mode: *{mode}*\n📦 Size: {size_kb:.2f} KB\n🔑 Keyframes: {keyframes}\n🎚️ Level: {level_percent}%",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data["last_messages"].append(info_msg)

# -------------------- MAIN --------------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()


