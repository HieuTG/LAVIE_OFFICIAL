import discord
from discord.ext import commands
from discord import app_commands
import os
import database as db

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_welcome_config(self, guild_id: int):
        """Lấy cấu hình Welcome từ Database, dự phòng từ file .env"""
        config = db.get_guild_config(guild_id)
        
        channel_id = config.get("welcome_channel_id")
        if not channel_id:
            env_channel = os.getenv("WELCOME_CHANNEL")
            if env_channel and env_channel.isdigit():
                channel_id = int(env_channel)

        message = config.get("welcome_message") or (
            "🎉 Chào mừng {mention} đã tham gia **{server}**!\n"
            "👥 Bạn là thành viên thứ `{count}` của máy chủ. Hãy đọc kỹ nội quy nhé!"
        )
        
        image_url = config.get("welcome_image_url")
        enabled = config.get("welcome_enabled", 1)  # Mặc định 1 (Bật)

        return channel_id, message, image_url, enabled

    def build_welcome_embed(self, member: discord.Member, message_template: str, image_url: str = None) -> discord.Embed:
        """Tạo Embed chào mừng kèm thay thế các biến động"""
        formatted_message = message_template.format(
            mention=member.mention,
            user=member.name,
            display_name=member.display_name,
            server=member.guild.name,
            count=member.guild.member_count
        )

        embed = discord.Embed(
            title="👋 THÀNH VIÊN MỚI GIA NHẬP!",
            description=formatted_message,
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"ID Thành viên: {member.id}")

        if image_url:
            embed.set_image(url=image_url)

        return embed

    # ==========================================
    # 1. GROUP SLASH COMMAND: /welcome
    # ==========================================
    welcome_group = app_commands.Group(name="welcome", description="Cấu hình hệ thống Chào mừng thành viên mới")

    # --- /welcome setup ---
    @welcome_group.command(name="setup", description="Thiết lập kênh và lời nhắn chào mừng")
    @app_commands.describe(
        channel="Kênh sẽ gửi tin nhắn chào mừng",
        message="Nội dung chào mừng (Có thể dùng: {mention}, {user}, {server}, {count})",
        image_url="URL hình ảnh Banner đính kèm (Tùy chọn)"
    )
    @app_commands.default_permissions(administrator=True)
    async def welcome_setup(
        self, 
        interaction: discord.Interaction, 
        channel: discord.TextChannel, 
        message: str = None, 
        image_url: str = None
    ):
        db.set_server_setting(interaction.guild_id, "welcome_channel_id", channel.id)
        db.set_server_setting(interaction.guild_id, "welcome_enabled", 1)

        if message:
            db.set_server_setting(interaction.guild_id, "welcome_message", message)
        if image_url:
            db.set_server_setting(interaction.guild_id, "welcome_image_url", image_url)

        embed = discord.Embed(
            title="✅ CÀI ĐẶT CHÀO MỪNG THÀNH CÔNG",
            description=(
                f"• **Kênh:** {channel.mention}\n"
                f"• **Trạng thái:** 🟢 Đã bật\n\n"
                f"💡 *Bạn có thể dùng lệnh `/welcome test` để xem thử giao diện hiển thị.*"
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- /welcome test ---
    @welcome_group.command(name="test", description="Thử nghiệm gửi tin nhắn Chào mừng")
    @app_commands.default_permissions(administrator=True)
    async def welcome_test(self, interaction: discord.Interaction):
        channel_id, message_template, image_url, enabled = self.get_welcome_config(interaction.guild_id)

        if not channel_id:
            return await interaction.response.send_message(
                "❌ **Chưa cài đặt kênh!** Vui lòng dùng lệnh `/welcome setup` trước.", 
                ephemeral=True
            )

        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            return await interaction.response.send_message(
                "❌ **Không tìm thấy kênh!** Kênh chào mừng đã bị xóa hoặc Bot không có quyền truy cập.", 
                ephemeral=True
            )

        embed = self.build_welcome_embed(interaction.user, message_template, image_url)
        await channel.send(content=f"🔔 *[Chế độ Test]*", embed=embed)
        await interaction.response.send_message(f"✅ Đã gửi tin nhắn mẫu đến kênh {channel.mention}!", ephemeral=True)

    # --- /welcome disable ---
    @welcome_group.command(name="disable", description="Tắt tính năng Chào mừng thành viên")
    @app_commands.default_permissions(administrator=True)
    async def welcome_disable(self, interaction: discord.Interaction):
        db.set_server_setting(interaction.guild_id, "welcome_enabled", 0)
        await interaction.response.send_message("🔴 **Đã tắt tính năng Chào mừng thành viên.**", ephemeral=True)

    # ==========================================
    # 2. SỰ KIỆN THÀNH VIÊN MỚI THAM GIA
    # ==========================================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        channel_id, message_template, image_url, enabled = self.get_welcome_config(member.guild.id)

        if enabled == 0 or not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        embed = self.build_welcome_embed(member, message_template, image_url)

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))