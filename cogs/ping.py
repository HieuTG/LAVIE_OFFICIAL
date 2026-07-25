import discord
from discord.ext import commands

class PingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping", aliases=["p"])
    async def ping_command(self, ctx):
        """Lệnh kiểm tra phản hồi của Bot"""
        # Tính toán độ trễ (latency)
        latency = round(self.bot.latency * 1000)
        
        # Đóng gói kết quả vào một Embed gọn gàng
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Độ trễ API hiện tại là: **{latency}ms**",
            color=0x2b2d31 # Màu xám đen đồng bộ với nền Discord
        )
        embed.set_footer(text="Tạp hóa LAVIE - keitou_hazime")
        
        await ctx.send(embed=embed)

# Hàm setup BẮT BUỘC phải có trong mọi file cog
async def setup(bot):
    await bot.add_cog(PingCog(bot))