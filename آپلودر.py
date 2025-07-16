#شروع ایمپورت
import os
import aiohttp
import time
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
#اتمام ایمپورت

#شروع اطلاعات
API_ID = 20793669
API_HASH = "a54f28c6b92cb12048063693d65c379f"
BOT_TOKEN = "7647177541:AAEFg3LFGyrdIQfzd6bqHxLr0V4Nk4RdiUs"
CHANNEL_USERNAME = "tyemydoc"
#اتمام اطلاعات

#شروع بات
app = Client("uploader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_states = {}
temp_files = {}

stats = {
    "downloaded_bytes": 0,
    "uploaded_bytes": 0,
    "download_time": 0,
    "upload_time": 0,
}

keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📥 آپلود از لینک")],
        [KeyboardButton("📤 آپلود داخلی | فوروارد")],
        [KeyboardButton("📊 گزارش استفاده")]
    ],
    resize_keyboard=True
)

def emoji_progress(percent):
    total_blocks = 5
    filled = int(percent / (100 / total_blocks))
    return "🔵"*filled + "⚪️"*(total_blocks - filled)

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply("👋 سلام! یکی از گزینه‌ها رو انتخاب کن:", reply_markup=keyboard)

@app.on_message(filters.private & filters.text)
async def handle_text(client, message: Message):
    user_id = message.from_user.id
    text = message.text.strip()

    state = user_states.get(user_id)

    if state == "waiting_link":
        msg = await message.reply("🚀 شروع دانلود...")
        file_path = await download_file(text, msg)
        if file_path:
            temp_files[user_id] = file_path
            user_states[user_id] = "waiting_caption"
            await msg.edit("✏️ لطفا کپشن دلخواهت رو بنویس.")
        else:
            await msg.edit("❌ دانلود ناموفق.")
            user_states.pop(user_id, None)

    elif state == "waiting_forward":
        await message.reply("لطفا فایل رو فوروارد کن.")
    
    elif state == "waiting_caption":
        file_path = temp_files.pop(user_id, None)
        if file_path:
            msg = await message.reply("🚀 در حال آپلود...")
            await upload_to_channel(msg, file_path, caption=text)
            os.remove(file_path)
            user_states.pop(user_id, None)
        else:
            await message.reply("❌ فایل موقتی پیدا نشد.")
            user_states.pop(user_id, None)

    elif text == "📥 آپلود از لینک":
        user_states[user_id] = "waiting_link"
        await message.reply("✅ لینک رو بفرست.", reply_markup=keyboard)

    elif text == "📤 آپلود داخلی | فوروارد":
        user_states[user_id] = "waiting_forward"
        await message.reply("✅ فایل رو فوروارد کن.", reply_markup=keyboard)

    elif text == "📊 گزارش استفاده":
        report = (
            f"📊 گزارش:\n"
            f"⬇️ دانلود: {stats['downloaded_bytes'] / (1024*1024):.2f} MB\n"
            f"🕐 زمان دانلود: {stats['download_time']:.2f}s\n"
            f"⬆️ آپلود: {stats['uploaded_bytes'] / (1024*1024):.2f} MB\n"
            f"🕐 زمان آپلود: {stats['upload_time']:.2f}s"
        )
        await message.reply(report, reply_markup=keyboard)

@app.on_message(filters.private & filters.forwarded)
async def handle_forward(client, message: Message):
    user_id = message.from_user.id
    if user_states.get(user_id) == "waiting_forward":
        if not message.media:
            await message.reply("❌ این پیام فایل نداره.", reply_markup=keyboard)
            return
        msg = await message.reply("⬇️ در حال دانلود...")
        file_path = await client.download_media(message, progress=progress_bar(msg, "دانلود"))
        if file_path:
            temp_files[user_id] = file_path
            user_states[user_id] = "waiting_caption"
            await msg.edit("✏️ لطفا کپشن دلخواهت رو بنویس.")
        else:
            await msg.edit("❌ خطا در دانلود.")
            user_states.pop(user_id, None)

def progress_bar(msg, mode):
    last_update = time.time()
    async def progress(current, total):
        nonlocal last_update
        if time.time() - last_update > 1:
            percent = current * 100 / total if total else 0
            bar = emoji_progress(percent)
            try:
                await msg.edit(f"⚙️ {mode}: {bar} {percent:.1f}%")
            except: pass
            last_update = time.time()
    return progress

async def download_file(url, msg):
    filename = url.split("/")[-1].split("?")[0] or "file.bin"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=300) as resp:
                total = int(resp.headers.get("Content-Length", 0)) or None
                chunk_size = 64 * 1024
                downloaded = 0
                start_time = time.time()
                last_update = time.time()
                with open(filename, "wb") as f:
                    async for chunk in resp.content.iter_chunked(chunk_size):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if time.time() - last_update > 1:
                            percent = downloaded * 100 / total if total else 0
                            bar = emoji_progress(percent)
                            elapsed = time.time() - start_time
                            speed = downloaded / 1024 / elapsed if elapsed else 0
                            eta = (total - downloaded) / 1024 / speed if total and speed else 0
                            if total:
                                await msg.edit(f"⬇️: {bar} {percent:.1f}%\n🚀 {speed:.1f} KB/s ⏱ {eta:.1f}s")
                            else:
                                await msg.edit(f"⬇️: {bar} {downloaded/(1024*1024):.2f} MB\n🚀 {speed:.1f} KB/s")
                            last_update = time.time()
                stats["downloaded_bytes"] += downloaded
                stats["download_time"] += time.time() - start_time
                return filename
    except Exception as e:
        await msg.edit(f"❌ خطا: {e}")
        return None

async def upload_to_channel(msg, file_path, caption="🚀 فایل آپلود شده توسط ربات"):
    start_time = time.time()
    file_size = os.path.getsize(file_path)
    async def progress(current, total):
        percent = current * 100 / total if total else 0
        bar = emoji_progress(percent)
        elapsed = time.time() - start_time
        speed = current / 1024 / elapsed if elapsed else 0
        eta = (total - current) / 1024 / speed if speed else 0
        try:
            await msg.edit(f"⬆️: {bar} {percent:.1f}%\n🚀 {speed:.1f} KB/s ⏱ {eta:.1f}s")
        except: pass
    try:
        await app.send_document(CHANNEL_USERNAME, file_path, caption=caption, progress=progress)
        stats["uploaded_bytes"] += file_size
        stats["upload_time"] += time.time() - start_time
        await msg.edit("✅ آپلود با موفقیت انجام شد.", reply_markup=keyboard)
    except Exception as e:
        await msg.edit(f"❌ خطا در آپلود: {e}")

if __name__ == "__main__":
    print("🚀 ربات داره کار میکنه")
    app.run()
#اتمام بات