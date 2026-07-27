import discord
from discord import member
from discord.ext import commands
import os


# ==========================================
# 1. GIAO DIỆN WELCOME COMPONENT V2 (KÊNH WELCOME)
# ==========================================
class WelcomeView(discord.ui.LayoutView):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        
        # Ping thành viên mới
        text_display1 = discord.ui.TextDisplay(content=f"{member.mention}")
        
        # Container chứa nội dung khung chào mừng
        container1 = discord.ui.Container(
            discord.ui.TextDisplay(content="# <a:sillyguy:1529888500566987054> Welcome to LAVIE !!"),
            discord.ui.Separator(visible=False, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="<:blue_point:1270403608114102304> <#1502093991863386152> Nơi để bạn cập nhật thông báo mới nhất của sivi\n<:blue_point:1270403608114102304> Đọc kĩ luật tại <#1502093758265692232>\n<:blue_point:1270403608114102304> <#1501566557287878786> Chat sinh hoạt chung văn hóa và thân thiện"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media="https://images-ext-1.discordapp.net/external/XHnM7jcGYALEoNjeaK3tg001PsRZ9hB5okOubQOjzM0/https/cdn.noctaly.com/servers/1501565452592091156/cNfLLrKnTY.gif?width=1280&height=688",
                ),
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=f"-# LAVIE - Thành viên thứ {member.guild.member_count}"),
        )
        
        self.add_item(text_display1)
        self.add_item(container1)


# ==========================================
# 2. XỬ LÝ SỰ KIỆN THÀNH VIÊN MỚI
# ==========================================
class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Tự động kích hoạt khi có thành viên mới vào server"""
        
        # --- TÍNH NĂNG 1: GỬI COMPONENT V2 VÀO KÊNH WELCOME ---
        welcome_channel_env = os.getenv("WELCOME_CHANNEL")
        if welcome_channel_env and welcome_channel_env.isdigit():
            try:
                channel_id = int(welcome_channel_env)
                wlc_channel = member.guild.get_channel(channel_id)
                if wlc_channel:
                    view = WelcomeView(member)
                    await wlc_channel.send(view=view)
            except Exception as e:
                print(f"❌ [Lỗi Welcome Component]: {e}")

async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))