import discord
from discord.ext import commands
import os
from datetime import datetime

class MemberLogsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_log_channel(self, guild: discord.Guild):
        """Hàm hỗ trợ lấy kênh logs từ biến môi trường"""
        log_channel_env = os.getenv("MEMBER_LOGS")
        if not log_channel_env:
            return None
            
        try:
            channel_id = int(log_channel_env)
            return guild.get_channel(channel_id)
        except ValueError:
            print("⚠️ [Warning] MEMBER_LOGS trong .env không phải là ID chữ số hợp lệ!")
            return None

    # ==========================================
    # 1. THEO DÕI THÀNH VIÊN THAM GIA (JOIN)
    # ==========================================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        log_channel = self.get_log_channel(member.guild)
        if not log_channel:
            return

        created_ts = int(member.created_at.timestamp())
        
        embed = discord.Embed(
            title="📥 THÀNH VIÊN MỚI THAM GIA",
            description=f"**{member.mention}** (`{member.name}`) đã gia nhập máy chủ.",
            color=0x2ecc71, # Màu xanh lá
            timestamp=datetime.now()
        )
        embed.set_author(name=f"{member.display_name} ({member.id})", icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="📅 Ngày tạo tài khoản", value=f"<t:{created_ts}:f> (<t:{created_ts}:R>)", inline=False)
        embed.add_field(name="👥 Tổng thành viên hiện tại", value=f"`{member.guild.member_count}` người", inline=False)
        embed.set_footer(text=f"ID Thành viên: {member.id}")

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    # ==========================================
    # 2. THEO DÕI THÀNH VIÊN RỜI ĐI (LEAVE)
    # ==========================================
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        log_channel = self.get_log_channel(member.guild)
        if not log_channel:
            return

        # Tính toán thời gian thành viên đã ở trong server trước khi rời đi
        joined_str = "Không xác định"
        if member.joined_at:
            joined_ts = int(member.joined_at.timestamp())
            joined_str = f"<t:{joined_ts}:f> (<t:{joined_ts}:R>)"

        embed = discord.Embed(
            title="📤 THÀNH VIÊN RỜI MÁY CHỦ",
            description=f"**{member.mention}** (`{member.name}`) đã rời khỏi hoặc bị đuổi khỏi máy chủ.",
            color=0xe74c3c, # Màu đỏ
            timestamp=datetime.now()
        )
        embed.set_author(name=f"{member.display_name} ({member.id})", icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🕒 Thời gian gia nhập trước đó", value=joined_str, inline=False)
        embed.add_field(name="👥 Tổng thành viên còn lại", value=f"`{member.guild.member_count}` người", inline=False)
        embed.set_footer(text=f"ID Thành viên: {member.id}")

        try:
            await log_channel.send(embed=embed)
        except discord.Forbidden:
            pass

    # ==========================================
    # 3. THEO DÕI ĐỔI BIỆT DANH & CẬP NHẬT ROLE
    # ==========================================
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        log_channel = self.get_log_channel(after.guild)
        if not log_channel:
            return

        # --- A. ĐỔI BIỆT DANH (NICKNAME) ---
        if before.nick != after.nick:
            before_nick = before.nick if before.nick else "*[Không có - Dùng tên gốc]*"
            after_nick = after.nick if after.nick else "*[Đã xóa - Dùng tên gốc]*"

            embed = discord.Embed(
                title="📝 THAY ĐỔI BIỆT DANH",
                description=f"**{after.mention}** đã thay đổi biệt danh trên server.",
                color=0x3498db, # Màu xanh dương
                timestamp=datetime.now()
            )
            embed.set_author(name=f"{after.display_name} ({after.id})", icon_url=after.display_avatar.url)
            embed.add_field(name="🔴 Biệt danh cũ", value=f"`{before_nick}`", inline=True)
            embed.add_field(name="🟢 Biệt danh mới", value=f"`{after_nick}`", inline=True)
            embed.set_footer(text=f"ID Thành viên: {after.id}")

            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass

        # --- B. CẬP NHẬT VAI TRÒ (ROLES) ---
        if before.roles != after.roles:
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]

            if added_roles or removed_roles:
                embed = discord.Embed(
                    title="🛡️ CẬP NHẬT VAI TRÒ (ROLE)",
                    description=f"Thành viên **{after.mention}** vừa có sự thay đổi về Role.",
                    color=0x9b59b6, # Màu tím
                    timestamp=datetime.now()
                )
                embed.set_author(name=f"{after.display_name} ({after.id})", icon_url=after.display_avatar.url)

                if added_roles:
                    roles_str = " ".join([r.mention for r in added_roles])
                    embed.add_field(name="➕ Role được thêm", value=roles_str, inline=False)
                    
                if removed_roles:
                    roles_str = " ".join([r.mention for r in removed_roles])
                    embed.add_field(name="➖ Role bị gỡ bỏ", value=roles_str, inline=False)

                embed.set_footer(text=f"ID Thành viên: {after.id}")

                try:
                    await log_channel.send(embed=embed)
                except discord.Forbidden:
                    pass

async def setup(bot):
    await bot.add_cog(MemberLogsCog(bot))