import os
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client(":memory:", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_state = {}  # simpan state sementara user

# /start → menu interaktif
@app.on_message(filters.command("start"))
async def start(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Upload .TGS", callback_data="upload_tgs")]
    ])
    await message.reply(
        "Selamat datang! Pilih fitur:", reply_markup=keyboard
    )

# Callback query → set user state
@app.on_callback_query()
async def callback_handler(client, query):
    action = query.data
    user_state[query.from_user.id] = action

    if action == "upload_tgs":
        await query.message.reply("Silakan kirim file .tgs yang ingin dicek/upload.")

# Handler document
@app.on_message(filters.document)
async def document_handler(client, message: Message):
    action = user_state.get(message.from_user.id)
    if not action:
        return

    if not message.document.file_name.endswith(".tgs"):
        await message.reply("❌ File bukan .tgs. Silakan kirim file yang benar.")
        return

    file_path = await message.download()
    try:
        size = os.path.getsize(file_path)
        if size > 64 * 1024:
            await message.reply("⚠️ File lebih dari 64KB! Tidak bisa dijadikan emoji.")
        else:
            await message.reply_document(file_path, caption="✅ File .tgs berhasil diterima!")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
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
