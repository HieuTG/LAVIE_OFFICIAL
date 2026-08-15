import discord
from discord.ext import commands
from discord import app_commands
import os
from datetime import datetime
import database as db

class SettingsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="settings", description="Xem toàn bộ cấu hình hệ thống của Server (Logs, Ticket, Welcome...)")
    @app_commands.default_permissions(administrator=True)
    async def show_settings(self, interaction: discord.Interaction):
        guild = interaction.guild
        config = db.get_guild_config(guild.id)

        # Hàm trợ giúp hiển thị Kênh (Ưu tiên Database -> Fallback .env)
        def fmt_channel(db_key: str, env_key: str = None):
            ch_id = config.get(db_key)
            if not ch_id and env_key:
                env_val = os.getenv(env_key)
                ch_id = int(env_val) if env_val and env_val.isdigit() else None
            
            if ch_id:
                ch = guild.get_channel(ch_id)
                return ch.mention if ch else f"`⚠️ Đã xóa (ID: {ch_id})`"
            return "`❌ Chưa cài đặt`"

        # Hàm trợ giúp hiển thị Vai trò (Role)
        def fmt_role(db_key: str, env_key: str = None):
            r_id = config.get(db_key)
            if not r_id and env_key:
                env_val = os.getenv(env_key)
                r_id = int(env_val) if env_val and env_val.isdigit() else None
            
            if r_id:
                role = guild.get_role(r_id)
                return role.mention if role else f"`⚠️ Đã xóa (ID: {r_id})`"
            return "`❌ Chưa cài đặt`"

        embed = discord.Embed(
            title=f"⚙️ TỔNG QUAN CẤU HÌNH — {guild.name}",
            description="Dưới đây là trạng thái cài đặt tất cả các tính năng của Bot trên máy chủ:",
            color=discord.Color.blurple(),
            timestamp=datetime.now()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # 1. Hệ Thống Welcome / Goodbye
        welcome_info = (
            f"• **Kênh Chào Mừng:** {fmt_channel('welcome_channel_id', 'WELCOME_CHANNEL')}\n"
            f"• **Kênh Tạm Biệt:** {fmt_channel('goodbye_channel_id', 'GOODBYE_CHANNEL')}\n"
            f"• **Auto Role:** {fmt_role('auto_role_id', 'AUTO_ROLE')}"
        )
        embed.add_field(name="👋 Chào Mừng & Tạm Biệt", value=welcome_info, inline=False)

        # 2. Hệ Thống Ticket
        ticket_info = (
            f"• **Category Ticket:** {fmt_channel('ticket_category_id', 'GIVEAWAY_CATEGORY')}\n"
            f"• **Role Staff Hỗ Trợ:** {fmt_role('ticket_support_role_id', 'TICKET_SUPPORT')}\n"
            f"• **Kênh Log Ticket:** {fmt_channel('ticket_logs_id', 'TICKET_LOGS_CHANNEL')}"
        )
        embed.add_field(name="🎫 Hệ Thống Ticket", value=ticket_info, inline=False)

        # 3. Hệ Thống Nhật Ký (Logs)
        logs_info = (
            f"• **Server Logs:** {fmt_channel('server_logs_id', 'SERVER_LOGS')}\n"
            f"• **Member Logs:** {fmt_channel('member_logs_id', 'MEMBER_LOGS')}\n"
            f"• **Message Logs:** {fmt_channel('message_logs_id', 'MESSAGE_LOGS')}\n"
            f"• **Mod Logs:** {fmt_channel('mod_logs_id', 'MOD_LOGS')}"
        )
        embed.add_field(name="📜 Nhật Ký Máy Chủ (Logs)", value=logs_info, inline=False)

        embed.set_footer(text="Dùng /logs set hoặc các lệnh cài đặt riêng để thay đổi cấu hình.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(SettingsCog(bot))