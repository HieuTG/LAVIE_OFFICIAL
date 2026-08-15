import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from datetime import datetime, timezone
import database as db

class ServerLogsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_log_channel(self, guild: discord.Guild, log_key: str = "server_logs_id", env_key: str = "SERVER_LOGS"):
        """Lấy kênh log từ DB, nếu không có sẽ lấy từ file .env"""
        config = db.get_guild_config(guild.id)
        channel_id = config.get(log_key)

        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                return channel

        log_channel_env = os.getenv(env_key)
        if log_channel_env and log_channel_env.isdigit():
            return guild.get_channel(int(log_channel_env))

        return None

    def is_ignored(self, channel):
        """Kiểm tra ngoại lệ EXCEPT_CHANNEL"""
        except_env = os.getenv("EXCEPT_CHANNEL", "")
        if not except_env:
            return False
        
        ignored_items = [item.strip() for item in except_env.split(",") if item.strip()]
        for item in ignored_items:
            if item.isdigit():
                if str(channel.id) == item or (getattr(channel, "category_id", None) and str(channel.category_id) == item):
                    return True
            elif channel.name.lower().startswith(item.lower()):
                return True
        return False

    async def get_audit_entry(self, guild: discord.Guild, action: discord.AuditLogAction, target_id: int):
        await asyncio.sleep(1)
        try:
            async for entry in guild.audit_logs(action=action, limit=5):
                if entry.target and entry.target.id == target_id:
                    if (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 15:
                        return entry
        except discord.Forbidden:
            pass
        return None

    # Lệnh cài đặt kênh Log
    logs_group = app_commands.Group(name="logs", description="Quản lý cài đặt Nhật ký (Logs)")

    @logs_group.command(name="set", description="Cài đặt kênh nhận Nhật ký (Logs)")
    @app_commands.describe(
        log_type="Chọn loại nhật ký cần thiết lập",
        channel="Kênh văn bản muốn nhận log"
    )
    @app_commands.choices(log_type=[
        app_commands.Choice(name="Server Logs (Kênh, Role)", value="server_logs_id"),
        app_commands.Choice(name="Member Logs (Join/Leave)", value="member_logs_id"),
        app_commands.Choice(name="Message Logs (Sửa/Xóa tin)", value="message_logs_id"),
        app_commands.Choice(name="Mod Logs (Ban/Kick/Timeout)", value="mod_logs_id"),
        app_commands.Choice(name="Ticket Logs (Đóng/Mở ticket)", value="ticket_logs_id"),
    ])
    @app_commands.default_permissions(administrator=True)
    async def set_log_channel_cmd(self, interaction: discord.Interaction, log_type: app_commands.Choice[str], channel: discord.TextChannel):
        db.set_server_setting(interaction.guild_id, log_type.value, channel.id)
        embed = discord.Embed(
            title="✅ CẬP NHẬT CẤU HÌNH THÀNH CÔNG",
            description=f"Đã gán **{log_type.name}** vào kênh {channel.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- CÁC EVENT LOGS (Giữ nguyên logic cũ của bạn) ---
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if self.is_ignored(channel):
            return
        log_channel = self.get_log_channel(channel.guild, "server_logs_id", "SERVER_LOGS")
        if not log_channel or channel.id == log_channel.id:
            return

        entry = await self.get_audit_entry(channel.guild, discord.AuditLogAction.channel_create, channel.id)
        creator = entry.user.mention if entry and entry.user else "*[Không xác định]*"

        embed = discord.Embed(
            title="🆕 KÊNH MỚI ĐƯỢC TẠO",
            description=f"Kênh **{channel.name}** vừa được tạo trên máy chủ.",
            color=0x2ecc71,
            timestamp=datetime.now()
        )
        embed.add_field(name="📁 Tên kênh", value=channel.mention if isinstance(channel, discord.TextChannel) else f"`{channel.name}`", inline=True)
        embed.add_field(name="📌 Loại kênh", value=f"`{str(channel.type).capitalize()}`", inline=True)
        embed.add_field(name="👮 Người tạo", value=creator, inline=False)
        embed.set_footer(text=f"ID Kênh: {channel.id}")

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if self.is_ignored(channel):
            return
        log_channel = self.get_log_channel(channel.guild, "server_logs_id", "SERVER_LOGS")
        if not log_channel or channel.id == log_channel.id:
            return

        entry = await self.get_audit_entry(channel.guild, discord.AuditLogAction.channel_delete, channel.id)
        deleter = entry.user.mention if entry and entry.user else "*[Không xác định]*"

        embed = discord.Embed(
            title="🗑️ KÊNH BỊ XÓA",
            description=f"Kênh **#{channel.name}** đã bị xóa khỏi máy chủ.",
            color=0xe74c3c,
            timestamp=datetime.now()
        )
        embed.add_field(name="📁 Tên kênh bị xóa", value=f"`#{channel.name}`", inline=True)
        embed.add_field(name="📌 Loại kênh", value=f"`{str(channel.type).capitalize()}`", inline=True)
        embed.add_field(name="👮 Người xóa", value=deleter, inline=False)
        embed.set_footer(text=f"ID Kênh: {channel.id}")

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

async def setup(bot):
    await bot.add_cog(ServerLogsCog(bot))