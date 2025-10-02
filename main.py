import os
import json
import gzip
from io import BytesIO
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# --------- Utilities ----------
def gzip_bytes(data_bytes: bytes) -> BytesIO:
    buf = BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="w", compresslevel=9) as f:
        f.write(data_bytes)
    buf.seek(0)
    buf.name = "emoji.tgs"   # wajib: supaya Telegram anggap animasi
    return buf

def size_kb(buf: BytesIO) -> float:
    return round(len(buf.getvalue()) / 1024, 2)

# --------- Converters ----------
def convert_json_to_tgs(json_bytes: bytes) -> BytesIO:
    data = json.loads(json_bytes.decode("utf-8"))
    compact = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return gzip_bytes(compact)

def optimize_json_to_tgs(json_bytes: bytes) -> BytesIO:
    data = json.loads(json_bytes.decode("utf-8"))

    # --- FIELD WAJIB HARUS ADA ---
    required = ["v", "fr", "ip", "op", "w", "h", "layers"]
    for r in required:
        if r not in data:
            raise ValueError(f"Field wajib hilang: {r}")

    # meta WAJIB ada
    if "meta" not in data:
        data["meta"] = {"g": "AE", "a": "", "k": "", "d": "", "tc": ""}

    # fps max 20
    try:
        if float(data.get("fr", 30)) > 20:
            data["fr"] = 20
    except:
        pass

    # hanya hapus property tidak penting di dalam layers
    def cleanup(obj):
        if isinstance(obj, dict):
            for k in ["nm", "mn", "cl", "bm", "hd"]:
                obj.pop(k, None)
            for v in obj.values():
                cleanup(v)
        elif isinstance(obj, list):
            for item in obj:
                cleanup(item)

    cleanup(data["layers"])

    # round angka biar kecil
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

def simplify_keyframes(json_bytes: bytes, step: int = 2) -> BytesIO:
    data = json.loads(json_bytes.decode("utf-8"))

    def traverse_and_reduce(obj):
        if isinstance(obj, dict):
            for k, v in list(obj.items()):
                if k == "k" and isinstance(v, list):
                    obj[k] = v[::step]  # kurangi keyframes
                else:
                    traverse_and_reduce(v)
        elif isinstance(obj, list):
            for item in obj:
                traverse_and_reduce(item)

    if "layers" in data:
        for layer in data["layers"]:
            traverse_and_reduce(layer)

    compact = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return gzip_bytes(compact)

def reduce_duration(json_bytes: bytes, factor: float = 0.5) -> BytesIO:
    data = json.loads(json_bytes.decode("utf-8"))
    ip = data.get("ip", 0)
    op = data.get("op", None)
    if op is None:
        compact = json.dumps(data, separators=(",", ":")).encode("utf-8")
        return gzip_bytes(compact)

    duration = max(1, op - ip)
    new_duration = max(1, int(duration * factor))
    new_op = ip + new_duration
    data["op"] = new_op

    def prune_by_time(obj):
        if isinstance(obj, dict):
            for k, v in list(obj.items()):
                if k == "k" and isinstance(v, list):
                    obj[k] = [e for e in v if not (isinstance(e, dict) and "t" in e and e["t"] >= new_op)]
                else:
                    prune_by_time(v)
        elif isinstance(obj, list):
            for it in obj:
                prune_by_time(it)

    if "layers" in data:
        for layer in data["layers"]:
            prune_by_time(layer)

    compact = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return gzip_bytes(compact)

# --------- Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Kirim file .json (Bodymovin), lalu pilih mode konversi ke .tgs (emoji).")

async def handle_json(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith(".json"):
        await update.message.reply_text("❌ Harap kirim file .json dari Bodymovin (AE).")
        return

    file = await doc.get_file()
    json_bytes = await file.download_as_bytearray()
    context.user_data["json_bytes"] = bytes(json_bytes)

    keyboard = [
        [InlineKeyboardButton("🔄 Normal", callback_data="normal")],
        [InlineKeyboardButton("⚡ Optimized", callback_data="optimize")],
    ]
    await update.message.reply_text("Pilih mode konversi:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = context.user_data.get("json_bytes")
    if not data:
        await query.edit_message_text("❌ File JSON tidak ditemukan. Silakan kirim ulang.")
        return

    try:
        if query.data == "normal":
            tgs_buf = convert_json_to_tgs(data)
            mode = "Normal"
        elif query.data == "optimize":
            tgs_buf = optimize_json_to_tgs(data)
            mode = "Optimized"
        elif query.data == "reduce_keyframes":
            tgs_buf = simplify_keyframes(data, step=2)
            mode = "Reduced Keyframes"
        elif query.data == "reduce_duration":
            tgs_buf = reduce_duration(data, factor=0.5)
            mode = "Reduced Duration"
        else:
            return

        kb = size_kb(tgs_buf)

        # kirim sebagai sticker
        await query.message.reply_sticker(sticker=InputFile(tgs_buf, filename=tgs_buf.name))

        if len(tgs_buf.getvalue()) <= 64 * 1024:
            msg = f"✅🟢 {mode}\n📦 Ukuran: {kb} KB\nSiap dipakai sebagai Emoji Premium 🚀"
            await query.message.reply_text(msg, parse_mode="Markdown")
        else:
            msg = (
                f"❌🔴 {mode}\n📦 Ukuran: {kb} KB\n"
                "⚠️ Melebihi batas 64 KB.\nPilih opsi optimasi:"
            )
            keyboard = [
                [InlineKeyboardButton("✂️ Kurangi Keyframes", callback_data="reduce_keyframes")],
                [InlineKeyboardButton("⏱ Kurangi Durasi 50%", callback_data="reduce_duration")],
                [InlineKeyboardButton("🔁 Optimized", callback_data="optimize")],
            ]
            await query.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    except Exception as e:
        await query.message.reply_text(f"❌ Error: {e}")

# --------- Main ----------
def main():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN belum diset di Railway.")
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.FileExtension("json"), handle_json))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
