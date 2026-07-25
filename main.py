import os
from colorama import Fore, Style, init
import discord
from discord.ext import commands
from dotenv import load_dotenv  # 1. Nhập thư viện đọc .env

# 2. Kích hoạt đọc file .env ngay khi chạy chương trình
load_dotenv()

# Khởi tạo colorama cho hệ thống màu console
init(autoreset=True)


class LavieBot(commands.Bot):

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        # Lấy tiền tố từ file .env, nếu không có thì mặc định dùng "!"
        prefix = os.getenv("PREFIX", "!")
        super().__init__(
            command_prefix=prefix, intents=intents, help_command=None
        )

    async def setup_hook(self):
        print(f"\n{Fore.CYAN}╭{'─'*40}╮")
        print(
            f"{Fore.CYAN}│ {Fore.WHITE}ĐANG KIỂM TRA & NẠP HỆ THỐNG MODULE...{Fore.CYAN} │"
        )
        print(f"{Fore.CYAN}├{'─'*40}┤")

        if not os.path.exists("./cogs"):
            os.makedirs("./cogs")

        success_count = 0
        error_count = 0

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(cog_name)
                    print(
                        f"{Fore.CYAN}│ {Fore.GREEN}[OK]{Style.RESET_ALL} Đã nạp thành công: {Fore.YELLOW}{filename:<21} {Fore.CYAN}│"
                    )
                    success_count += 1
                except Exception as e:
                    print(
                        f"{Fore.CYAN}│ {Fore.RED}[ERR]{Style.RESET_ALL} Lỗi nạp {Fore.YELLOW}{filename}: {Fore.RED}{str(e)[:15]}... {Fore.CYAN}│"
                    )
                    error_count += 1

        print(f"{Fore.CYAN}├{'─'*40}┤")
        print(
            f"{Fore.CYAN}│ {Fore.WHITE}TỔNG KẾT: {Fore.GREEN}{success_count} Tốt {Fore.WHITE}| {Fore.RED}{error_count} Lỗi{Fore.CYAN:>18} │"
        )
        print(f"{Fore.CYAN}╰{'─'*40}╯{Style.RESET_ALL}")

    async def on_ready(self):
        activity = discord.Activity(
            type=discord.ActivityType.watching, name="Đang quản lí LAVIE"
        )
        await self.change_presence(
            status=discord.Status.online, activity=activity
        )

        print(f"\n{Fore.MAGENTA}✦ {Fore.WHITE}Bot đã sẵn sàng phục vụ! {Fore.MAGENTA}✦")
        print(
            f"{Fore.GREEN}➜ {Fore.WHITE}Tên đăng nhập: {Fore.YELLOW}{self.user}"
        )
        print(
            f"{Fore.GREEN}➜ {Fore.WHITE}Độ trễ API:   {Fore.YELLOW}{round(self.latency * 1000)}ms"
        )
        print(
            f"{Fore.GREEN}➜ {Fore.WHITE}Trạng thái:   {Fore.YELLOW}Đang xem Tạp hóa LAVIE\n"
        )


if __name__ == "__main__":
    bot = LavieBot()

    # 3. Lấy token một cách bảo mật từ biến môi trường
    token = os.getenv("BOT_TOKEN")

    # Kiểm tra xem đã điền Token chưa
    if not token:
        print(
            f"{Fore.RED}[LỖI NGHIÊM TRỌNG] Chưa tìm thấy DISCORD_TOKEN trong file .env! Vui lòng kiểm tra lại."
        )
    else:
        bot.run(token)