import discord
from discord.ext import commands, tasks
import sqlite3
import os
import time
from datetime import datetime, timedelta

# ==========================================
# 0. HÀM KIỂM TRA QUYỀN STAFF & XỬ LÝ TIME
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

def parse_days(time_str: str) -> int:
    """Chuyển đổi chuỗi thời gian như '12d', '30d' hoặc '30' thành số ngày"""
    time_str = time_str.lower().strip().rstrip('d')
    if time_str.isdigit():
        return int(time_str)
    raise ValueError("Định dạng thời gian không hợp lệ")

# ==========================================
# 1. FORM TÌM KIẾM (MODAL)
# ==========================================
class SearchModal(discord.ui.Modal, title="🔍 Tìm kiếm Custom Role"):
    search_input = discord.ui.TextInput(
        label="ID Role hoặc ID Chủ sở hữu",
        placeholder="Nhập ID (chỉ số, vd: 123456789...)",
        min_length=17,
        max_length=20,
        required=True
    )

    def __init__(self, bot, cog):
        super().__init__()
        self.bot = bot
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        query_id = self.search_input.value.strip()
        if not query_id.isdigit():
            return await interaction.response.send_message("❌ ID nhập vào phải là một dãy số!", ephemeral=True)

        # Tìm trong database theo role_id hoặc user_id
        records = self.cog.get_filtered_records(int(query_id))
        if not records:
            return await interaction.response.send_message(f"❌ Không tìm thấy Custom Role nào với ID `{query_id}` trong hệ thống!", ephemeral=True)

        # Hiển thị kết quả tìm kiếm bằng Component V2
        view = CustomRoleListView(records, interaction.guild, page=0)
        await interaction.response.send_message("✅ **Kết quả tìm kiếm:**", view=view, ephemeral=True)

# ==========================================
# 2. GIAO DIỆN DANH SÁCH COMPONENT V2
# ==========================================
class CustomRoleListView(discord.ui.LayoutView):
    def __init__(self, records: list, guild: discord.Guild, page: int = 0):
        super().__init__(timeout=180)
        self.records = records
        self.guild = guild
        self.page = page
        self.per_page = 5
        self.total_pages = max(1, (len(self.records) + self.per_page - 1) // self.per_page)
        
        self.build_view()

    def build_view(self):
        self.clear_items()
        
        # --- BUILD CONTAINER CHỨA NỘI DUNG ---
        items = [
            discord.ui.TextDisplay(content="# Danh sách Custom Roles"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)
        ]

        start_idx = self.page * self.per_page
        end_idx = min(start_idx + self.per_page, len(self.records))
        page_records = self.records[start_idx:end_idx]

        if not page_records:
            items.append(discord.ui.TextDisplay(content="Hiện tại chưa có Custom Role nào được lưu trong hệ thống."))
        else:
            current_time = int(time.time())
            for idx, row in enumerate(page_records, start=start_idx + 1):
                role_id, user_id, created_at, expires_at, notified = row
                
                role = self.guild.get_role(role_id)
                member = self.guild.get_member(user_id)
                
                role_text = role.mention if role else f"*(Đã xóa - ID: {role_id})*"
                user_text = member.mention if member else f"*(ID: {user_id})*"
                avatar_url = member.display_avatar.url if member else "https://cdn.discordapp.com/embed/avatars/0.png"
                
                # Tính trạng thái và thời gian
                days_ago = max(0, (current_time - created_at) // 86400)
                created_str = datetime.fromtimestamp(created_at).strftime("%d/%m/%Y")
                expires_str = datetime.fromtimestamp(expires_at).strftime("%d/%m/%Y (%H:%M)")
                
                if current_time >= expires_at:
                    status_badge = "🔴 **Hết hạn**"
                else:
                    status_badge = "🟢 **Còn hạn**"

                section_content = (
                    f"### `#0{idx}.` | Role: {role_text} - {status_badge}\n"
                    f"- 👤 **Chủ sở hữu:** {user_text}\n"
                    f"- **Ngày tạo:** {created_str} ({days_ago} ngày trước)\n"
                    f"- **Hết hạn:** {expires_str}"
                )

                items.append(
                    discord.ui.Section(
                        discord.ui.TextDisplay(content=section_content),
                        accessory=discord.ui.Thumbnail(media=avatar_url)
                    )
                )
                if idx < end_idx:
                    items.append(discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))

        container = discord.ui.Container(*items)
        self.add_item(container)

        # --- BUILD ACTION ROW (NÚT ĐIỀU HƯỚNG & TÌM KIẾM) ---
        btn_prev = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="◀️", disabled=(self.page <= 0))
        btn_prev.callback = self.prev_page

        btn_page = discord.ui.Button(style=discord.ButtonStyle.secondary, label=f"Trang {self.page + 1}/{self.total_pages}", disabled=True)

        btn_next = discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="▶️", disabled=(self.page >= self.total_pages - 1))
        btn_next.callback = self.next_page

        btn_search = discord.ui.Button(style=discord.ButtonStyle.success, label="Tìm kiếm", emoji="🔍")
        btn_search.callback = self.open_search

        action_row = discord.ui.ActionRow(btn_prev, btn_page, btn_next, btn_search)
        self.add_item(action_row)

    async def prev_page(self, interaction: discord.Interaction):
        if self.page > 0:
            self.page -= 1
            self.build_view()
            await interaction.response.edit_message(view=self)

    async def next_page(self, interaction: discord.Interaction):
        if self.page < self.total_pages - 1:
            self.page += 1
            self.build_view()
            await interaction.response.edit_message(view=self)

    async def open_search(self, interaction: discord.Interaction):
        # Mở Form tìm kiếm Modal
        modal = SearchModal(interaction.client, interaction.client.get_cog("CustomRolesCog"))
        await interaction.response.send_modal(modal)

# ==========================================
# 3. MODULE COG CHÍNH VÀ XỬ LÝ DATABASE
# ==========================================
class CustomRolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "custom_role.db"
        self.init_database()
        self.check_expires_task.start() # Khởi chạy luồng kiểm tra tự động 24/7

    def init_database(self):
        """Khởi tạo file database sqlite3 nếu chưa có"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS custom_roles (
                role_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                notified INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def get_all_records(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT role_id, user_id, created_at, expires_at, notified FROM custom_roles ORDER BY expires_at ASC")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_filtered_records(self, query_id: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT role_id, user_id, created_at, expires_at, notified FROM custom_roles WHERE role_id = ? OR user_id = ?", (query_id, query_id))
        rows = cursor.fetchall()
        conn.close()
        return rows

    async def log_to_mod_logs(self, guild: discord.Guild, title: str, description: str, color: int):
        """Ghi log hệ thống lên kênh MOD_LOGS"""
        mod_logs_id = os.getenv("MOD_LOGS")
        if mod_logs_id and mod_logs_id.isdigit():
            channel = guild.get_channel(int(mod_logs_id))
            if channel:
                embed = discord.Embed(title=title, description=description, color=color, timestamp=discord.utils.utcnow())
                await channel.send(embed=embed)

    # --- LỆNH !RLIST ---
    @commands.command(name="rlist")
    @is_staff()
    async def rlist(self, ctx):
        """Xem danh sách custom role bằng bảng Component V2"""
        records = self.get_all_records()
        view = CustomRoleListView(records, ctx.guild, page=0)
        await ctx.reply(view=view)

    # --- LỆNH !RADD ---
    @commands.command(name="radd")
    @is_staff()
    async def radd(self, ctx, role: discord.Role = None, user: discord.Member = None, time_str: str = None):
        """Thêm custom role cho user vào database với thời hạn (vd: 12d)"""
        if not role or not user or not time_str:
            return await ctx.reply(
                "❌ **Sai cú pháp!**\n"
                "👉 **Hướng dẫn sử dụng:** `!radd <@Role> <@User> <Thời_gian>`\n"
                "💡 **Ví dụ:** `!radd @VIP @HieuTG 30d` (Gán role VIP cho HieuTG trong 30 ngày)"
            )

        try:
            days = parse_days(time_str)
            if days <= 0: return await ctx.reply("❌ Số ngày phải lớn hơn 0!")
        except ValueError:
            return await ctx.reply("❌ **Định dạng thời gian không hợp lệ!**\n👉 Vui lòng nhập số ngày kèm chữ `d` (Ví dụ: `7d`, `12d`, `30d`).")

        now = int(time.time())
        expires_at = now + (days * 86400)

        # Cấp role cho User trên server nếu chưa có
        if role not in user.roles:
            try:
                await user.add_roles(role)
            except discord.Forbidden:
                return await ctx.reply("❌ Bot không đủ quyền để cấp Role này! Hãy kiểm tra lại vị trí role của Bot trên Server.")

        # Lưu vào Database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO custom_roles (role_id, user_id, created_at, expires_at, notified)
            VALUES (?, ?, ?, ?, 0)
        """, (role.id, user.id, now, expires_at))
        conn.commit()
        conn.close()

        expires_str = datetime.fromtimestamp(expires_at).strftime("%d/%m/%Y %H:%M")
        await ctx.reply(f"✅ Đã thêm/cập nhật Custom Role {role.mention} cho {user.mention}!\n⏳ **Thời hạn:** `{days} ngày` (Hết hạn vào: `{expires_str}`)")
        
        # Log sang MOD_LOGS
        await self.log_to_mod_logs(
            ctx.guild, "➕ Thêm Custom Role Mới",
            f"• **Staff thực hiện:** {ctx.author.mention}\n• **Role:** {role.mention} (`{role.id}`)\n• **Chủ sở hữu:** {user.mention} (`{user.id}`)\n• **Thời gian:** `{days} ngày` (Hết hạn: {expires_str})",
            0x57F287
        )

    # --- LỆNH !RENEW ---
    @commands.command(name="renew")
    @is_staff()
    async def renew(self, ctx, role: discord.Role = None, time_str: str = None):
        """Gia hạn thời gian cho Custom Role (vd: !renew @Role 15d)"""
        if not role or not time_str:
            return await ctx.reply(
                "❌ **Sai cú pháp!**\n"
                "👉 **Hướng dẫn sử dụng:** `!renew <@Role> <Thời_gian_gia_hạn>`\n"
                "💡 **Ví dụ:** `!renew @VIP 15d` (Gia hạn thêm 15 ngày)"
            )

        try:
            days = parse_days(time_str)
            if days <= 0: return await ctx.reply("❌ Số ngày gia hạn phải lớn hơn 0!")
        except ValueError:
            return await ctx.reply("❌ **Định dạng thời gian không hợp lệ!**\n👉 Vui lòng nhập số ngày kèm chữ `d` (Ví dụ: `7d`, `12d`, `30d`).")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, expires_at FROM custom_roles WHERE role_id = ?", (role.id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return await ctx.reply(f"❌ Role {role.mention} không tồn tại trong Database Custom Role!")

        user_id, current_expires = row
        # Nếu đã hết hạn trong quá khứ thì cộng từ thời điểm hiện tại, ngược lại cộng dồn vào hạn cũ
        base_time = max(int(time.time()), current_expires)
        new_expires = base_time + (days * 86400)

        # Cập nhật hạn mới và reset trạng thái notified về 0
        cursor.execute("UPDATE custom_roles SET expires_at = ?, notified = 0 WHERE role_id = ?", (new_expires, role.id))
        conn.commit()
        conn.close()

        # Đảm bảo user vẫn giữ role trên server
        member = ctx.guild.get_member(user_id)
        if member and role not in member.roles:
            try: await member.add_roles(role)
            except: pass

        expires_str = datetime.fromtimestamp(new_expires).strftime("%d/%m/%Y %H:%M")
        await ctx.reply(f"🔄 Đã gia hạn thành công Role {role.mention} thêm **`{days} ngày`**!\n📅 **Hạn mới:** `{expires_str}`")
        
        # Log sang MOD_LOGS
        await self.log_to_mod_logs(
            ctx.guild, "🔄 Gia Hạn Custom Role",
            f"• **Staff thực hiện:** {ctx.author.mention}\n• **Role:** {role.mention} (`{role.id}`)\n• **Chủ sở hữu:** <@{user_id}>\n• **Gia hạn thêm:** `{days} ngày`\n• **Hạn mới:** `{expires_str}`",
            0xFEE75C
        )

    # --- LỆNH !RXOA ---
    @commands.command(name="rxoa")
    @is_staff()
    async def rxoa(self, ctx, role: discord.Role = None):
        """Xóa role khỏi server và bỏ theo dõi trong database"""
        if not role:
            return await ctx.reply(
                "❌ **Sai cú pháp!**\n"
                "👉 **Hướng dẫn sử dụng:** `!rxoa <@Role>`\n"
                "💡 **Ví dụ:** `!rxoa @VIP`"
            )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM custom_roles WHERE role_id = ?", (role.id,))
        row = cursor.fetchone()
        
        if row:
            cursor.execute("DELETE FROM custom_roles WHERE role_id = ?", (role.id,))
            conn.commit()
        conn.close()

        role_name = role.name
        role_id = role.id
        owner_id = row[0] if row else None
        owner_str = f"<@{owner_id}>" if owner_id else "Không xác định"

        # Xóa Role khỏi máy chủ Discord
        try:
            await role.delete(reason=f"Staff {ctx.author} đã xóa Custom Role qua lệnh !rxoa")
            await ctx.reply(f"🗑️ Đã xóa hoàn toàn Role **{role_name}** khỏi Máy chủ và Database!")
        except discord.Forbidden:
            await ctx.reply(f"⚠️ Đã xóa Role **{role_name}** khỏi Database, nhưng Bot không có quyền xóa Role này trên Server! Hãy xóa thủ công trong Cài đặt Server.")
        except discord.HTTPException as e:
            await ctx.reply(f"⚠️ Đã xóa khỏi Database nhưng gặp lỗi khi xóa role trên Server: {e}")

        # Log sang MOD_LOGS
        await self.log_to_mod_logs(
            ctx.guild, "🗑️ Xóa Custom Role",
            f"• **Staff thực hiện:** {ctx.author.mention}\n• **Role đã xóa:** **{role_name}** (`{role_id}`)\n• **Chủ sở hữu:** {owner_str}",
            0xED4245
        )

    # ==========================================
    # 4. TASK KIỂM TRA HẾT HẠN & THÔNG BÁO DMS (Chạy mỗi 30 phút)
    # ==========================================
    @tasks.loop(minutes=30)
    async def check_expires_task(self):
        await self.bot.wait_until_ready()
        now = int(time.time())
        one_day_later = now + 86400

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tìm các role còn <= 1 ngày hạn và chưa thông báo (notified == 0)
        cursor.execute("SELECT role_id, user_id, expires_at FROM custom_roles WHERE expires_at <= ? AND expires_at > ? AND notified = 0", (one_day_later, now))
        expiring_soon = cursor.fetchall()

        for role_id, user_id, expires_at in expiring_soon:
            for guild in self.bot.guilds:
                role = guild.get_role(role_id)
                member = guild.get_member(user_id)
                if role and member:
                    expires_str = datetime.fromtimestamp(expires_at).strftime("%d/%m/%Y %H:%M")
                    
                    # Gửi DMS thông báo cho chủ sở hữu
                    try:
                        dm_embed = discord.Embed(
                            title="⚠️ Thông Báo Sắp Hết Hạn Custom Role",
                            description=(
                                f"Chào bạn **{member.display_name}**,\n\n"
                                f"Custom Role **{role.name}** của bạn tại máy chủ **{guild.name}** chỉ còn **1 ngày nữa** sẽ hết hạn (Vào lúc: `{expires_str}`).\n\n"
                                f"👉 **Vui lòng mở Ticket hỗ trợ tại máy chủ để tiến hành gia hạn tránh bị mất role nhé!**"
                            ),
                            color=0xFEE75C
                        )
                        await member.send(embed=dm_embed)
                    except discord.Forbidden:
                        print(f"⚠️ Không thể gửi DMS cho user {user_id} (Họ đã tắt nhận tin nhắn người lạ).")

                    # Log thông báo lên MOD_LOGS
                    await self.log_to_mod_logs(
                        guild, "⏰ Thông Báo Gia Hạn Custom Role",
                        f"• **Role:** {role.mention} (`{role.id}`)\n• **Chủ sở hữu:** {member.mention} (`{member.id}`)\n• **Hạn cuối:** `{expires_str}`\n• **Trạng thái:** Đã gửi hệ thống cảnh báo DMS trước 1 ngày.",
                        0xFEE75C
                    )

                    # Đánh dấu đã gửi cảnh báo để không gửi lại liên tục
                    cursor.execute("UPDATE custom_roles SET notified = 1 WHERE role_id = ?", (role_id,))
                    conn.commit()

        conn.close()

    @check_expires_task.before_loop
    async def before_check_task(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(CustomRolesCog(bot))