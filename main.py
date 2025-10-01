import os
import asyncio
import json
from pyrogram import Client, filters
from pyrogram.types import Message
import lottie
from lottie.exporters import exporters
from lottie.parsers.tgs import parse_tgs
import time
time.time = lambda: int(time.time())

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("emoji-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# Helper: JSON to TGS
async def convert_json_to_tgs(input_path, output_path, optimize=False):
    with open(input_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    # load animation
    animation = lottie.parsers.tgs.parse_tgs(json_data)

    if optimize:
        # misal minimal optimize: hapus metadata, compress
        exporters.export_tgs(animation, output_path, minify=True)
    else:
        exporters.export_tgs(animation, output_path)


# Command: /json2tgs
@app.on_message(filters.command("json2tgs") & filters.private)
async def json2tgs_handler(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("❌ Reply ke file .json untuk convert ke `.tgs`")

    file = await message.reply_to_message.download()
    output = file.replace(".json", ".tgs")

    try:
        await convert_json_to_tgs(file, output, optimize=False)
        size = os.path.getsize(output)

        if size > 64 * 1024:
            await message.reply("⚠️ Hasil file lebih dari 64KB! Tidak bisa dijadikan emoji.")
        else:
            await message.reply_document(output, caption="✅ Berhasil convert!\nMau impor ke emoji premium? Gunakan /import_tgs")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")
    finally:
        os.remove(file)
        if os.path.exists(output):
            os.remove(output)


# Command: /json2tgs_optimilize
@app.on_message(filters.command("json2tgs_optimilize") & filters.private)
async def json2tgs_opt_handler(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("❌ Reply ke file .json untuk convert ke .tgs (optimize)")

    file = await message.reply_to_message.download()
    output = file.replace(".json", "_opt.tgs")

    try:
        await convert_json_to_tgs(file, output, optimize=True)
        size = os.path.getsize(output)

        if size > 64 * 1024:
            await message.reply("⚠️ Hasil file lebih dari 64KB! Tidak bisa dijadikan emoji.")
        else:
            await message.reply_document(output, caption="✅ Berhasil convert (optimized)!\nMau impor ke emoji premium? Gunakan /import_tgs")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")
    finally:
        os.remove(file)
        if os.path.exists(output):
            os.remove(output)


# Command: /import_tgs
@app.on_message(filters.command("import_tgs") & filters.private)
async def import_tgs_handler(client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("❌ Reply ke file .tgs untuk impor ke emoji premium")

    file = await message.reply_to_message.download()
    size = os.path.getsize(file)

    if size > 64 * 1024:
        await message.reply("⚠️ File lebih dari 64KB! Tidak bisa dijadikan emoji.")
        os.remove(file)
        return

    # Tanya detail pack
    await message.reply(
        "📝 Masukkan nama pack emoji premium yang diinginkan.\n\nFormat:\n`nama_pack | emoji_replacement | custom_link`\n\nContoh:\n`RensiPack | 😎 | rensipackemoji`"
    )

    # Tunggu response
    response: Message = await client.listen(message.chat.id)

    try:
        nama_pack, emoji_replacement, custom_link = map(str.strip, response.text.split("|"))

        # Simulasi import (aslinya pakai stickers.createNewStickerSet via MTProto raw)
        await message.reply(
            f"✅ Emoji siap diimpor!\n\nNama Pack: {nama_pack}\nEmoji: {emoji_replacement}\nCustom Link: https://t.me/addemoji/{custom_link}"
        )
    except Exception as e:
        await message.reply(f"❌ Format salah. Error: {e}")

    os.remove(file)


if __name__ == "__main__":
    app.run()



