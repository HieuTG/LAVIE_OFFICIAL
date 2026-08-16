import discord
from discord.ext import commands
from discord import app_commands
import os
import database as db

def is_staff():
    """Kiểm tra người dùng có sở hữu role trong ROLES_STAFF hay không"""
    async def predicate(ctx):
        roles_env = os.getenv("ROLES_STAFF", "")
        if not roles_env:
            await ctx.reply("❌ **Lỗi cấu hình:** Chưa thiết lập biến `ROLES_STAFF` trong file `.env`!", delete_after=10)
            return False
        
        staff_role_ids = [int(r.strip()) for r in roles_env.split(",") if r.strip().isdigit()]
        user_role_ids = [r.id for r in ctx.author.roles]
        
        if any(role_id in staff_role_ids for role_id in user_role_ids) or ctx.author.guild_permissions.administrator:
            return True
        else:
            await ctx.reply("⛔ Bạn không có quyền (Staff) để sử dụng lệnh này!", delete_after=10)
            return False
    return commands.check(predicate)

class AutoRoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==========================================
    # 1. LỆNH SLASH: /autorole <role> (CÀI ĐẶT NHANH ROLE)
    # ==========================================
    @app_commands.command(name="autorole", description="Cài đặt hoặc thay đổi Role gán nhanh cho Server")
    @app_commands.describe(role="Chọn Role muốn đặt làm Auto Role gán nhanh")
    @app_commands.default_permissions(administrator=True)
    async def set_autorole_slash(self, interaction: discord.Interaction, role: discord.Role):
        # Lưu ID Role vào SQLite Database
        db.set_server_setting(interaction.guild_id, "auto_role_id", role.id)

        embed = discord.Embed(
            title="✅ CẬP NHẬT AUTO ROLE THÀNH CÔNG",
            description=f"Đã thiết lập Role gán nhanh thành {role.mention}.\n\n💡 *Bây giờ bạn có thể dùng lệnh `!ar @User` để gán role này.*",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==========================================
    # 2. LỆNH PREFIX TRUYỀN THỐNG: !ar <@User> (GIỮ NGUYÊN)
    # ==========================================
    @commands.command(name="ar")
    @is_staff()
    async def auto_role_cmd(self, ctx, member: discord.Member = None):
        """Thêm nhanh role cấu hình cho thành viên"""
        # 1. Kiểm tra tham số nhập vào
        if not member:
            return await ctx.reply(
                "❌ **Sai cú pháp!**\n"
                "👉 **Hướng dẫn:** `!ar <@User>`\n"
                "💡 **Ví dụ:** `!ar @HieuTG`"
            )

        # 2. Lấy ID Role: Ưu tiên Database trước -> Dự phòng file .env
        config = db.get_guild_config(ctx.guild.id)
        auto_role_id = config.get("auto_role_id")

        if not auto_role_id:
            env_val = os.getenv("AUTO_ROLE")
            auto_role_id = int(env_val) if env_val and env_val.isdigit() else None

        if not auto_role_id:
            return await ctx.reply("❌ **Chưa cài đặt Role!** Dùng lệnh Slash `/autorole <role>` hoặc thiết lập `AUTO_ROLE` trong `.env` trước.")

        # 3. Lấy đối tượng Role từ server
        role = ctx.guild.get_role(auto_role_id)
        if not role:
            return await ctx.reply("❌ **Không tìm thấy Role!** Role đã cài đặt không còn tồn tại trên máy chủ này.")

        # 4. Kiểm tra thành viên đã có role chưa
        if role in member.roles:
            return await ctx.reply(f"⚠️ Thành viên {member.mention} đã có role {role.mention} từ trước rồi!")

        # 5. Tiến hành cấp Role
        try:
            await member.add_roles(role, reason=f"Được thêm bởi {ctx.author}")
            await ctx.reply(f"✅ Đã thêm thành công role ``ngoan xinh iu`` cho {member.mention}!")
        except discord.Forbidden:
            await ctx.reply("❌ **Thiếu quyền!** Vị trí Role của Bot trong Cài đặt máy chủ đang thấp hơn Role cần cấp.")
        except Exception as e:
            await ctx.reply(f"❌ **Đã xảy ra lỗi:** {e}")

async def setup(bot):
    await bot.add_cog(AutoRoleCog(bot))