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
def gzip_bytes(data_bytes: bytes, filename: str = "emoji.tgs") -> BytesIO:
    buf = BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="w", compresslevel=9) as f:
        f.write(data_bytes)
    buf.seek(0)
    buf.name = filename
    return buf

def size_kb(buf: BytesIO) -> float:
    return round(len(buf.getvalue()) / 1024, 2)


# --------- Converters / Optimizers ----------
def convert_json_to_tgs(json_bytes: bytes) -> BytesIO:
    """Bungkus JSON Bodymovin jadi TGS (gzip)"""
    # validate and compact
    data = json.loads(json_bytes.decode("utf-8"))
    compact = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return gzip_bytes(compact, filename="emoji.tgs")


def optimize_json_to_tgs(json_bytes: bytes) -> BytesIO:
    """Optimasi ringan: hapus meta, turunkan framerate >30 => 30, compact, gzip"""
    data = json.loads(json_bytes.decode("utf-8"))

    # turunkan framerate
    if "fr" in data:
        try:
            fr = float(data["fr"])
            if fr > 30:
                data["fr"] = 30
        except Exception:
            pass

    # hapus meta bila ada
    if "meta" in data:
        data.pop("meta", None)

    # compact
    compact = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return gzip_bytes(compact, filename="emoji_optimized.tgs")


def simplify_keyframes(json_bytes: bytes, step: int = 2) -> BytesIO:
    """Sample keyframes: ambil 1 dari tiap 'step' entries pada array keyframes"""
    data = json.loads(json_bytes.decode("utf-8"))

    def traverse_and_reduce(obj):
        if isinstance(obj, dict):
            for k, v in list(obj.items()):
                if k == "k" and isinstance(v, list):
                    # reduce list length by sampling
                    obj[k] = v[::step]
                else:
                    traverse_and_reduce(v)
        elif isinstance(obj, list):
            for item in obj:
                traverse_and_reduce(item)

    if "layers" in data and isinstance(data["layers"], list):
        for layer in data["layers"]:
            traverse_and_reduce(layer)

    compact = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return gzip_bytes(compact, filename="emoji_reduced_kf.tgs")


def reduce_duration(json_bytes: bytes, factor: float = 0.5) -> BytesIO:
    """
    Pangkas durasi animasi (misal 50%): ubah data['op'] jadi lebih kecil
    dan buang keyframes yang t >= new_op bila keyframe punya 't'.
    (Sederhana — bisa memotong data yang mengandung time-based keyframes)
    """
    data = json.loads(json_bytes.decode("utf-8"))
    ip = data.get("ip", 0)
    op = data.get("op", None)
    if op is None:
        # kalau tidak ada op/ip, fallback pake keyframe prune (tidak berubah durasi)
        compact = json.dumps(data, separators=(",", ":")).encode("utf-8")
        return gzip_bytes(compact, filename="emoji_reduced_dur.tgs")

    duration = max(1, op - ip)
    new_duration = max(1, int(duration * factor))
    new_op = ip + new_duration
    data["op"] = new_op

    def prune_by_time(obj):
        if isinstance(obj, dict):
            for k, v in list(obj.items()):
                if k == "k" and isinstance(v, list):
                    newlist = []
                    for entry in v:
                        if isinstance(entry, dict) and "t" in entry:
                            try:
                                if entry["t"] < new_op:
                                    newlist.append(entry)
                            except Exception:
                                newlist.append(entry)
                        else:
                            newlist.append(entry)
                    obj[k] = newlist
                else:
                    prune_by_time(v)
        elif isinstance(obj, list):
            for it in obj:
                prune_by_time(it)

    if "layers" in data and isinstance(data["layers"], list):
        for layer in data["layers"]:
            prune_by_time(layer)

    compact = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return gzip_bytes(compact, filename="emoji_reduced_dur.tgs")


# --------- Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Kirim file .json (Bodymovin), lalu pilih mode untuk convert ke .tgs (emoji).")


async def handle_json(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith(".json"):
        await update.message.reply_text("❌ Harap kirim file .json dari Bodymovin (AE).")
        return

    file = await doc.get_file()
    json_bytes = await file.download_as_bytearray()
    context.user_data["json_bytes"] = bytes(json_bytes)  # simpan original untuk re-optimasi

    keyboard = [
        [InlineKeyboardButton("🔄 JSON → TGS (Normal)", callback_data="normal")],
        [InlineKeyboardButton("⚡ JSON → TGS (Optimized)", callback_data="optimize")],
    ]
    await update.message.reply_text("Pilih mode konversi:", reply_markup=InlineKeyboardMarkup(keyboard))


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = context.user_data.get("json_bytes")
    if not data:
        await query.edit_message_text("❌ File JSON tidak ditemukan. Silakan kirim ulang.")
        return

    action = query.data

    try:
        if action == "normal":
            tgs_buf = convert_json_to_tgs(data)
            mode = "Normal"
        elif action == "optimize":
            tgs_buf = optimize_json_to_tgs(data)
            mode = "Optimized"
        elif action == "reduce_keyframes":
            tgs_buf = simplify_keyframes(data, step=2)
            mode = "Reduced Keyframes"
        elif action == "reduce_duration":
            tgs_buf = reduce_duration(data, factor=0.5)
            mode = "Reduced Duration (50%)"
        else:
            # unknown action
            return

        kb = size_kb(tgs_buf)

        # Kirim hanya SEKALI sebagai animasi (sticker)
        await query.message.reply_sticker(sticker=InputFile(tgs_buf, filename=tgs_buf.name))

        # Persiapkan pesan info dengan indikator warna (emoji)
        if len(tgs_buf.getvalue()) <= 64 * 1024:
            info = f"✅🟢 Konversi selesai ({mode})\n📦 Ukuran file: {kb} KB\n\nSiap diunggah sebagai *Emoji Premium* 🚀"
            await query.message.reply_text(info, parse_mode="Markdown")
        else:
            info = (
                f"❌🔴 Konversi selesai ({mode})\n📦 Ukuran file: {kb} KB\n\n"
                "⚠️ Ukuran melebihi batas *64 KB* untuk Emoji Premium.\n"
                "Pilih salah satu opsi optimasi di bawah untuk mencoba memperkecil file:"
            )
            keyboard = [
                [InlineKeyboardButton("✂️ Kurangi Keyframes (Sampling)", callback_data="reduce_keyframes")],
                [InlineKeyboardButton("⏱ Kurangi Durasi 50%", callback_data="reduce_duration")],
                [InlineKeyboardButton("🔁 Coba Optimized", callback_data="optimize")],
            ]
            await query.message.reply_text(info, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    except json.JSONDecodeError:
        await query.message.reply_text("❌ Gagal: file JSON tidak valid.")
    except Exception as e:
        await query.message.reply_text(f"❌ Gagal convert: {e}")


# --------- Main ----------
def main():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable belum diset.")
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.FileExtension("json"), handle_json))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 Bot running (polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
