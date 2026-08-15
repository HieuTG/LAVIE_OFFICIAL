import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import os
import time
import random
import asyncio

# ==========================================
# 0. HÀM KIỂM TRA QUYỀN STAFF & XỬ LÝ THỜI GIAN
# ==========================================
def is_staff_user(user: discord.Member) -> bool:
    """Kiểm tra người dùng có sở hữu role trong ROLES_STAFF hoặc là Admin không"""
    if user.guild_permissions.administrator:
        return True
    roles_env = os.getenv("ROLES_STAFF", "")
    if not roles_env:
        return False
    staff_role_ids = [int(r.strip()) for r in roles_env.split(",") if r.strip().isdigit()]
    user_role_ids = [r.id for r in user.roles]
    return any(role_id in staff_role_ids for role_id in user_role_ids)

def is_staff():
    """Predicate Check dành cho Prefix Commands"""
    async def predicate(ctx):
        if is_staff_user(ctx.author):
            return True
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

def extract_ids_from_link(link_or_id: str):
    """Trích xuất channel_id và message_id từ Discord message link hoặc ID đơn"""
    if not link_or_id:
        return None, None
    link_or_id = link_or_id.strip()
    if "/" in link_or_id:
        parts = link_or_id.rsplit("/", 2)
        if len(parts) >= 2 and parts[-1].isdigit():
            msg_id = int(parts[-1])
            channel_id = int(parts[-2]) if parts[-2].isdigit() else None
            return channel_id, msg_id
    elif link_or_id.isdigit():
        return None, int(link_or_id)
    return None, None

# ==========================================
# 1. TẠO EMBED VÀ NÚT BẤM (GIAO DIỆN EMBED)
# ==========================================
def build_giveaway_embed(prize: str, end_time: int, host_id: int, required_role_id: int = None, count: int = 0, winners_count: int = 1, ended: bool = False, winner_text: str = None, guild: discord.Guild = None) -> discord.Embed:
    icon_url = guild.icon.url if (guild and guild.icon) else None
    
    if not ended:
        embed = discord.Embed(
            title="<:lavie1:1534553030937018530><:lavie2:1534553133446070482><:lavie3:1534553194502557718><:lavie4:1534553262504808488><:lavie5:1534553319111000085>",
            description=(
                f"# <a:h1h441:1504391747201925162> GIVEAWAY <a:h1h440:1504391680898367538>\n\n"
                f"## <:holiday_crate:1523749995059216494> **Phần thưởng:** `{prize}`\n\n"
                f"• **Người tạo:** <@{host_id}>\n"
                f"• **Số giải:** `{winners_count}` người thắng\n"
                f"• **Kết thúc:** <t:{end_time}:R> (<t:{end_time}:f>)\n"
                f"• **Yêu cầu Role:** {f'<@&{required_role_id}>' if required_role_id else 'Tất cả mọi người'}\n"
                f"• **Số người tham gia:** `{count}` người\n\n"
                f"**NHỚ LÀM REQ ( NẾU CÓ ) TRƯỚC KHI THAM GIA!!!<a:0013_redfish:1507669400994447400>**"
            ),
            color=discord.Color.from_str("#00FFFF")
        )
        embed.set_footer(text="L A V I E • Bấm nút bên dưới để tham gia", icon_url=icon_url)
    else:
        embed = discord.Embed(
            title="<:lavie1:1534553030937018530><:lavie2:1534553133446070482><:lavie3:1534553194502557718><:lavie4:1534553262504808488><:lavie5:1534553319111000085>",
            description=(
                f"# GIVEAWAY ĐÃ KẾT THÚC\n\n"
                f"## <:holiday_crate:1523749995059216494> **Phần thưởng:** `{prize}`\n\n"
                f"• **Người tạo:** <@{host_id}>\n"
                f"• **Số giải:** `{winners_count}` người thắng\n"
                f"• **Người thắng cuộc:** {winner_text}\n"
                f"• **Tổng người tham gia:** `{count}` người\n"
                f"• **Đã kết thúc lúc:** <t:{end_time}:f>"
            ),
            color=discord.Color.from_str("#00FFFF")
        )
        embed.set_footer(text="L A V I E • Đã kết thúc", icon_url=icon_url)
    return embed

class GiveawayJoinView(discord.ui.View):
    def __init__(self, count: int = 0, ended: bool = False):
        super().__init__(timeout=None)
        if ended:
            btn = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label="Đã kết thúc",
                emoji="🔒",
                disabled=True,
                custom_id="ga_button_join"
            )
        else:
            btn = discord.ui.Button(
                style=discord.ButtonStyle.success,
                label=f"Tham gia ({count})",
                emoji="<a:tada_right:1523846292105724035>",
                disabled=False,
                custom_id="ga_button_join"
            )
        self.add_item(btn)

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
        """Khởi tạo file cơ sở dữ liệu cho Giveaway và tự động nâng cấp nếu thiếu cột"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS giveaways (
                message_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                host_id INTEGER NOT NULL,
                prize TEXT NOT NULL,
                winners_count INTEGER DEFAULT 1,
                end_time INTEGER NOT NULL,
                required_role_id INTEGER,
                ended INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ga_participants (
                message_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (message_id, user_id)
            )
        """)

        cursor.execute("PRAGMA table_info(giveaways)")
        columns = [column[1] for column in cursor.fetchall()]
        if "winners_count" not in columns:
            cursor.execute("ALTER TABLE giveaways ADD COLUMN winners_count INTEGER DEFAULT 1")
            print("🛠️ [DATABASE] Đã tự động bổ sung cột 'winners_count' vào bảng giveaways thành công!")

        conn.commit()
        conn.close()

    def get_participant_count(self, message_id: int) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ga_participants WHERE message_id = ?", (message_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    # ==========================================
    # 3. SLASH COMMAND: /giveaway start
    # ==========================================
    giveaway_group = app_commands.Group(name="giveaway", description="Lệnh quản lý Giveaway")

    @giveaway_group.command(name="start", description="Tạo một Giveaway mới")
    @app_commands.describe(
        time_str="Thời gian diễn ra (Ví dụ: 30s, 10m, 2h, 1d)",
        prize="Tên phần thưởng",
        winners="Số lượng người chiến thắng (Mặc định: 1)",
        required_role="Yêu cầu Role để tham gia (Tùy chọn)"
    )
    async def giveaway_start_slash(
        self,
        interaction: discord.Interaction,
        time_str: str,
        prize: str,
        winners: int = 1,
        required_role: discord.Role = None
    ):
        if not is_staff_user(interaction.user):
            return await interaction.response.send_message("⛔ Bạn không có quyền (Staff) để sử dụng lệnh này!", ephemeral=True)

        if winners < 1:
            return await interaction.response.send_message("❌ **Số người thắng** phải lớn hơn 0!", ephemeral=True)

        try:
            duration = parse_duration(time_str)
            if duration < 10:
                return await interaction.response.send_message("❌ Thời gian Giveaway tối thiểu phải từ **10 giây** trở lên!", ephemeral=True)
        except ValueError:
            return await interaction.response.send_message("❌ **Định dạng thời gian không hợp lệ!** Dùng các đuôi `s`, `m`, `h`, `d` (Ví dụ: 30m, 2h).", ephemeral=True)

        end_time = int(time.time()) + duration
        req_role_id = required_role.id if required_role else None
        host_id = interaction.user.id

        embed = build_giveaway_embed(prize, end_time, host_id, req_role_id, count=0, winners_count=winners, guild=interaction.guild)
        view = GiveawayJoinView(count=0, ended=False)

        await interaction.response.send_message(embed=embed, view=view)
        ga_msg = await interaction.original_response()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO giveaways (message_id, channel_id, guild_id, host_id, prize, winners_count, end_time, required_role_id, ended)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (ga_msg.id, interaction.channel_id, interaction.guild_id, host_id, prize, winners, end_time, req_role_id))
        conn.commit()
        conn.close()

    # ==========================================
    # 4. PREFIX COMMANDS (!ga, !ga end, !ga reroll)
    # ==========================================
    @commands.group(name="giveaway", aliases=["ga"], invoke_without_command=True)
    @is_staff()
    async def create_giveaway(self, ctx):
        """Hướng dẫn khi gõ !ga sai cú pháp"""
        await ctx.reply(
            "👉 **Tạo Giveaway:** Dùng lệnh Slash `/giveaway start`\n"
            "👉 **Kết thúc:** `!ga end [Link/ID tin nhắn]` (Hoặc để trống cho GA gần nhất)\n"
            "👉 **Quay lại:** `!ga reroll [Link/ID tin nhắn]` (Hoặc để trống cho GA gần nhất)"
        )

    # --- LỆNH !GA END ---
    @create_giveaway.command(name="end")
    @is_staff()
    async def end_giveaway(self, ctx, message_link: str = None):
        """Kết thúc ngay lập tức một Giveaway (Gần nhất hoặc theo ID/Link)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if message_link:
            _, msg_id = extract_ids_from_link(message_link)
            if not msg_id:
                conn.close()
                return await ctx.reply("❌ **Link hoặc ID tin nhắn không hợp lệ!**")
            cursor.execute("SELECT message_id, channel_id, guild_id, host_id, prize, end_time, required_role_id, winners_count, ended FROM giveaways WHERE message_id = ?", (msg_id,))
        else:
            cursor.execute("SELECT message_id, channel_id, guild_id, host_id, prize, end_time, required_role_id, winners_count, ended FROM giveaways WHERE channel_id = ? AND ended = 0 ORDER BY message_id DESC LIMIT 1", (ctx.channel.id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return await ctx.reply("❌ **Không tìm thấy Giveaway đang diễn ra nào!**")

        msg_id, channel_id, guild_id, host_id, prize, end_time, req_role_id, winners_count, ended = row

        if ended == 1:
            conn.close()
            return await ctx.reply("⚠️ **Giveaway này đã kết thúc từ trước rồi!**")

        cursor.execute("SELECT user_id FROM ga_participants WHERE message_id = ?", (msg_id,))
        participants = [r[0] for r in cursor.fetchall()]
        count = len(participants)

        if count == 0:
            winner_text = "Không có ai tham gia"
        else:
            num_winners = min(count, winners_count if winners_count else 1)
            winners_list = random.sample(participants, num_winners)
            winner_text = ", ".join([f"<@{w_id}>" for w_id in winners_list])

        cursor.execute("UPDATE giveaways SET ended = 1 WHERE message_id = ?", (msg_id,))
        conn.commit()
        conn.close()

        channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
        msg = None
        if channel:
            try:
                msg = await channel.fetch_message(msg_id)
                embed = build_giveaway_embed(prize, end_time, host_id, req_role_id, count, winners_count, ended=True, winner_text=winner_text, guild=ctx.guild)
                view = GiveawayJoinView(count=count, ended=True)
                await msg.edit(embed=embed, view=view)
            except:
                pass

            if count > 0:
                announcement = (
                    f"<a:lucky:1524034548709724262> **Chúc mừng** {winner_text} nhận được **{prize}** của <@{host_id}>\n"
                    f"Hãy mở Ticket tại <#1507407585962361078> trong vòng 24h để nhận thưởng nhé!"
                )
            else:
                announcement = f"🎁 **Phần thưởng:** `{prize}`\n👤 **Người tạo:** <@{host_id}>\n• *Không có ai tham gia Giveaway này.*"

            try:
                if msg:
                    await msg.reply(content=announcement, mention_author=False)
                else:
                    await channel.send(content=announcement)
            except:
                pass

        await ctx.reply("🛑 **Đã kết thúc Giveaway thành công!**")

    # --- LỆNH !GA REROLL ---
    @create_giveaway.command(name="reroll")
    @is_staff()
    async def reroll_giveaway(self, ctx, message_link: str = None):
        """Quay lại người chiến thắng (Gần nhất hoặc theo ID/Link)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if message_link:
            _, msg_id = extract_ids_from_link(message_link)
            if not msg_id:
                conn.close()
                return await ctx.reply("❌ **Link hoặc ID tin nhắn không hợp lệ!**")
            cursor.execute("SELECT message_id, channel_id, guild_id, host_id, prize, winners_count FROM giveaways WHERE message_id = ?", (msg_id,))
        else:
            cursor.execute("SELECT message_id, channel_id, guild_id, host_id, prize, winners_count FROM giveaways WHERE channel_id = ? AND ended = 1 ORDER BY message_id DESC LIMIT 1", (ctx.channel.id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return await ctx.reply("❌ **Không tìm thấy Giveaway đã kết thúc nào!**")

        msg_id, channel_id, guild_id, host_id, prize, winners_count = row

        cursor.execute("SELECT user_id FROM ga_participants WHERE message_id = ?", (msg_id,))
        participants = [r[0] for r in cursor.fetchall()]
        conn.close()

        count = len(participants)
        if count == 0:
            return await ctx.reply("❌ **Không thể Reroll!** Không có ai tham gia Giveaway này.")

        num_winners = min(count, winners_count if winners_count else 1)
        winners_list = random.sample(participants, num_winners)
        winner_text = ", ".join([f"<@{w_id}>" for w_id in winners_list])

        channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
        if channel:
            try:
                msg = await channel.fetch_message(msg_id)
            except:
                msg = None

            reroll_announcement = (
                f"🎉 **REROLL GIVEAWAY!**\n"
                f"<a:lucky:1524034548709724262> **Chúc mừng** {winner_text} nhận được **{prize}** của <@{host_id}>\n"
                f"Hãy mở Ticket tại <#1507407585962361078> trong vòng 24h để nhận thưởng nhé!"
            )

            try:
                if msg:
                    await msg.reply(content=reroll_announcement, mention_author=False)
                else:
                    await channel.send(content=reroll_announcement)
            except:
                pass

        await ctx.reply(f"🎲 **Đã Reroll thành công!** Người chiến thắng mới: {winner_text}")

    # ==========================================
    # 5. XỬ LÝ BẤM NÚT THAM GIA / RỜI GA
    # ==========================================
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get("custom_id", "")
        if custom_id != "ga_button_join":
            return

        message_id = interaction.message.id

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT prize, end_time, host_id, required_role_id, winners_count, ended FROM giveaways WHERE message_id = ?", (message_id,))
        ga_row = cursor.fetchone()

        if not ga_row or ga_row[5] == 1:
            conn.close()
            return await interaction.response.send_message("❌ Giveaway này đã kết thúc hoặc không tồn tại!", ephemeral=True)

        prize, end_time, host_id, required_role_id, winners_count, _ = ga_row

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

            embed = build_giveaway_embed(prize, end_time, host_id, required_role_id, count, winners_count, guild=interaction.guild)
            view = GiveawayJoinView(count=count, ended=False)
            try:
                await interaction.message.edit(embed=embed, view=view)
            except:
                pass

            await interaction.response.send_message("❌ **Bạn đã rời khỏi Giveaway!** (Bấm nút lần nữa nếu muốn đổi ý)", ephemeral=True)
        else:
            cursor.execute("INSERT INTO ga_participants (message_id, user_id) VALUES (?, ?)", (message_id, interaction.user.id))
            conn.commit()
            count = self.get_participant_count(message_id)
            conn.close()

            embed = build_giveaway_embed(prize, end_time, host_id, required_role_id, count, winners_count, guild=interaction.guild)
            view = GiveawayJoinView(count=count, ended=False)
            try:
                await interaction.message.edit(embed=embed, view=view)
            except:
                pass

            await interaction.response.send_message("🎉 **Bạn đã tham gia Giveaway thành công!** Chúc bạn may mắn!", ephemeral=True)

    # ==========================================
    # 6. TASK TỰ ĐỘNG TÍNH GIVEAWAY HẾT HẠN
    # ==========================================
    @tasks.loop(seconds=15)
    async def check_giveaway_task(self):
        await self.bot.wait_until_ready()
        now = int(time.time())

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT message_id, channel_id, guild_id, host_id, prize, end_time, required_role_id, winners_count FROM giveaways WHERE ended = 0 AND end_time <= ?", (now,))
        expired_giveaways = cursor.fetchall()

        for msg_id, channel_id, guild_id, host_id, prize, end_time, req_role_id, winners_count in expired_giveaways:
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
                num_winners = min(count, winners_count if winners_count else 1)
                winners_list = random.sample(participants, num_winners)
                winner_text = ", ".join([f"<@{w_id}>" for w_id in winners_list])

            cursor.execute("UPDATE giveaways SET ended = 1 WHERE message_id = ?", (msg_id,))
            conn.commit()

            msg = None
            try:
                msg = await channel.fetch_message(msg_id)
                embed = build_giveaway_embed(prize, end_time, host_id, req_role_id, count, winners_count, ended=True, winner_text=winner_text, guild=guild)
                view = GiveawayJoinView(count=count, ended=True)
                await msg.edit(embed=embed, view=view)
            except:
                pass

            if count > 0:
                announcement = (
                    f"<a:lucky:1524034548709724262> **Chúc mừng** {winner_text} nhận được **{prize}** của <@{host_id}>\n"
                    f"Hãy mở Ticket tại <#1507407585962361078> trong vòng 24h để nhận thưởng nhé!"
                )
            else:
                announcement = f"🎁 **Phần thưởng:** `{prize}`\n👤 **Người tạo:** <@{host_id}>\n• *Không có ai tham gia Giveaway này.*"

            try:
                if msg:
                    await msg.reply(content=announcement, mention_author=False)
                else:
                    await channel.send(content=announcement)
            except:
                pass

        conn.close()

    # ==========================================
    # 7. LỆNH !NUKE
    # ==========================================
    @commands.command(name="nuke")
    @is_staff()
    async def nuke_channel(self, ctx):
        """Xóa toàn bộ tin nhắn kênh tức thì"""
        allowed_cat_env = os.getenv("GIVEAWAY_CATEGORY", "").strip()
        if allowed_cat_env:
            allowed_cat_ids = [int(cid.strip()) for cid in allowed_cat_env.split(",") if cid.strip().isdigit()]
            if not ctx.channel.category_id or ctx.channel.category_id not in allowed_cat_ids:
                return await ctx.reply("⛔ **Không thể Nuke!** Kênh này không nằm trong danh sách được phép nuke!")

        channel = ctx.channel
        pos = channel.position
        new_channel = None
        
        nuke_content = (
            "### <:Lavie:1531334063816839298> <:Lavie2:1531334114714714366> <:Lavie3:1531334146650148977> <:Lavie4:1531334188219891872> <:Lavie5:1531334235494027364>\n# <a:brown_star:1523753543897710773> COMING SOON!\n"
            "- Bật thông báo để Nhận thông báo khi có Giveaway mới!\n"
            "-# *Xin cảm ơn!!*"
        )

        for attempt in range(3):
            try:
                new_channel = await channel.clone(reason=f"Kênh được Nuke bởi Staff {ctx.author}")
                await asyncio.sleep(1)
                
                await new_channel.edit(position=pos)
                await asyncio.sleep(0.5)
                
                await new_channel.send(content=nuke_content)
                await asyncio.sleep(0.5)

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