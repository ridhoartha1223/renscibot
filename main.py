import os
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import lottie
from lottie.exporters.tgs import export_tgs

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client(":memory:", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Simpan state user sementara
user_state = {}  # {user_id: action}


# Helper: JSON to TGS
def convert_json_to_tgs(input_path, output_path, optimize=False):
    animation = lottie.parsers.tgs.parse_tgs(input_path)  # pakai file path langsung
    export_tgs(animation, output_path, minify=optimize)   # versi terbaru


# /start → menu interaktif
@app.on_message(filters.command("start"))
async def start(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("JSON → TGS", callback_data="json2tgs")],
        [InlineKeyboardButton("JSON → TGS (Optimize)", callback_data="json2tgs_opt")]
    ])
    await message.reply("Selamat datang! Pilih fitur:", reply_markup=keyboard)


# Callback query → set user state
@app.on_callback_query()
async def callback_handler(client, query):
    action = query.data
    user_state[query.from_user.id] = action  # simpan state

    if action == "json2tgs":
        await query.message.reply("Silakan kirim file .json yang ingin di-convert ke `.tgs`")
    elif action == "json2tgs_opt":
        await query.message.reply("Silakan kirim file .json yang ingin di-convert ke .tgs (optimized)")


# Handler document → cek state user
@app.on_message(filters.document)
async def document_handler(client, message: Message):
    action = user_state.get(message.from_user.id)
    if not action:
        return  # user belum pilih fitur

    file_path = await message.download()
    output = None

    try:
        if action == "json2tgs":
            output = file_path.replace(".json", ".tgs")
            convert_json_to_tgs(file_path, output, optimize=False)
        elif action == "json2tgs_opt":
            output = file_path.replace(".json", "_opt.tgs")
            convert_json_to_tgs(file_path, output, optimize=True)

        # Cek ukuran
        size = os.path.getsize(output)
        if size > 64 * 1024:
            await message.reply("⚠️ Hasil file lebih dari 64KB! Tidak bisa dijadikan emoji.")
        else:
            await message.reply_document(output, caption="✅ Berhasil convert!")

    except Exception as e:
        await message.reply(f"❌ Error: {e}")

    finally:
        # Hapus file sementara
        if os.path.exists(file_path):
            os.remove(file_path)
        if output and os.path.exists(output):
            os.remove(output)

        # Reset state user
        user_state.pop(message.from_user.id, None)


# Debug ping
@app.on_message(filters.private & filters.command("ping"))
async def debug_ping(client, message):
    await message.reply("✅ Bot connected and working!")


if name == "__main__":
    print("🚀 Bot is starting...")
    app.start()
    print("🚀 Bot is running...")
    idle()  # tunggu update Telegram
    app.stop()
