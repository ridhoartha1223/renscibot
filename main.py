import os
import logging
import re
from telegram import Update, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from removebg import RemoveBg
from PIL import Image

# --- Konfigurasi Awal ---
# Konfigurasi Logging
logging.basicConfig(
   format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Atur variabel lingkungan dari Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
REMOVE_BG_KEY = os.getenv("REMOVE_BG_KEY")
DOWNLOADS_DIR = "downloads"

# Definisikan State untuk ConversationHandler (Feature 2: .tgs)
GET_PACK_NAME = 1

# Pastikan folder downloads ada
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# --- FUNGSI DUMMY (INTEGRASI LOTTIE/TGS) ---
# CATATAN PENTING: Implementasi fungsi ini adalah TUGAS ANDA.
# Bot ini hanya menyediakan kerangka. Anda perlu mengganti 'pass' dengan
# kode yang memanggil Lottie tool/library yang sesuai (misalnya, pylottie, atau
# subprocess call ke lottie-rs/lottie-min yang dikompilasi di Railway).

def optimize_tgs_file(file_path: str) -> str:
   """Simulasi: Menerima path .tgs, optimasi, dan mengembalikan path baru."""
   # Implementasi Nyata: Panggil tool/library optimasi Lottie di sini.
   # Contoh: subprocess.run(['lottie-min', file_path, '-o', optimized_path])
   
   # Keterangan: Jika optimasi tidak mengubah path, Anda bisa langsung mengembalikan file_path.
   return file_path

def convert_json_to_tgs_file(json_path: str) -> str:
   """Simulasi: Menerima path .json, konversi ke .tgs, dan mengembalikan path .tgs."""
   # Implementasi Nyata: Panggil tool/library konversi Lottie di sini.
   # Contoh: output_path = json_path.replace(".json", ".tgs")
   # Contoh: subprocess.run(['lottie-tool', 'convert', json_path, output_path])
   
   tgs_path = json_path.replace(".json", ".tgs")
   return tgs_path

# --- HANDLER: /start (Feature 1) ---
async def start_command(update: Update, context) -> None:
   """Menampilkan pesan selamat datang, command, dan kegunaan."""
   welcome_message = (
       "**Selamat Datang di Bot Emoji Animasi (.tgs) Penuh Fitur! 🤖**\n\n"
       "Saya dirancang untuk membantu Anda membuat, mengoptimalkan, dan membagikan "
       "paket **Emoji Animasi (.tgs)** Anda.\n\n"
       "**Daftar Command & Fitur:**\n"
       "1. **Kirim file .tgs:** Bot akan **otomatis mengoptimalkan** ukurannya, "
       "meminta nama paket, dan membuat *share link* `t.me/addemoji/...`.\n"
       "2. **`/json2tgs`:** Kirim atau balas ke file **.json** untuk di-convert menjadi **.tgs**.\n"
       "3. **`/removebg`:** Kirim atau balas ke file **gambar (.png/.jpg)** untuk menghapus *background*.\n"
   )
   await update.message.reply_text(welcome_message, parse_mode='Markdown')

# --- HANDLER: Feature 2: Proses Otomatis .TGS (Multi-Langkah) ---

async def handle_tgs_file(update: Update, context) -> int:
   """Langkah 1: Menerima file .tgs, mengoptimalkan, dan meminta nama pack."""
   file_id = update.message.document.file_id
   file_name = update.message.document.file_name
   user_id = update.effective_user.id
   
   await update.message.reply_text("✅ File **.tgs** diterima. Sedang mengunduh dan mengoptimalkan...")
   
   # 1. Unduh File
   new_file = await context.bot.get_file(file_id)
   safe_name = f"{user_id}_{os.urandom(4).hex()}_{file_name}"
   download_path = os.path.join(DOWNLOADS_DIR, safe_name)
   await new_file.download_to_drive(download_path)
   
   try:
       # 2. Optimasi (Minify)
       await update.message.reply_text("⏳ Mengoptimalkan ukuran file...")
       optimized_path = optimize_tgs_file(download_path)
       
       # Simpan path file di context.user_data
       context.user_data['tgs_path'] = optimized_path
       
       await update.message.reply_text(
           "🎉 **Optimasi selesai!** File siap dijadikan emoji pack.\n"
           "Sekarang, **kirimkan nama unik** untuk paket emoji Anda (contoh: `MyCoolPack`)\n"
           "*(Hanya huruf dan angka)*",
           reply_markup=ForceReply(selective=True)
       )
       
       # Pindah ke State GET_PACK_NAME
       return GET_PACK_NAME
       
   except Exception as e:
       await update.message.reply_text(f"❌ Gagal memproses file .tgs. Error: {e}")
       if os.path.exists(download_path):
           os.remove(download_path)
       # Batalkan ConversationHandler
       return ConversationHandler.END

async def get_pack_name(update: Update, context) -> int:
   """Langkah 2: Menerima nama pack, generate link, kirim file, dan selesai."""
   user_id = update.effective_user.id
   pack_name = update.message.text.strip()
   
   original_file_path = context.user_data.pop('tgs_path', None)
   
   # Bersihkan data jika ada error/validasi
   def cleanup():
       if original_file_path and os.path.exists(original_file_path):
           os.remove(original_file_path)

   if not original_file_path or not os.path.exists(original_file_path):
       await update.message.reply_text("❌ File .tgs sebelumnya hilang atau proses sudah kadaluarsa. Silakan kirim ulang file .tgs Anda.")
       return ConversationHandler.END

   # Validasi nama pack
   if not re.fullmatch(r'^[a-zA-Z0-9]+$', pack_name):
       await update.message.reply_text(
           "⚠️ Nama paket tidak valid. Gunakan hanya huruf dan angka (contoh: `KucingImutPack`)."
       )
       cleanup()
       return ConversationHandler.END

   # Generate Link & Kirim Hasil
   emoji_pack_link = f"t.me/addemoji/{pack_name}"
   
   response_message = (
       f"**🚀 Paket Emoji Siap!**\n\n"
       f"Nama Paket Anda: `{pack_name}`\n"
       f"Link Emoji Pack: {emoji_pack_link}\n\n"
       f"File **.tgs** yang dioptimalkan dikirim di bawah ini."
   )
   
   try:
       with open(original_file_path, 'rb') as f:
           await update.message.reply_document(
               document=f,
               caption=response_message,
               parse_mode='Markdown'
           )
   except Exception as e:
       await update.message.reply_text(f"❌ Gagal mengirim file .tgs hasil optimasi: {e}")
   finally:
       cleanup()

   return ConversationHandler.END

async def cancel_tgs(update: Update, context) -> int:
   """Membatalkan proses .tgs jika ada teks yang tidak terduga."""
   if 'tgs_path' in context.user_data:
       file_path = context.user_data.pop('tgs_path')
       if os.path.exists(file_path):
           os.remove(file_path)
   
   await update.message.reply_text("Proses pembuatan paket emoji dibatalkan.")
   return ConversationHandler.END


# --- HANDLER: Feature 3: Konversi .json ke .tgs ---
async def json2tgs_command(update: Update, context) -> None:
   """Convert file .json menjadi .tgs"""
   message = update.message
   target_message = message.reply_to_message if message.reply_to_message else message
   
   if not target_message.document or target_message.document.mime_type != 'application/json':
       await message.reply_text("⚠️ Mohon balas (reply) ke file **.json** atau kirim file .json dengan *caption* `/json2tgs`.")
       return

   file_id = target_message.document.file_id
   json_path = None
   tgs_path = None
   
   try:
       await message.reply_text("⏳ File **.json** diterima. Sedang di-convert ke **.tgs**...")
       
       # 1. Unduh File
       new_file = await context.bot.get_file(file_id)
       json_path = os.path.join(DOWNLOADS_DIR, f"temp_{os.urandom(4).hex()}.json")
       await new_file.download_to_drive(json_path)
       
       # 2. Convert & Optimasi
       tgs_path = convert_json_to_tgs_file(json_path)
       
       # 3. Kirim Balik
       with open(tgs_path, 'rb') as f:
            await message.reply_document(document=f, caption="✅ Konversi & Optimasi Selesai!")
       
   except Exception as e:
       await message.reply_text(f"❌ Gagal convert .json ke .tgs: {e}")
   finally:
       # 4. Bersihkan
       if json_path and os.path.exists(json_path):
           os.remove(json_path)
       if tgs_path and os.path.exists(tgs_path):
           os.remove(tgs_path)

# --- HANDLER: Feature 4: Remove Background (.png/.jpg) ---
async def removebg_command(update: Update, context) -> None:
   """Hapus background dari gambar menggunakan remove.bg API"""
   message = update.message
   target_message = message.reply_to_message if message.reply_to_message else message
   
   if not REMOVE_BG_KEY:
       await message.reply_text("❌ **API Key Remove.bg** belum dikonfigurasi.")
       return
   
   # Cek apakah ada file yang didukung
   if not target_message.photo and (not target_message.document or target_message.document.mime_type not in ['image/png', 'image/jpeg']):
       await message.reply_text("⚠️ Mohon balas (reply) ke file **gambar (.png/.jpg)** atau kirim gambar dengan *caption* `/removebg`.")
       return
       
   file_id = target_message.photo[-1].file_id if target_message.photo else target_message.document.file_id
   
   input_path = None
   output_path = None
   
   try:
       await message.reply_text("⏳ Gambar diterima. Sedang menghapus background...")
       
       # 1. Unduh File
       new_file = await context.bot.get_file(file_id)
       input_path = os.path.join(DOWNLOADS_DIR, f"in_{os.urandom(4).hex()}.jpg") # Gunakan .jpg/png
       output_path = os.path.join(DOWNLOADS_DIR, f"out_{os.urandom(4).hex()}_nobg.png")
       await new_file.download_to_drive(input_path)
       
       # 2. Proses Remove.bg
       rmbg = RemoveBg(REMOVE_BG_KEY, "error.log")
       rmbg.remove_background_from_img_file(input_path, size="regular", output_path=output_path)
       
       # 3. Kirim Balik
       with open(output_path, 'rb') as f:
            await message.reply_document(document=f, caption="✅ Background Dihapus!")
       
   except Exception as e:
       await message.reply_text(f"❌ Gagal remove background. Pastikan API key valid: {e}")
   finally:
       # 4. Bersihkan
       if input_path and os.path.exists(input_path):
           os.remove(input_path)
       if output_path and os.path.exists(output_path):
           os.remove(output_path)

# --- FUNGSI UTAMA (MAIN) ---
def main() -> None:
   """Menjalankan bot."""
   if not BOT_TOKEN:
       raise ValueError("BOT_TOKEN tidak ditemukan. Bot tidak bisa dijalankan.")

   # 1. Buat Aplikasi dan atur ConversationHandler
   application = Application.builder().token(BOT_TOKEN).build()
   
   # Conversation Handler untuk proses .tgs
   tgs_handler = ConversationHandler(
       entry_points=[MessageHandler(filters.Document.TGS, handle_tgs_file)],
AttributeError: type object 'Document' has no attribute 'TGS'
entry_points=[MessageHandler(filters.Document.TGS, handle_tgs_file)],
AttributeError: type object 'Document' has no attribute 'TGS'
)

   # 2. Tambahkan Handlers
   application.add_handler(CommandHandler("start", start_command))
   application.add_handler(tgs_handler)
   
   # Handlers untuk command file
   application.add_handler(CommandHandler("json2tgs", json2tgs_command)
   application.add_handler(MessageHandler(filters.Document.JSON & filters.Caption("json2tgs"), json2tgs_command))

   application.add_handler(CommandHandler("removebg", removebg_command))
   application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL & (filters.Caption("removebg") | filters.Caption("/removebg")), removebg_command))
   
   # 3. Jalankan Bot (Railway akan menggunakan polling atau webhook, tergantung setup)
   print("Bot is running...")
   application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
   main()

