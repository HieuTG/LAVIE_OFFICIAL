import discord
from discord.ext import commands
import os
import asyncio
from datetime import datetime, timezone

class ServerLogsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_log_channel(self, guild: discord.Guild):
        """Hàm hỗ trợ lấy kênh logs từ biến môi trường"""
        log_channel_env = os.getenv("SERVER_LOGS")
        if not log_channel_env:
            return None
            
        try:
            channel_id = int(log_channel_env)
            return guild.get_channel(channel_id)
        except ValueError:
            print("⚠️ [Warning] SERVER_LOGS trong .env không phải là ID chữ số hợp lệ!")
            return None

    def is_ignored(self, channel):
        """Kiểm tra xem kênh có nằm trong danh sách ngoại lệ EXCEPT_CHANNEL hay không"""
        except_env = os.getenv("EXCEPT_CHANNEL", "")
        if not except_env:
            return False
        
        ignored_items = [item.strip() for item in except_env.split(",") if item.strip()]
        for item in ignored_items:
            # 1. Kiểm tra theo ID kênh hoặc ID danh mục (Category ID)
            if item.isdigit():
                if str(channel.id) == item or (getattr(channel, "category_id", None) and str(channel.category_id) == item):
                    return True
            # 2. Kiểm tra theo tiền tố tên kênh (ví dụ: "góp-ý-", "hỗ-trợ-")
            elif channel.name.lower().startswith(item.lower()):
                return True
        return False

    async def get_audit_entry(self, guild: discord.Guild, action: discord.AuditLogAction, target_id: int):
        """Tra cứu Audit Log để tìm người thực hiện hành động"""
        await asyncio.sleep(1) # Chờ Discord cập nhật nhật ký kiểm toán
        try:
            async for entry in guild.audit_logs(action=action, limit=5):
                if entry.target and entry.target.id == target_id:
                    if (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 15:
                        return entry
        except discord.Forbidden:
            pass
        return None

    # ==========================================
    # 1. THEO DÕI TẠO KÊNH MỚI
    # ==========================================
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if self.is_ignored(channel):
            return

        log_channel = self.get_log_channel(channel.guild)
        if not log_channel or channel.id == log_channel.id:
            return

        entry = await self.get_audit_entry(channel.guild, discord.AuditLogAction.channel_create, channel.id)
        creator = entry.user.mention if entry and entry.user else "*[Không xác định]*"

        embed = discord.Embed(
            title="🆕 KÊNH MỚI ĐƯỢC TẠO",
            description=f"Kênh **{channel.name}** vừa được tạo trên máy chủ.",
            color=0x2ecc71, # Màu xanh lá
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

    # ==========================================
    # 2. THEO DÕI XÓA KÊNH
    # ==========================================
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if self.is_ignored(channel):
            return

        log_channel = self.get_log_channel(channel.guild)
        if not log_channel or channel.id == log_channel.id:
            return

        entry = await self.get_audit_entry(channel.guild, discord.AuditLogAction.channel_delete, channel.id)
        deleter = entry.user.mention if entry and entry.user else "*[Không xác định]*"

        embed = discord.Embed(
            title="🗑️ KÊNH BỊ XÓA",
            description=f"Kênh **#{channel.name}** đã bị xóa khỏi máy chủ.",
            color=0xe74c3c, # Màu đỏ
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

    # ==========================================
    # 3. THEO DÕI ĐỔI TÊN KÊNH
    # ==========================================
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        if self.is_ignored(after) or before.name == after.name:
            return

        log_channel = self.get_log_channel(after.guild)
        if not log_channel or after.id == log_channel.id:
            return

        entry = await self.get_audit_entry(after.guild, discord.AuditLogAction.channel_update, after.id)
        updater = entry.user.mention if entry and entry.user else "*[Không xác định]*"

        embed = discord.Embed(
            title="✏️ KÊNH ĐƯỢC ĐỔI TÊN",
            description=f"Kênh {after.mention} vừa được thay đổi tên.",
            color=0xf39c12, # Màu cam vàng
            timestamp=datetime.now()
        )
        embed.add_field(name="🔴 Tên cũ", value=f"`{before.name}`", inline=True)
        embed.add_field(name="🟢 Tên mới", value=f"`{after.name}`", inline=True)
        embed.add_field(name="👮 Người thực hiện", value=updater, inline=False)
        embed.set_footer(text=f"ID Kênh: {after.id}")

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    # ==========================================
    # 4. THEO DÕI TẠO ROLE MỚI
    # ==========================================
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        log_channel = self.get_log_channel(role.guild)
        if not log_channel:
            return

        entry = await self.get_audit_entry(role.guild, discord.AuditLogAction.role_create, role.id)
        creator = entry.user.mention if entry and entry.user else "*[Không xác định]*"

        embed = discord.Embed(
            title="🛡️ VAI TRÒ (ROLE) MỚI ĐƯỢC TẠO",
            description=f"Role **{role.name}** vừa được tạo trên máy chủ.",
            color=0x3498db, # Màu xanh dương
            timestamp=datetime.now()
        )
        embed.add_field(name="🏷️ Role", value=role.mention, inline=True)
        embed.add_field(name="👮 Người tạo", value=creator, inline=True)
        embed.set_footer(text=f"ID Role: {role.id}")

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    # ==========================================
    # 5. THEO DÕI XÓA ROLE
    # ==========================================
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        log_channel = self.get_log_channel(role.guild)
        if not log_channel:
            return

        entry = await self.get_audit_entry(role.guild, discord.AuditLogAction.role_delete, role.id)
        deleter = entry.user.mention if entry and entry.user else "*[Không xác định]*"

        embed = discord.Embed(
            title="🗑️ VAI TRÒ (ROLE) BỊ XÓA",
            description=f"Role **@{role.name}** đã bị xóa khỏi máy chủ.",
            color=0x9b59b6, # Màu tím
            timestamp=datetime.now()
        )
        embed.add_field(name="🏷️ Tên Role bị xóa", value=f"`@{role.name}`", inline=True)
        embed.add_field(name="👮 Người xóa", value=deleter, inline=True)
        embed.set_footer(text=f"ID Role: {role.id}")

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

async def setup(bot):
    await bot.add_cog(ServerLogsCog(bot))