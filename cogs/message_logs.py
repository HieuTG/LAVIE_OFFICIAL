import discord
from discord.ext import commands
import os
from datetime import datetime

class MessageLogsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_log_channel(self, guild: discord.Guild):
        """Hàm hỗ trợ lấy kênh logs từ biến môi trường"""
        log_channel_env = os.getenv("MESSAGE_LOGS")
        if not log_channel_env:
            return None
            
        try:
            channel_id = int(log_channel_env)
            return guild.get_channel(channel_id)
        except ValueError:
            print("⚠️ [Warning] MESSAGE_LOGS trong .env không phải là ID chữ số hợp lệ!")
            return None

    # ==========================================
    # 1. SỰ KIỆN XÓA TIN NHẮN
    # ==========================================
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        # Bỏ qua tin nhắn trong tin nhắn riêng tư (DM) hoặc tin nhắn của Bot
        if not message.guild or message.author.bot:
            return

        log_channel = self.get_log_channel(message.guild)
        if not log_channel or message.channel.id == log_channel.id:
            return

        # Lấy nội dung tin nhắn bị xóa (xử lý trường hợp tin nhắn chỉ có ảnh/file)
        content = message.clean_content if message.clean_content else "*[Tin nhắn không có văn bản hoặc chỉ chứa tệp đính kèm]*"
        if len(content) > 1024:
            content = content[:1020] + "..."

        embed = discord.Embed(
            title="🗑️ TIN NHẮN BỊ XÓA",
            description=f"Tin nhắn của **{message.author.mention}** đã bị xóa tại kênh **{message.channel.mention}**.",
            color=0xe74c3c, # Màu đỏ
            timestamp=datetime.now()
        )
        
        embed.set_author(name=f"{message.author.display_name} ({message.author.id})", icon_url=message.author.display_avatar.url)
        embed.add_field(name="💬 Nội dung bị xóa", value=f"```{content}```", inline=False)
        
        # Nếu có file đính kèm bị xóa thì liệt kê tên file
        if message.attachments:
            files_names = ", ".join([att.filename for att in message.attachments])
            embed.add_field(name="📎 Tệp đính kèm", value=f"`{files_names}`", inline=False)

        embed.set_footer(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    # ==========================================
    # 2. SỰ KIỆN CHỈNH SỬA TIN NHẮN
    # ==========================================
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        # Bỏ qua tin nhắn DM, tin nhắn của Bot
        if not before.guild or before.author.bot:
            return

        # Bỏ qua trường hợp Discord tự động cập nhật Embed/Link (nội dung text không đổi)
        if before.content == after.content:
            return

        log_channel = self.get_log_channel(before.guild)
        if not log_channel or before.channel.id == log_channel.id:
            return

        before_content = before.clean_content if before.clean_content else "*[Trống]*"
        after_content = after.clean_content if after.clean_content else "*[Trống]*"

        # Giới hạn ký tự để không bị lỗi vượt quá 1024 ký tự của Discord Embed
        if len(before_content) > 1000:
            before_content = before_content[:996] + "..."
        if len(after_content) > 1000:
            after_content = after_content[:996] + "..."

        embed = discord.Embed(
            title="✏️ TIN NHẮN ĐƯỢC CHỈNH SỬA",
            description=f"**{before.author.mention}** đã chỉnh sửa tin nhắn trong kênh **{before.channel.mention}**.\n[🔗 Nhấp để đi đến tin nhắn]({after.jump_url})",
            color=0xf1c40f, # Màu vàng
            timestamp=datetime.now()
        )

        embed.set_author(name=f"{before.author.display_name} ({before.author.id})", icon_url=before.author.display_avatar.url)
        embed.add_field(name="🔴 Trước khi sửa", value=f"```{before_content}```", inline=False)
        embed.add_field(name="🟢 Sau khi sửa", value=f"```{after_content}```", inline=False)
        
        embed.set_footer(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

async def setup(bot):
    await bot.add_cog(MessageLogsCog(bot))