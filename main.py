import os
import json
import requests
import lottie
from lottie.exporters import exporters
from pyrogram import Client, filters
import ntplib, time

# =======================
# Sinkronisasi waktu dulu
# =======================
try:
    print("⏳ Sinkronisasi waktu dengan NTP...")
    c = ntplib.NTPClient()
    response = c.request('pool.ntp.org')
    ts = response.tx_time
    time_tuple = time.localtime(ts)
    print("✅ Waktu sinkron:", time.strftime('%Y-%m-%d %H:%M:%S', time_tuple))
except Exception as e:
    print("⚠️ Gagal sinkronisasi waktu:", e)

# =======================
# Konfigurasi
# =======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
REMOVE_BG_API = os.getenv("REMOVE_BG_API")

app = Client("emoji_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================
# Auto convert JSON ke TGS
# ================
@app.on_message(filters.document)
async def handle_json(client, message):
    if not message.document.file_name.endswith(".json"):
        return
    
    json_path = await message.download(file_name="input.json")
    tgs_path = "output.tgs"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Parse & export ke TGS
        animation = lottie.parsers.tgs.parse_tgs(data)
        with open(tgs_path, "wb") as tgs_file:
            exporters.tgs.export_tgs(animation, tgs_file)

        size_kb = os.path.getsize(tgs_path) / 1024
        caption = f"✅ Convert JSON → TGS selesai! (size: {size_kb:.1f} KB)"
        if size_kb > 64:
            caption += "\n⚠️ Warning: File > 64KB, tidak bisa dijadikan emoji premium."

        await message.reply_document(tgs_path, caption=caption)

    except Exception as e:
        await message.reply_text(f"❌ Gagal convert: {e}")

    finally:
        if os.path.exists(json_path):
            os.remove(json_path)
        if os.path.exists(tgs_path):
            os.remove(tgs_path)

print("🚀 Bot jalan...")
app.run()
