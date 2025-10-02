import os
import json
import gzip
from io import BytesIO
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

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
            return {k: clean(v) for k, v in obj.items() if v not in [0, 0.0, False, None, "", [], {}] and k not in ["ix", "a", "ddd", "bm", "mn", "hd", "cl", "ln", "tt"]}
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

def apply_effect(data, effect):
    for layer in data.get("layers", []):
        ks = layer.get("ks", {})
        if effect == "pop" and "s" in ks:
            ks["s"]["k"] = [{"t":0,"s":[100,100]}, {"t":10,"s":[120,120]}, {"t":20,"s":[100,100]}]
        elif effect == "flash" and "o" in ks:
            ks["o"]["k"] = [{"t":0,"s":100}, {"t":5,"s":0}, {"t":10,"s":100}]
        elif effect == "rainbow" and "c" in ks:
            ks["c"]["k"] = [{"t":0,"s":[1,0,0,1]}, {"t":10,"s":[0,1,0,1]}, {"t":20,"s":[0,0,1,1]}]
        elif effect == "shake" and "p" in ks:
            ks["p"]["k"] = [{"t":0,"s":[0,0]}, {"t":5,"s":[10,-10]}, {"t":10,"s":[-10,10]}, {"t":15,"s":[0,0]}]
    return data

def generate_emoji_with_effect(json_bytes: bytes, effect: str) -> BytesIO:
    data = json.loads(json_bytes.decode("utf-8"))
    data = apply_effect(data, effect)
    compact = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return gzip_bytes(compact)

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
        [InlineKeyboardButton("✨ Emoji Generator", callback_data="menu_emoji_gen")],
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

    elif mode_selected == "emoji_gen":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎨 Pop", callback_data="effect_pop")],
            [InlineKeyboardButton("💫 Flash", callback_data="effect_flash")],
            [InlineKeyboardButton("🌈 Rainbow", callback_data="effect_rainbow")],
            [InlineKeyboardButton("🌀 Shake", callback_data="effect_shake")],
            [InlineKeyboardButton("❌ Batal", callback_data="menu_reset")]
        ])
        await update.message.reply_text("✅ File diterima!\nPilih efek emoji:", reply_markup=keyboard)

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
                    del context.user_data["json_bytes"]

    except Exception as e:
        await query.message.reply_text(f"❌ Gagal convert: {str(e)}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
