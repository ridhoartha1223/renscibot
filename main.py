import os
import asyncio
import json
from telethon import TelegramClient, events
# Asumsi:
# 1. lottie_convert.py memiliki fungsi convert_json_to_tgs(json_path) dan
#    optimize_tgs(tgs_path) untuk minify.
from lottie_convert import convert_json_to_tgs, optimize_tgs
from removebg import RemoveBg
from telethon.tl.types import DocumentAttributeFilename # Penting untuk ekstensi file

# --- Variabel Lingkungan (Environment Variables) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
REMOVE_BG_KEY = os.getenv("REMOVE_BG_KEY")

# --- Inisialisasi Klien ---
client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- State Management (untuk menyimpan file yang sedang diproses) ---
# Format: {user_id: file_path}
processing_tgs = {}

# Folder downloads
DOWNLOADS_DIR = "downloads"
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

# --- Command /start ---
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    welcome_message = (
        "**Selamat Datang di Bot Emoji Animasi (.tgs) Penuh Fitur! 🤖**\n\n"
        "Saya dirancang untuk membantu Anda membuat, mengoptimalkan, dan membagikan "
        "paket Emoji Animasi (.tgs) Anda.\n\n"
        "**Daftar Command & Fitur:**\n"
        "1. Kirim file .tgs: Bot akan otomatis mengoptimalkan ukurannya, "
        "meminta nama paket, dan membuat *share link* t.me/addemoji/....\n"
        "2. `/json2tgs`: Balas ke file .json untuk di-convert menjadi .tgs.\n"
        "3. `/removebg`: Balas ke file gambar (.png/.jpg) untuk menghapus *background*.\n\n"
        "**Tips:** Untuk fitur 2 & 3, Anda juga bisa mengirimkan file dengan *caption* "
        "berisi perintah /json2tgs atau /removebg."
    )
    await event.reply(welcome_message)

# --- Feature 2: Otomatis Menerima & Mengoptimalkan .tgs ---
@client.on(events.NewMessage(func=lambda e: e.media and e.file and e.file.ext == '.tgs'))
async def handle_tgs_file(event):
    user_id = event.sender_id
    await event.reply("✅ File .tgs diterima. Sedang mengunduh dan mengoptimalkan...")
    
    try:
        # 1. Unduh File
        file_name = f"{user_id}_{event.file.name or 'temp'}"
        temp_path = os.path.join(DOWNLOADS_DIR, file_name)
        downloaded_path = await event.download_media(temp_path)
        
        # 2. Optimasi (Minify)
        await event.reply("⏳ Mengoptimalkan ukuran file...")
        optimized_path = optimize_tgs(downloaded_path) # Asumsi: fungsi ini me-minify dan mengembalikan path baru/sama
        
        # 3. Simpan state dan Minta Nama Pack
        processing_tgs[user_id] = optimized_path
        
        await client.send_message(
            user_id,
            "🎉 Optimasi selesai! File siap dijadikan emoji pack.\n"
            "Sekarang, kirimkan nama unik untuk paket emoji Anda (contoh: `MyCoolPack`)\n"
            "*(Hanya huruf dan angka, tanpa spasi atau karakter khusus)*"
        )
        
    except Exception as e:
        await event.reply(f"❌ Gagal memproses file .tgs: {str(e)}")
        if user_id in processing_tgs:
            del processing_tgs[user_id]
        # Hapus file sementara
        if os.path.exists(downloaded_path):
            os.remove(downloaded_path)

# --- Menanggapi Nama Pack yang Dikirim Setelah Optimasi ---
@client.on(events.NewMessage(func=lambda e: e.sender_id in processing_tgs and not e.file and not e.text.startswith('/')))
async def get_pack_name(event):
    user_id = event.sender_id
    pack_name = event.text.strip()
    original_file_path = processing_tgs.pop(user_id)
    
    # Validasi nama pack (sederhana)
    if not pack_name.isalnum():
        await event.reply(
            "⚠️ Nama paket tidak valid. Gunakan hanya huruf dan angka (contoh: `KucingImutPack`). "
            "Silakan kirim ulang file .tgs dan ulangi prosesnya."
        )
        os.remove(original_file_path)
        return

    # 4. Generate Link & Kirim Hasil
    emoji_pack_link = f"t.me/addemoji/{pack_name}"
    f"Nama Paket Anda: `{pack_name}`\n"
        f"Link Emoji Pack: {emoji_pack_link}\n\n"
        f"File .tgs yang dioptimalkan dikirim di bawah ini. Gunakan file ini saat "
        f"mengklik link di atas untuk menambahkannya ke Telegram."
    )
    
    # Kirim file .tgs yang sudah dioptimalkan
    await client.send_file(user_id, original_file_path, caption=response_message)
    
    # Bersihkan
    os.remove(original_file_path)


# --- Feature 3: Konversi .json ke .tgs ---
@client.on(events.NewMessage(pattern=r"(?i)/json2tgs", outgoing=False))
async def json2tgs_cmd(event):
    # Cek apakah ada file dalam pesan itu sendiri atau di pesan yang dibalas
    if event.is_reply:
        target_message = await event.get_reply_message()
    else:
        target_message = event

    if target_message.file and target_message.file.ext == '.json':
        await event.reply("⏳ File .json diterima. Sedang di-convert ke .tgs...")
        
        # 1. Unduh File
        json_path = await target_message.download_media(file=os.path.join(DOWNLOADS_DIR, f"{event.sender_id}.json"))
        
        try:
            # 2. Convert & Optimasi
            # Asumsi convert_json_to_tgs juga otomatis me-minify
            tgs_path = convert_json_to_tgs(json_path) 
            
            # 3. Kirim Balik
            await event.reply(file=tgs_path, caption="✅ Konversi & Optimasi Selesai!")
            
        except Exception as e:
            await event.reply(f"❌ Gagal convert .json ke .tgs: {str(e)}")
        finally:
            # 4. Bersihkan
            if os.path.exists(json_path):
                os.remove(json_path)
            if 'tgs_path' in locals() and os.path.exists(tgs_path):
                os.remove(tgs_path)
    else:
        await event.reply("⚠️ Mohon balas (reply) ke file .json dengan perintah /json2tgs atau kirim file .json dengan *caption* /json2tgs.")

# --- Feature 4: Remove Background (.png/.jpg) ---
@client.on(events.NewMessage(pattern=r"(?i)/removebg", outgoing=False))
async def removebg_cmd(event):
    if not REMOVE_BG_KEY:
        await event.reply("❌ API Key Remove.bg belum dikonfigurasi.")
        return
        
    if event.is_reply:
        target_message = await event.get_reply_message()
    else:
        target_message = event

    if target_message.file and (target_message.file.ext in ['.png', '.jpg', '.jpeg']):
        await event.reply("⏳ Gambar diterima. Sedang menghapus background...")
        
        # Penamaan file yang aman dan unik
        input_ext = target_message.file.ext
        file_name = f"{event.sender_id}_{os.urandom(4).hex()}"
        input_path = os.path.join(DOWNLOADS_DIR, f"{file_name}{input_ext}")
        output_path = os.path.join(DOWNLOADS_DIR, f"{file_name}_nobg.png")

        # 1. Unduh File
        await target_message.download_media(file=input_path)
        
        try:
            # 2. Proses Remove.bg
            rmbg = RemoveBg(REMOVE_BG_KEY, "error.log") # error.log untuk logging
            # RemoveBg menyimpan output di output_path secara default
            rmbg.remove_background_from_img_file(input_path, size="regular", bg_color="transparent", output_path=output_path)
            
            # 3. Kirim Balik
            await event.reply(file=output_path, caption="✅ Background Dihapus!")
            
        except Exception as e:
            await event.reply(f"❌ Gagal remove background: {str(e)}")
        finally:
            # 4. Bersihkan
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                # Hapus output setelah dikirim
                if 'output_path' in locals() and os.path.exists(output_path):
                     os.remove(output_path)
    else:
        await event.reply("⚠️ Mohon balas (reply) ke file gambar (.png/.jpg) dengan perintah /removebg atau kirim gambar dengan *caption* /removebg.")


print("Bot running...")
client.run_until_disconnected()
    response_message = (
        f"**🚀 Paket Emoji Siap!**\n\n"
