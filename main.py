import os
import json
import lottie
from lottie.exporters import exporters
from pyrogram import Client, filters
from pyrogram.raw import functions

# ENV Vars
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Bot
bot = Client("emoji_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Database sementara (dict)
user_packs = {}

# Start Command
@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text(
        "👋 Halo!\n\n"
        "Aku bisa convert file .json ke .tgs lalu otomatis bikin EmojiPack.\n\n"
        "📌 Command:\n"
        "`/newpack <nama>` - bikin pack baru\n"
        "`/add` - tambah emoji ke pack\n"
        "atau cukup kirim .json, aku auto convert & masukkan ke pack ✨"
    )

# Buat pack baru
@bot.on_message(filters.command("newpack"))
async def newpack_cmd(client, message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply_text("⚠️ Gunakan: `/newpack nama_pack`")

    pack_name = args[1]
    user_id = message.from_user.id
    username = message.from_user.username or f"user{user_id}"

    short_name = f"rensci_{username}_by_{client.me.username}"
    user_packs[user_id] = short_name

    try:
        await client.invoke(
            functions.stickers.CreateStickerSet(
                user_id=user_id,
                title=pack_name,
                short_name=short_name,
                stickers=[]
            )
        )
        await message.reply_text(f"✅ Pack baru dibuat: [klik disini](https://t.me/addemoji/{short_name})", disable_web_page_preview=True)
    except Exception as e:
        await message.reply_text(f"❌ Gagal bikin pack: {e}")

# Handler kirim JSON
@bot.on_message(filters.document)
async def handle_json(client, message):
    if not message.document.file_name.endswith(".json"):
        return

    user_id = message.from_user.id
    if user_id not in user_packs:
        return await message.reply_text("⚠️ Kamu belum punya pack! Bikin dulu dengan /newpack namanya.")

    # Download JSON
    json_path = await message.download(file_name="input.json")
    tgs_path = "output.tgs"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        animation = lottie.parsers.tgs.parse_tgs(data)
        with open(tgs_path, "wb") as tgs_file:
            exporters.tgs.export_tgs(animation, tgs_file)

        # Upload ke emoji pack
        short_name = user_packs[user_id]
        emoji_char = "😎"  # default emoji

        with open(tgs_path, "rb") as sticker_file:
            await client.invoke(
                functions.stickers.AddStickerToSet(
                    stickerset=await client.invoke(
                        functions.stickers.CheckShortName(short_name=short_name)
                    ),
                    sticker=functions.inputStickerSetItem.InputStickerSetItem(
                        document=await client.save_file(sticker_file),
                        emoji=emoji_char
                    )
                )
            )

        await message.reply_text(f"✅ Ditambah ke pack: [klik disini](https://t.me/addemoji/{short_name})", disable_web_page_preview=True)

    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

    finally:
        if os.path.exists(json_path):
            os.remove(json_path)
        if os.path.exists(tgs_path):
            os.remove(tgs_path)

print("🚀 Bot jalan...")
bot.run()
