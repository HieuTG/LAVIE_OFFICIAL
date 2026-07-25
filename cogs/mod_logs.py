import discord
from discord.ext import commands
import os
import asyncio
from datetime import datetime, timezone

class ModLogsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_log_channel(self, guild: discord.Guild):
        """Hàm hỗ trợ lấy kênh logs từ biến môi trường"""
        log_channel_env = os.getenv("MOD_LOGS")
        if not log_channel_env:
            return None
            
        try:
            channel_id = int(log_channel_env)
            return guild.get_channel(channel_id)
        except ValueError:
            print("⚠️ [Warning] MOD_LOGS trong .env không phải là ID chữ số hợp lệ!")
            return None

    async def get_audit_entry(self, guild: discord.Guild, action: discord.AuditLogAction, target_id: int):
        """Hàm hỗ trợ tra cứu Audit Log để tìm ra Mod thực hiện hành động"""
        # Chờ 1 giây để đảm bảo Discord đã ghi nhận Audit Log
        await asyncio.sleep(1)
        try:
            async for entry in guild.audit_logs(action=action, limit=5):
                if entry.target and entry.target.id == target_id:
                    # Kiểm tra hành động vừa diễn ra trong vòng 15 giây
                    if (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 15:
                        return entry
        except discord.Forbidden:
            pass
        return None

    # ==========================================
    # 1. THEO DÕI BAN (CẤM THÀNH VIÊN)
    # ==========================================
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        log_channel = self.get_log_channel(guild)
        if not log_channel:
            return

        entry = await self.get_audit_entry(guild, discord.AuditLogAction.ban, user.id)
        moderator = entry.user.mention if entry and entry.user else "*[Không xác định - Thiếu quyền Audit Log]*"
        reason = entry.reason if entry and entry.reason else "Không có lý do được ghi nhận."

        embed = discord.Embed(
            title="🔨 LỆNH CẤM (BAN)",
            description=f"**{user.mention}** (`{user.name}`) đã bị cấm khỏi máy chủ.",
            color=0x992d22, # Màu đỏ đậm
            timestamp=datetime.now()
        )
        embed.set_author(name=f"{user.display_name} ({user.id})", icon_url=user.display_avatar.url if user.display_avatar else None)
        embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
        embed.add_field(name="👮 Người thực hiện", value=moderator, inline=True)
        embed.add_field(name="📝 Lý do", value=f"```{reason}```", inline=False)
        embed.set_footer(text=f"ID Thành viên: {user.id}")

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    # ==========================================
    # 2. THEO DÕI UNBAN (GỠ CẤM THÀNH VIÊN)
    # ==========================================
    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        log_channel = self.get_log_channel(guild)
        if not log_channel:
            return

        entry = await self.get_audit_entry(guild, discord.AuditLogAction.unban, user.id)
        moderator = entry.user.mention if entry and entry.user else "*[Không xác định]*"
        reason = entry.reason if entry and entry.reason else "Không có lý do được ghi nhận."

        embed = discord.Embed(
            title="🕊️ GỠ CẤM (UNBAN)",
            description=f"**{user.mention}** (`{user.name}`) đã được gỡ lệnh cấm.",
            color=0x1abc9c, # Màu xanh ngọc
            timestamp=datetime.now()
        )
        embed.set_author(name=f"{user.display_name} ({user.id})", icon_url=user.display_avatar.url if user.display_avatar else None)
        embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
        embed.add_field(name="👮 Người thực hiện", value=moderator, inline=True)
        embed.add_field(name="📝 Lý do", value=f"```{reason}```", inline=False)
        embed.set_footer(text=f"ID Thành viên: {user.id}")

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    # ==========================================
    # 3. THEO DÕI KICK (ĐUỔI KHỎI SERVER)
    # ==========================================
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        log_channel = self.get_log_channel(member.guild)
        if not log_channel:
            return

        # Khi member rời server, tra cứu Audit Log xem có phải bị Kick không
        entry = await self.get_audit_entry(member.guild, discord.AuditLogAction.kick, member.id)
        
        # Nếu không có log kick, nghĩa là họ tự rời đi (đã được log bên member_logs) -> Bỏ qua
        if not entry:
            return

        moderator = entry.user.mention if entry.user else "*[Không xác định]*"
        reason = entry.reason if entry.reason else "Không có lý do được ghi nhận."

        embed = discord.Embed(
            title="👢 ĐUỔI THÀNH VIÊN (KICK)",
            description=f"**{member.mention}** (`{member.name}`) đã bị trục xuất khỏi máy chủ.",
            color=0xe67e22, # Màu cam
            timestamp=datetime.now()
        )
        embed.set_author(name=f"{member.display_name} ({member.id})", icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👮 Người thực hiện", value=moderator, inline=True)
        embed.add_field(name="📝 Lý do", value=f"```{reason}```", inline=False)
        embed.set_footer(text=f"ID Thành viên: {member.id}")

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    # ==========================================
    # 4. THEO DÕI TIMEOUT & UN-TIMEOUT (CẤM NGÔN)
    # ==========================================
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Chỉ kiểm tra nếu trạng thái Timeout có sự thay đổi
        if before.timed_out_until == after.timed_out_until:
            return

        log_channel = self.get_log_channel(after.guild)
        if not log_channel:
            return

        entry = await self.get_audit_entry(after.guild, discord.AuditLogAction.member_update, after.id)
        moderator = entry.user.mention if entry and entry.user else "*[Không xác định]*"
        reason = entry.reason if entry and entry.reason else "Không có lý do được ghi nhận."

        embed = discord.Embed(timestamp=datetime.now())
        embed.set_author(name=f"{after.display_name} ({after.id})", icon_url=after.display_avatar.url)
        embed.set_thumbnail(url=after.display_avatar.url)
        embed.set_footer(text=f"ID Thành viên: {after.id}")

        if after.is_timed_out():
            # Bị Timeout
            timeout_end = int(after.timed_out_until.timestamp())
            embed.title = "🔇 CẤM NGÔN (TIMEOUT)"
            embed.color = 0xf1c40f # Màu vàng
            embed.description = f"**{after.mention}** đã bị cấm ngôn."
            embed.add_field(name="👮 Người thực hiện", value=moderator, inline=True)
            embed.add_field(name="⏰ Hết hạn vào", value=f"<t:{timeout_end}:f> (<t:{timeout_end}:R>)", inline=True)
            embed.add_field(name="📝 Lý do", value=f"```{reason}```", inline=False)
        else:
            # Được gỡ Timeout trước thời hạn
            embed.title = "🔊 GỠ CẤM NGÔN (UN-TIMEOUT)"
            embed.color = 0x2ecc71 # Màu xanh lá
            embed.description = f"**{after.mention}** đã được gỡ lệnh cấm ngôn sớm."
            embed.add_field(name="👮 Người thực hiện", value=moderator, inline=True)
            embed.add_field(name="📝 Lý do", value=f"```{reason}```", inline=False)

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

async def setup(bot):
    await bot.add_cog(ModLogsCog(bot))