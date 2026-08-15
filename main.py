import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import database as db

# 1. Tải cấu hình từ file .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
PREFIX = os.getenv("PREFIX", "!")

# 2. Cấu hình Intents (Quyền hạn của Bot)
# Cần bật tất cả Intents để theo dõi được Member Join/Leave, Audit Logs (Ban/Kick/Channel) và Tin nhắn
intents = discord.Intents.all()

# 3. Định nghĩa Lớp Bot chính (Sử dụng cấu trúc OOP hiện đại của discord.py)
class LavieBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None, # Tắt lệnh help mặc định để tránh xung đột
            case_insensitive=True # Không phân biệt chữ hoa/thường khi gõ lệnh
        )

    async def setup_hook(self):
        """Hàm tự động chạy trước khi bot kết nối để tải các module (Cogs)"""
        db.init_db()
        print("⏳ Đang tải hệ thống các module (Cogs)...")
        
        # Kiểm tra và tạo thư mục cogs nếu chưa tồn tại
        if not os.path.exists("./cogs"):
            os.makedirs("./cogs")
            print("📁 Đã tự động tạo thư mục ./cogs mới.")
        
        # Tự động quét và tải toàn bộ file .py trong thư mục cogs
        loaded_count = 0
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(cog_name)
                    print(f"  ✔ [OK] Đã tải module: {filename}")
                    loaded_count += 1
                except Exception as e:
                    print(f"  ❌ [LỖI] Không thể tải {filename} -> {e}")

        print(f"📦 Đã tải thành công {loaded_count} module.")

        # Đồng bộ Slash Commands (Lệnh gạch chéo /) với Discord
        try:
            synced = await self.tree.sync()
            print(f"🌐 Đã đồng bộ thành công {len(synced)} lệnh Slash Commands.")
        except Exception as e:
            print(f"⚠️ Lỗi khi đồng bộ Slash Commands: {e}")

    async def on_ready(self):
        """Sự kiện kích hoạt khi Bot đã hoàn tất kết nối và sáng đèn"""
        print("=" * 45)
        print(f"🚀 BOT ĐÃ KHỞI ĐỘNG VÀ SẴN SÀNG HOẠT ĐỘNG!")
        print(f"🤖 Tên Bot  : {self.user} (ID: {self.user.id})")
        print(f"📡 Máy chủ  : Đang kết nối với {len(self.guilds)} server")
        print("=" * 45)

        # Cài đặt trạng thái hiển thị của Bot trên Discord (Status / Activity)
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"Đang theo dõi L A V I E"
            )
        )

# 4. Khởi tạo và Khởi chạy Bot
bot = LavieBot()

if __name__ == "__main__":
    if not TOKEN:
        print("❌ [LỖI NGHIÊM TRỌNG] Không tìm thấy biến DISCORD_TOKEN trong file .env!")
        print("👉 Vui lòng tạo file .env trên máy và điền DISCORD_TOKEN=Mã_Token_Của_Bạn vào.")
    else:
        try:
            # Khởi chạy Bot
            bot.run(TOKEN)
        except discord.LoginFailure:
            print("❌ [LỖI ĐĂNG NHẬP] Token không hợp lệ hoặc đã bị Discord tự động reset!")
            print("👉 Vui lòng vào Discord Developer Portal copy lại Token mới nhất.")
        except Exception as e:
            print(f"❌ Lỗi ngoại lệ khi khởi chạy bot: {e}")