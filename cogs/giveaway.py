import discord
from discord.ext import commands, tasks
import sqlite3
import os
import time
import random
import asyncio

# ==========================================
# 0. HÀM KIỂM TRA QUYỀN STAFF & XỬ LÝ THỜI GIAN
# ==========================================
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

def parse_duration(time_str: str) -> int:
    """Chuyển đổi chuỗi thời gian như '30s', '10m', '2h', '1d' thành giây"""
    time_str = time_str.lower().strip()
    unit = time_str[-1]
    val_str = time_str[:-1]
    
    if not val_str.isdigit():
        raise ValueError("Định dạng thời gian không hợp lệ")
        
    val = int(val_str)
    if unit == 's':
        return val
    elif unit == 'm':
        return val * 60
    elif unit == 'h':
        return val * 3600
    elif unit == 'd':
        return val * 86400
    else:
        if time_str.isdigit():
            return int(time_str) * 60
        raise ValueError("Đơn vị thời gian không hợp lệ (dùng s, m, h, d)")


# ==========================================
# 1. GIAO DIỆN GIVEAWAY COMPONENT V2
# ==========================================
class GiveawayView(discord.ui.LayoutView):
    def __init__(self, prize: str, end_time: int, host_id: int, required_role_id: int = None, count: int = 0, ended: bool = False, winner_text: str = None):
        super().__init__(timeout=None)
        self.prize = prize
        self.end_time = end_time
        self.host_id = host_id
        self.required_role_id = required_role_id
        self.count = count
        self.ended = ended
        self.winner_text = winner_text
        
        self.build_view()

    def build_view(self):
        self.clear_items()
        
        end_str = f"<t:{self.end_time}:R> (<t:{self.end_time}:f>)"
        role_req_str = f"<@&{self.required_role_id}>" if self.required_role_id else "Tất cả mọi người"
        host_str = f"<@{self.host_id}>"
        
        if not self.ended:
            header_text = "# <a:event:1530563975828209664> GIVEAWAY <a:event:1530563975828209664>"
            status_text = (
                f"### <:holiday_crate:1523749995059216494> **Phần thưởng:** `{self.prize}`\n\n"
                f"• **Người tạo:** {host_str}\n"
                f"• **Kết thúc:** {end_str}\n"
                f"• **Yêu cầu Role:** {role_req_str}\n"
                f"• **Số người tham gia:** `{self.count}` người\n\n"
                f"-# Bấm nút bên dưới để tham gia (Bấm lần nữa để rời khỏi)"
            )
            btn_label = f"Tham gia ({self.count})"
            btn_style = discord.ButtonStyle.success
            btn_disabled = False
        else:
            header_text = "# <a:event:1530563975828209664> GIVEAWAY ĐÃ KẾT THÚC <a:event:1530563975828209664>"
            status_text = (
                f"### <:holiday_crate:1523749995059216494> **Phần thưởng:** `{self.prize}`\n\n"
                f"• **Người tạo:** {host_str}\n"
                f"• **Người thắng cuộc:** {self.winner_text}\n"
                f"• **Tổng người tham gia:** `{self.count}` người\n"
                f"• **Đã kết thúc lúc:** <t:{self.end_time}:f>"
            )
            btn_label = "Đã kết thúc"
            btn_style = discord.ButtonStyle.secondary
            btn_disabled = True

        container = discord.ui.Container(
            discord.ui.TextDisplay(content=header_text),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=status_text),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(
                discord.ui.Button(
                    style=btn_style,
                    label=btn_label,
                    emoji="<a:tada_right:1523846292105724035>",
                    disabled=btn_disabled,
                    custom_id="ga_button_join"  # Dùng ID tĩnh để tránh lỗi mất nút
                )
            ),
            discord.ui.TextDisplay(content="-# <:Lavie:1531334063816839298> <:Lavie2:1531334114714714366> <:Lavie3:1531334146650148977> <:Lavie4:1531334188219891872> <:Lavie5:1531334235494027364> • Giveaway System")
        )
        self.add_item(container)


# ==========================================
# 2. MODULE COG CHÍNH (GIVEAWAY & NUKE)
# ==========================================
class GiveawayNukeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "giveaway.db"
        self.init_db()
        self.check_giveaway_task.start()

    def init_db(self):
        """Khởi tạo file cơ sở dữ liệu cho Giveaway và tự động cập nhật cột host_id nếu chưa có"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS giveaways (
                message_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                host_id INTEGER NOT NULL,
                prize TEXT NOT NULL,
                end_time INTEGER NOT NULL,
                required_role_id INTEGER,
                ended INTEGER DEFAULT 0
            )
        """)
        # Kiểm tra và thêm cột host_id cho database cũ (nếu có)
        try:
            cursor.execute("ALTER TABLE giveaways ADD COLUMN host_id INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
            
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ga_participants (
                message_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (message_id, user_id)
            )
        """)
        conn.commit()
        conn.close()

    def get_participant_count(self, message_id: int) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ga_participants WHERE message_id = ?", (message_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    # --- LỆNH !GIVEAWAY (!GA) ---
    @commands.command(name="giveaway", aliases=["ga"])
    @is_staff()
    async def create_giveaway(self, ctx):
        """Tạo Giveaway mới: !ga <phần thưởng> <thời gian> [-r <role>]"""
        content = ctx.message.content
        parts = content.split(" ", 1)
        
        if len(parts) < 2:
            return await ctx.reply(
                "❌ **Sai cú pháp!**\n"
                "👉 **Hướng dẫn:** `!ga <Phần thưởng> <Thời gian> [-r <@Role>]`\n"
                "💡 **Ví dụ:**\n"
                "• `!ga Nitro Boost 1 tháng 24h` *(Mọi người đều được tham gia, kết thúc sau 24 giờ)*\n"
                "• `!ga 100k VND 30m -r @VIP` *(Chỉ role @VIP được tham gia, kết thúc sau 30 phút)*"
            )

        args_str = parts[1].strip()
        required_role = None

        if "-r" in args_str:
            main_part, role_part = args_str.split("-r", 1)
            role_id_str = ''.join(filter(str.isdigit, role_part))
            if role_id_str:
                required_role = ctx.guild.get_role(int(role_id_str))
            if not required_role:
                return await ctx.reply("❌ **Không tìm thấy Role yêu cầu!** Hãy tag đúng role sau cờ `-r`.")
        else:
            main_part = args_str

        tokens = main_part.strip().rsplit(" ", 1)
        if len(tokens) < 2:
            return await ctx.reply("❌ **Thiếu thông tin!** Vui lòng nhập đủ **Phần thưởng** và **Thời gian** (Ví dụ: `10m`, `2h`, `1d`).")

        prize = tokens[0].strip()
        time_str = tokens[1].strip()

        try:
            duration = parse_duration(time_str)
            if duration < 10:
                return await ctx.reply("❌ Thời gian Giveaway tối thiểu phải từ **10 giây** trở lên!")
        except ValueError:
            return await ctx.reply("❌ **Định dạng thời gian không hợp lệ!**\n👉 Dùng các đuôi `s` (giây), `m` (phút), `h` (giờ), `d` (ngày). Ví dụ: `30m`, `2h`, `1d`.")

        end_time = int(time.time()) + duration
        req_role_id = required_role.id if required_role else None
        host_id = ctx.author.id

        view = GiveawayView(prize=prize, end_time=end_time, host_id=host_id, required_role_id=req_role_id, count=0)
        ga_msg = await ctx.send(view=view)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO giveaways (message_id, channel_id, guild_id, host_id, prize, end_time, required_role_id, ended)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """, (ga_msg.id, ctx.channel.id, ctx.guild.id, host_id, prize, end_time, req_role_id))
        conn.commit()
        conn.close()

        try:
            await ctx.message.delete()
        except:
            pass

    # --- SỰ KIỆN BẤM NÚT THAM GIA / RỜI GIVEAWAY (FIX LỖI NÚT) ---
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.type == discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get("custom_id", "")
        if custom_id != "ga_button_join":
            return

        message_id = interaction.message.id

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT prize, end_time, host_id, required_role_id, ended FROM giveaways WHERE message_id = ?", (message_id,))
        ga_row = cursor.fetchone()

        if not ga_row or ga_row[4] == 1:
            conn.close()
            return await interaction.response.send_message("❌ Giveaway này đã kết thúc hoặc không tồn tại!", ephemeral=True)

        prize, end_time, host_id, required_role_id, _ = ga_row

        if required_role_id:
            role = interaction.guild.get_role(required_role_id)
            if role and role not in interaction.user.roles:
                conn.close()
                return await interaction.response.send_message(
                    f"⛔ Bạn cần sở hữu role {role.mention} mới có thể tham gia Giveaway này!",
                    ephemeral=True
                )

        cursor.execute("SELECT 1 FROM ga_participants WHERE message_id = ? AND user_id = ?", (message_id, interaction.user.id))
        exists = cursor.fetchone()

        if exists:
            cursor.execute("DELETE FROM ga_participants WHERE message_id = ? AND user_id = ?", (message_id, interaction.user.id))
            conn.commit()
            count = self.get_participant_count(message_id)
            conn.close()

            view = GiveawayView(prize=prize, end_time=end_time, host_id=host_id, required_role_id=required_role_id, count=count)
            try:
                await interaction.message.edit(view=view)
            except:
                pass

            await interaction.response.send_message("❌ **Bạn đã rời khỏi Giveaway!** (Bấm nút lần nữa nếu muốn đổi ý)", ephemeral=True)
        else:
            cursor.execute("INSERT INTO ga_participants (message_id, user_id) VALUES (?, ?)", (message_id, interaction.user.id))
            conn.commit()
            count = self.get_participant_count(message_id)
            conn.close()

            view = GiveawayView(prize=prize, end_time=end_time, host_id=host_id, required_role_id=required_role_id, count=count)
            try:
                await interaction.message.edit(view=view)
            except:
                pass

            await interaction.response.send_message("🎉 **Bạn đã tham gia Giveaway thành công!** Chúc bạn may mắn!", ephemeral=True)

    # --- TASK TỰ ĐỘNG KIỂM TRA GIVEAWAY HẾT HẠN & QUAY THƯỞNG ---
    @tasks.loop(seconds=15)
    async def check_giveaway_task(self):
        await self.bot.wait_until_ready()
        now = int(time.time())

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT message_id, channel_id, guild_id, host_id, prize, end_time, required_role_id FROM giveaways WHERE ended = 0 AND end_time <= ?", (now,))
        expired_giveaways = cursor.fetchall()

        for msg_id, channel_id, guild_id, host_id, prize, end_time, req_role_id in expired_giveaways:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
            channel = guild.get_channel(channel_id)
            if not channel:
                continue

            cursor.execute("SELECT user_id FROM ga_participants WHERE message_id = ?", (msg_id,))
            participants = [row[0] for row in cursor.fetchall()]
            count = len(participants)

            if count == 0:
                winner_text = "Không có ai tham gia"
            else:
                winner_id = random.choice(participants)
                winner_text = f"<@{winner_id}>"

            cursor.execute("UPDATE giveaways SET ended = 1 WHERE message_id = ?", (msg_id,))
            conn.commit()

            msg = None
            try:
                msg = await channel.fetch_message(msg_id)
                view = GiveawayView(
                    prize=prize, end_time=end_time, host_id=host_id,
                    required_role_id=req_role_id, count=count, ended=True,
                    winner_text=winner_text
                )
                await msg.edit(view=view)
            except:
                pass

            # Gửi tin nhắn văn bản thuần (Không Embed) và Reply trực tiếp tin nhắn Giveaway gốc
            if count > 0:
                announcement = (
                    f"<a:lucky:1524034548709724262> **Chúc mừng** {winner_text} nhận được **{prize}** của <@{host_id}>\n"
                    f"Hãy mở Ticket tại <#1507407585962361078> trong vòng 24h để nhận thưởng nhé!"
                )
            else:
                announcement = (
                    f"🎁 **Phần thưởng:** `{prize}`\n"
                    f"👤 **Người tạo:** <@{host_id}>\n"
                    f"• *Không có ai tham gia Giveaway này.*"
                )

            try:
                if msg:
                    await msg.reply(content=announcement, mention_author=False)
                else:
                    await channel.send(content=announcement)
            except:
                pass

        conn.close()


# --- LỆNH !NUKE ---
    @commands.command(name="nuke")
    @is_staff()
    async def nuke_channel(self, ctx):
        """Xóa toàn bộ tin nhắn kênh tức thì (Gửi tin nhắn mẫu Lavie mới)"""
        # Kiểm tra biến GIVEAWAY_CATEGORY trong file .env
        allowed_cat_env = os.getenv("GIVEAWAY_CATEGORY", "").strip()
        if allowed_cat_env:
            allowed_cat_ids = [int(cid.strip()) for cid in allowed_cat_env.split(",") if cid.strip().isdigit()]
            if not ctx.channel.category_id or ctx.channel.category_id not in allowed_cat_ids:
                return await ctx.reply("⛔ **Không thể Nuke!** Kênh này không nằm trong danh sách được phép nuke!")

        channel = ctx.channel
        pos = channel.position
        new_channel = None
        
        # Nội dung tin nhắn gửi sau khi nuke (Đã cập nhật theo yêu cầu)
        nuke_content = (
            "### <:Lavie:1531334063816839298> <:Lavie2:1531334114714714366> <:Lavie3:1531334146650148977> <:Lavie4:1531334188219891872> <:Lavie5:1531334235494027364>\n# <a:brown_star:1523753543897710773> COMING SOON!\n"
            "- Bật thông báo để Nhận thông báo khi có Giveaway mới!\n"
            "-# *Xin cảm ơn!!*"
        )

        for attempt in range(3):
            try:
                # 1. Tạo kênh mới
                new_channel = await channel.clone(reason=f"Kênh được Nuke bởi Staff {ctx.author}")
                await asyncio.sleep(1)
                
                await new_channel.edit(position=pos)
                await asyncio.sleep(0.5)
                
                # 2. Gửi tin nhắn mới vào kênh
                await new_channel.send(content=nuke_content)
                await asyncio.sleep(0.5)

                # 3. Xóa kênh cũ
                await channel.delete(reason="Nuke kênh cũ")
                break

            except discord.HTTPException as e:
                if e.status >= 500 and attempt < 2:
                    await asyncio.sleep(2)
                    continue
                
                try:
                    if new_channel:
                        await new_channel.send(content=f"❌ **Lỗi máy chủ Discord ({e.status}):** Không thể hoàn tất Nuke. Vui lòng thử lại sau!")
                    else:
                        await ctx.reply(content=f"❌ **Lỗi máy chủ Discord ({e.status}):** `{e}`")
                except discord.NotFound:
                    pass
                break

            except discord.Forbidden:
                try:
                    await ctx.reply("❌ **Thiếu quyền!** Bot cần quyền `Quản lý Kênh (Manage Channels)` để thực hiện lệnh Nuke.")
                except discord.NotFound:
                    pass
                break

            except Exception as e:
                try:
                    if new_channel:
                        await new_channel.send(content=f"❌ **Đã xảy ra lỗi khi Nuke:** `{e}`")
                    else:
                        await ctx.reply(content=f"❌ **Đã xảy ra lỗi khi Nuke:** `{e}`")
                except discord.NotFound:
                    pass
                break

async def setup(bot):
    await bot.add_cog(GiveawayNukeCog(bot))