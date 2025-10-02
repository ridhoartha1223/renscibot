import os
import json
import gzip
from io import BytesIO
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import random

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

def compress_json_level(json_bytes: bytes, level_percent: int) -> BytesIO:
    """
    Menghapus sebagian data JSON sesuai persentase level.
    level_percent: 25, 50, 75, 100
    """
    data = json.loads(json_bytes.decode("utf-8"))

    def clean(obj):
        if isinstance(obj, dict):
            new_obj = {}
            for k, v in obj.items():
                # Hapus sebagian key dengan probabilitas sesuai level
                if random.randint(1, 100) > level_percent:
                    new_obj[k] = clean(v)
            return new_obj
        elif isinstance(obj, list):
            new_list = []
            for item in obj:
                if random.randint(1, 100) > level_percent:
                    new_list.append(clean(item))
            return new_list
        elif isinstance(obj, float):
            return round(obj, 3)
        return obj

    cleaned = clean(data)
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
            f"──────────────────\n"
            f"• 🏷️ Nama: `{name}`\n"
            f"• 🎞️ Layer: `{layers}`\n"
            f"• 🗂️ Asset: `{assets}`\n"
            f"• ⏱️ Durasi: `{duration:.2f}` detik\n"
            f"• 💾 Ukuran file: `{size_kb:.2f} KB`\n"
            f"──────────────────"
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

    # Inline keyboard untuk level compression
    keyboard = [
        [
            InlineKeyboardButton("25% Compression", callback_data="level_25"),
            InlineKeyboardButton("50% Compression", callback_data="level_50")
        ],
        [
            InlineKeyboardButton("75% Compression", callback_data="level_75"),
            InlineKeyboardButton("100% Compression", callback_data="level_100")
        ],
        [InlineKeyboardButton("❌ Batal", callback_data="reset")]
    ]

    await update.message.reply_text(
        "✅ *File JSON berhasil diterima!* 🎉\n\n" + preview,
        parse_mode="Markdown"
    )
    await update.message.reply_text(
        "Pilih *Level Compression* untuk mengecilkan file sebelum dikonversi ke TGS:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # ------------------- Bantuan & Navigasi -------------------
    if query.data == "help":
        help_text = (
            "ℹ️ *Panduan Penggunaan*\n\n"
            "1. Kirim file `.json` animasi Lottie.\n"
            "2. Pilih level compression untuk mengecilkan file (25%,50%,75%,100%).\n"
            "3. Terima hasil `.tgs` siap pakai sebagai stiker Telegram."
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
            "📤 *Silakan kirim file `.json` animasi Lottie untuk dikonversi!*",
            parse_mode="Markdown"
        )
        return

    # ------------------- Reset -------------------
    if query.data == "reset":
        context.user_data.clear()
        await query.edit_message_text("✅ Semua data direset. Kirim file baru untuk mulai lagi.")
        return

    # ------------------- Level Compression -------------------
    if "json_bytes" not in context.user_data:
        await query.edit_message_text("❌ File JSON tidak ditemukan. Kirim ulang.")
        return

    json_bytes = context.user_data["json_bytes"]

    try:
        # Hapus preview hasil convert sebelumnya (jika ada)
        for msg in context.user_data.get("last_messages", []):
            try:
                await msg.delete()
            except:
                continue
        context.user_data["last_messages"] = []

        loading_msg = await query.message.reply_text("⏳ Sedang memproses JSON...")
        context.user_data["last_messages"].append(loading_msg)

        # Tentukan level compression
        if query.data.startswith("level_"):
            level_percent = int(query.data.split("_")[1])
        else:
            level_percent = 0

        tgs_file = compress_json_level(json_bytes, level_percent)

        await loading_msg.delete()

        size_kb = len(tgs_file.getvalue()) / 1024
        keyframes = count_keyframes(json_bytes)

        # Kirim sticker
        sticker_msg = await query.message.reply_sticker(sticker=InputFile(tgs_file, filename="emoji.tgs"))
        context.user_data["last_messages"].append(sticker_msg)

        # Inline keyboard tetap muncul agar user bisa pilih level lain
        keyboard = [
            [
                InlineKeyboardButton("25% Compression", callback_data="level_25"),
                InlineKeyboardButton("50% Compression", callback_data="level_50")
            ],
            [
                InlineKeyboardButton("75% Compression", callback_data="level_75"),
                InlineKeyboardButton("100% Compression", callback_data="level_100")
            ],
            [InlineKeyboardButton("❌ Batal", callback_data="reset")]
        ]

        info_msg = await query.message.reply_text(
            f"✅ File TGS berhasil dibuat!\n"
            f"📦 Size: {size_kb:.2f} KB\n"
            f"🔑 Keyframes: {keyframes}\n"
            f"🎚️ Compression Level: {level_percent}%",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data["last_messages"].append(info_msg)

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
