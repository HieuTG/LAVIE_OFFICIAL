import discord
from discord.ext import commands
import os

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

    @commands.command(name="ar")
    @is_staff()
    async def auto_role_cmd(self, ctx, member: discord.Member = None):
        """Thêm nhanh role cấu hình trong AUTO_ROLE cho thành viên"""
        # 1. Kiểm tra tham số nhập vào
        if not member:
            return await ctx.reply(
                "❌ **Sai cú pháp!**\n"
                "👉 **Hướng dẫn:** `!ar <@User>`\n"
                "💡 **Ví dụ:** `!ar @HieuTG`"
            )

        # 2. Đọc ID Role từ biến môi trường
        auto_role_id = os.getenv("AUTO_ROLE")
        if not auto_role_id or not auto_role_id.isdigit():
            return await ctx.reply("❌ **Lỗi cấu hình:** Chưa thiết lập hoặc ID biến `AUTO_ROLE` không hợp lệ trong file `.env`!")

        # 3. Lấy đối tượng Role từ server
        role = ctx.guild.get_role(int(auto_role_id))
        if not role:
            return await ctx.reply("❌ **Không tìm thấy Role!** ID trong `AUTO_ROLE` không tồn tại trên máy chủ này.")

        # 4. Kiểm tra thành viên đã có role chưa
        if role in member.roles:
            return await ctx.reply(f"⚠️ Thành viên {member.mention} đã có role `ngoan xinh iu` từ trước rồi!")

        # 5. Tiến hành cấp Role
        try:
            await member.add_roles(role, reason=f"Được thêm bởi {ctx.author}")
            await ctx.reply(f"✅ Đã thêm thành công role `ngoan xinh iu` cho {member.mention}!")
        except discord.Forbidden:
            await ctx.reply("❌ **Thiếu quyền!** Vị trí Role của Bot trong Cài đặt máy chủ đang thấp hơn Role cần cấp.")
        except Exception as e:
            await ctx.reply(f"❌ **Đã xảy ra lỗi:** {e}")

async def setup(bot):
    await bot.add_cog(AutoRoleCog(bot))