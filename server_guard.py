import os
import discord
from discord.ext import commands

class ServerGuardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_allowed_guilds(self):
        raw = os.getenv("ALLOWED_GUILDS", "")
        return [int(g.strip()) for g in raw.split(",") if g.strip().isdigit()]

    # 1. Tự động kiểm tra và rời tất cả server lạ khi Bot bật lên
    @commands.Cog.listener()
    async def on_ready(self):
        allowed = self.get_allowed_guilds()
        if not allowed:
            return

        for guild in self.bot.guilds:
            if guild.id not in allowed:
                await guild.leave()
                print(f"🚫 [GUARD] Đã rời khỏi server lạ: {guild.name} (ID: {guild.id})")

    # 2. Ngăn chặn: Nếu ai đó cố tình thêm Bot vào server mới, Bot tự thoát ngay
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        allowed = self.get_allowed_guilds()
        if allowed and guild.id not in allowed:
            await guild.leave()
            print(f"⛔ [GUARD] Từ chối tham gia server lạ: {guild.name} (ID: {guild.id})")

    # 3. Lệnh thủ công dành cho Owner: !leaveserver <Guild_ID>
    @commands.command(name="leaveserver")
    @commands.is_owner()
    async def leave_server_cmd(self, ctx, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if guild:
            name = guild.name
            await guild.leave()
            await ctx.reply(f"✅ Đã ép Bot rời khỏi server: **{name}** (`{guild_id}`)")
        else:
            await ctx.reply("❌ Bot không có mặt trong server này!")

async def setup(bot):
    await bot.add_cog(ServerGuardCog(bot))