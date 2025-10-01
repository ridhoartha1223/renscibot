import os
import subprocess
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client(":memory:", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_state = {}  # simpan state sementara user


# Helper: Convert JSON -> TGS via lottie2tgs CLI
def convert_json_to_tgs_cli(input_path, output_path, optimize=False):
    cmd = ["lottie2tgs", input_path, output_path]
    if optimize:
        cmd.append("--minify")
    # jalankan subprocess
    subprocess.run(cmd, check=True)


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
    user_state[query.from_user.id] = action

    if action == "json2tgs":
        await query.message.reply("Silakan kirim file .json yang ingin di-convert ke `.tgs`")
    elif action == "json2tgs_opt":
        await query.message.reply("Silakan kirim file .json yang ingin di-convert ke .tgs (optimized)")


# Handler document
@app.on_message(filters.document)
async def document_handler(client, message: Message):
    action = user_state.get(message.from_user.id)
    if not action:
        return

    file_path = await message.download()
    output = file_path.replace(".json", "_converted.tgs")

    try:
        optimize = True if action == "json2tgs_opt" else False
        convert_json_to_tgs_cli(file_path, output, optimize=optimize)

        size = os.path.getsize(output)
        if size > 64 * 1024:
            await message.reply("⚠️ Hasil file lebih dari 64KB! Tidak bisa dijadikan emoji.")
        else:
            await message.reply_document(output, caption="✅ Berhasil convert!")

    except subprocess.CalledProcessError as e:
        await message.reply(f"❌ Error convert: {e}")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(output):
            os.remove(output)
        user_state.pop(message.from_user.id, None)


# Debug ping
@app.on_message(filters.private & filters.command("ping"))
async def debug_ping(client, message):
    await message.reply("✅ Bot connected and working!")


if __name__ == "__main__":
    print("🚀 Bot starting...")
    app.start()
    print("🚀 Bot running...")
    idle()
    app.stop()
