import os
import asyncio
from telethon import TelegramClient, events
# PENTING: Pastikan file lottie_convert.py ada dan berisi fungsi yang diperlukan!
try:
    from lottie_convert import convert_json_to_tgs, optimize_tgs
except ImportError:
    print("WARNING: lottie_convert.py tidak ditemukan. Fitur TGS/JSON tidak akan berfungsi.")
    
from removebg import RemoveBg 

# --- Variabel Lingkungan (Environment Variables) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
REMOVE_BG_KEY = os.getenv("REMOVE_BG_KEY")

# --- Inisialisasi Klien ---
if not all([BOT_TOKEN, API_ID, API_HASH]):
    raise ValueError("API_ID, API_HASH, atau BOT_TOKEN belum dikonfigurasi di environment variables.")

client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- State Management ---
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
        "**Daftar Command & Fitur:**\n"
        "1. Kirim file .tgs: Bot akan otomatis mengoptimalkan ukurannya, "
        "meminta nama paket, dan membuat *share link* t.me/addemoji/....\n"
        "2. `/json2tgs`: Balas ke file .json untuk di-convert menjadi .tgs.\n"
        "3. `/removebg`: Balas ke file gambar (.png/.jpg) untuk menghapus *background*.\n\n"
    )
    await event.reply(welcome_message)

# --- Feature 2: Otomatis Menerima & Mengoptimalkan .tgs ---
@client.on(events.NewMessage(func=lambda e: e.media and e.file and e.file.ext == '.tgs'))
async def handle_tgs_file(event):
    user_id = event.sender_id
    temp_path = None 
    downloaded_path = None
    
    await event.reply("✅ File .tgs diterima. Sedang mengunduh dan mengoptimalkan...")
    
    try:
        file_name = f"{user_id}_{os.urandom(4).hex()}_in.tgs"
        temp_path = os.path.join(DOWNLOADS_DIR, file_name)
        downloaded_path = await event.download_media(temp_path)
        
        await event.reply("⏳ Mengoptimalkan ukuran file...")
        # Asumsi: optimize_tgs akan mengembalikan path ke file yang sudah dioptimalkan
        optimized_path = optimize_tgs(downloaded_path) 
        
        processing_tgs[user_id] = optimized_path
        
        await client.send_message(
            user_id,
            "🎉 Optimasi selesai! File siap dijadikan emoji pack.\n"
            "Sekarang, kirimkan nama unik untuk paket emoji Anda (contoh: `MyCoolPack`)\n"
            "*(Hanya huruf dan angka, tanpa spasi atau karakter khusus)*"
        )
        
    except Exception as e:
        await event.reply(f"❌ Gagal memproses file .tgs. Pastikan file valid dan lottie_convert.py berfungsi: {str(e)}")
        if user_id in processing_tgs:
            del processing_tgs[user_id]
        if downloaded_path and os.path.exists(downloaded_path):
             os.remove(downloaded_path)


# --- Menanggapi Nama Pack yang Dikirim Setelah Optimasi ---
@client.on(events.NewMessage(func=lambda e: e.sender_id in processing_tgs and not e.file and not e.text.startswith('/')))
async def get_pack_name(event):
    user_id = event.sender_id
    pack_name = event.text.strip()
    
    # Ambil path file, dan hapus dari state *sebelum* proses lain
    original_file_path = processing_tgs.pop(user_id, None) 
    
    if not original_file_path or not os.path.exists(original_file_path):
        await event.reply("❌ File .tgs sebelumnya hilang atau proses sudah kadaluarsa. Silakan kirim ulang file .tgs Anda.")
        return
        
    # Validasi nama pack
    if not pack_name.isalnum():
        await event.reply(
            "⚠️ Nama paket tidak valid. Gunakan hanya huruf dan angka (contoh: `KucingImutPack`). "
            "Silakan kirim ulang file .tgs dan ulangi prosesnya."
        )
        # PERBAIKAN: Gunakan pengecekan keberadaan file sebelum dihapus
        if os.path.exists(original_file_path):os.remove(original_file_path)
        return

    # 4. Generate Link & Kirim Hasil
    emoji_pack_link = f"t.me/addemoji/{pack_name}"
    
    response_message = (
        f"**🚀 Paket Emoji Siap!**\n\n"
        f"Nama Paket Anda: `{pack_name}`\n"
        f"Link Emoji Pack: {emoji_pack_link}\n\n"
        f"File .tgs yang dioptimalkan dikirim di bawah ini."
    )
    
    try:
        # Kirim file .tgs yang sudah dioptimalkan
        await client.send_file(user_id, original_file_path, caption=response_message)
    except Exception as e:
        await event.reply(f"❌ Gagal mengirim file .tgs hasil optimasi: {str(e)}")
    finally:
        # 5. Bersihkan file setelah berhasil dikirim atau gagal kirim
        if os.path.exists(original_file_path):
            os.remove(original_file_path)


# --- Feature 3: Konversi .json ke .tgs ---
@client.on(events.NewMessage(pattern=r"(?i)/json2tgs", outgoing=False))
async def json2tgs_cmd(event):
    tgs_path = None
    json_path = None
    
    if event.is_reply:
        target_message = await event.get_reply_message()
    else:
        target_message = event

    if target_message.file and target_message.file.ext == '.json':
        await event.reply("⏳ File .json diterima. Sedang di-convert ke .tgs...")
        
        try:
            file_name = f"{event.sender_id}_{os.urandom(4).hex()}.json"
            json_path = await target_message.download_media(file=os.path.join(DOWNLOADS_DIR, file_name))
            
            tgs_path = convert_json_to_tgs(json_path) 
            
            await event.reply(file=tgs_path, caption="✅ Konversi & Optimasi Selesai!")
            
        except Exception as e:
            await event.reply(f"❌ Gagal convert .json ke .tgs: {str(e)}")
        finally:
            if json_path and os.path.exists(json_path):
                os.remove(json_path)
            if tgs_path and os.path.exists(tgs_path):
                os.remove(tgs_path)
    else:
        await event.reply("⚠️ Mohon balas (reply) ke file .json dengan perintah /json2tgs.")

# --- Feature 4: Remove Background (.png/.jpg) ---
@client.on(events.NewMessage(pattern=r"(?i)/removebg", outgoing=False))
async def removebg_cmd(event):
    input_path = None
    output_path = None

    if not REMOVE_BG_KEY:
        await event.reply("❌ API Key Remove.bg belum dikonfigurasi. Fitur tidak dapat digunakan.")
        return
        
    if event.is_reply:
        target_message = await event.get_reply_message()
    else:
        target_message = event

    if target_message.file and (target_message.file.ext in ['.png', '.jpg', '.jpeg']):
        await event.reply("⏳ Gambar diterima. Sedang menghapus background...")
        
        try:
            input_ext = target_message.file.ext
            file_name = f"{event.sender_id}_{os.urandom(4).hex()}"
            input_path = os.path.join(DOWNLOADS_DIR, f"{file_name}{input_ext}")
            output_path = os.path.join(DOWNLOADS_DIR, f"{file_name}_nobg.png")

            await target_message.download_media(file=input_path)
            
            rmbg = RemoveBg(REMOVE_BG_KEY, "error.log") 
            rmbg.remove_background_from_img_file(input_path, size="regular", bg_color="transparent", output_path=output_path)
            
            await event.reply(file=output_path, caption="✅ Background Dihapus!")
            
        except Exception as e:
            await event.reply(f"❌ Gagal remove background: {str(e)}")
        finally:
            if input_path and os.path.exists(input_path):
                os.remove(input_path)
            if output_path and os.path.exists(output_path):
                 os.remove(output_path)
    else:
        await event.reply("⚠️ Mohon balas (reply) ke file gambar (.png/.jpg) dengan perintah /removebg.")


print("Bot running...")
client.run_until_disconnected()
