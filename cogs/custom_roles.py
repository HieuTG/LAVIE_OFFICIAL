import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import os
import time
from datetime import datetime

# ==========================================
# 0. HÀM KIỂM TRA QUYỀN STAFF & XỬ LÝ TIME
# ==========================================
def is_staff_user(interaction: discord.Interaction) -> bool:
    """Kiểm tra người dùng có sở hữu role trong ROLES_STAFF hoặc Admin không"""
    if interaction.user.guild_permissions.administrator:
        return True
    
    roles_env = os.getenv("ROLES_STAFF", "")
    if not roles_env:
        return False
        
    staff_role_ids = [int(r.strip()) for r in roles_env.split(",") if r.strip().isdigit()]
    user_role_ids = [r.id for r in interaction.user.roles]
    return any(role_id in staff_role_ids for role_id in user_role_ids)

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

        records = self.cog.get_filtered_records(int(query_id))
        if not records:
            return await interaction.response.send_message(f"❌ Không tìm thấy Custom Role nào với ID `{query_id}` trong hệ thống!", ephemeral=True)

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
                
                days_ago = max(0, (current_time - created_at) // 86400)
                created_str = datetime.fromtimestamp(created_at).strftime("%d/%m/%Y")
                expires_str = datetime.fromtimestamp(expires_at).strftime("%d/%m/%Y (%H:%M)")
                
                status_badge = "🔴 **Hết hạn**" if current_time >= expires_at else "🟢 **Còn hạn**"

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
        modal = SearchModal(interaction.client, interaction.client.get_cog("CustomRolesCog"))
        await interaction.response.send_modal(modal)

# ==========================================
# 3. MODULE COG CHÍNH VÀ XỬ LÝ DATABASE
# ==========================================
class CustomRolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Tự động chọn file DB đã tồn tại (custom_role.db hoặc custom_roles.db)
        env_db = os.getenv("CUSTOM_ROLE_DB_PATH")
        if env_db and os.path.exists(env_db):
            self.db_path = env_db
        elif os.path.exists("custom_roles.db"):
            self.db_path = "custom_roles.db"
        else:
            self.db_path = "custom_role.db"

        self.init_database()
        self.check_expires_task.start()

    def init_database(self):
        """Khởi tạo hoặc kết nối file SQLite có sẵn và đảm bảo đủ cấu trúc cột"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tạo bảng nếu chưa tồn tại đúng cấu trúc 
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS custom_roles (
                role_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                notified INTEGER DEFAULT 0
            )
        """)

        # Tự động bổ sung cột 'notified' nếu DB cũ chưa có
        cursor.execute("PRAGMA table_info(custom_roles)")
        columns = [column[1] for column in cursor.fetchall()]
        if "notified" not in columns:
            cursor.execute("ALTER TABLE custom_roles ADD COLUMN notified INTEGER DEFAULT 0")
            print("🛠️ [DATABASE] Đã tự động bổ sung cột 'notified' vào bảng custom_roles!")

        conn.commit()
        conn.close()
        print(f"✅ [CUSTOM ROLE] Đã kết nối thành công tới Database: '{self.db_path}'")

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
        mod_logs_id = os.getenv("MOD_LOGS")
        if mod_logs_id and mod_logs_id.isdigit():
            channel = guild.get_channel(int(mod_logs_id))
            if channel:
                embed = discord.Embed(title=title, description=description, color=color, timestamp=discord.utils.utcnow())
                await channel.send(embed=embed)

    # ==========================================
    # 4. DASHBOARD SLASH COMMANDS (/customrole)
    # ==========================================
    role_group = app_commands.Group(name="customrole", description="Quản lý Custom Roles gia hạn")

    # --- /customrole list ---
    @role_group.command(name="list", description="Xem danh sách Custom Roles bằng bảng Component V2")
    async def role_list(self, interaction: discord.Interaction):
        if not is_staff_user(interaction):
            return await interaction.response.send_message("⛔ Bạn không có quyền (Staff) để sử dụng lệnh này!", ephemeral=True)

        records = self.get_all_records()
        view = CustomRoleListView(records, interaction.guild, page=0)
        await interaction.response.send_message(view=view)

    # --- /customrole add ---
    @role_group.command(name="add", description="Thêm custom role cho user với thời hạn (VD: 30d hoặc 30)")
    @app_commands.describe(role="Role cần gán", user="Chủ sở hữu role", days="Thời gian sử dụng (VD: 30d)")
    async def role_add(self, interaction: discord.Interaction, role: discord.Role, user: discord.Member, days: str):
        if not is_staff_user(interaction):
            return await interaction.response.send_message("⛔ Bạn không có quyền (Staff) để sử dụng lệnh này!", ephemeral=True)

        try:
            days_int = parse_days(days)
            if days_int <= 0:
                return await interaction.response.send_message("❌ Số ngày phải lớn hơn 0!", ephemeral=True)
        except ValueError:
            return await interaction.response.send_message("❌ **Định dạng thời gian không hợp lệ!** Vui lòng nhập dạng `30d` hoặc `30`.", ephemeral=True)

        now = int(time.time())
        expires_at = now + (days_int * 86400)

        if role not in user.roles:
            try:
                await user.add_roles(role)
            except discord.Forbidden:
                return await interaction.response.send_message("❌ Bot không đủ quyền để cấp Role này! Hãy kiểm tra lại thứ tự Role trong Cài đặt Server.", ephemeral=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO custom_roles (role_id, user_id, created_at, expires_at, notified)
            VALUES (?, ?, ?, ?, 0)
        """, (role.id, user.id, now, expires_at))
        conn.commit()
        conn.close()

        expires_str = datetime.fromtimestamp(expires_at).strftime("%d/%m/%Y %H:%M")
        await interaction.response.send_message(f"✅ Đã thêm/cập nhật Custom Role {role.mention} cho {user.mention}!\n⏳ **Thời hạn:** `{days_int} ngày` (Hết hạn vào: `{expires_str}`)")

        await self.log_to_mod_logs(
            interaction.guild, "➕ Thêm Custom Role Mới",
            f"• **Staff thực hiện:** {interaction.user.mention}\n• **Role:** {role.mention} (`{role.id}`)\n• **Chủ sở hữu:** {user.mention} (`{user.id}`)\n• **Thời gian:** `{days_int} ngày` (Hết hạn: {expires_str})",
            0x57F287
        )

    # --- /customrole renew ---
    @role_group.command(name="renew", description="Gia hạn thời gian cho Custom Role (VD: 15d hoặc 15)")
    @app_commands.describe(role="Role cần gia hạn", days="Số ngày cộng thêm (VD: 15d)")
    async def role_renew(self, interaction: discord.Interaction, role: discord.Role, days: str):
        if not is_staff_user(interaction):
            return await interaction.response.send_message("⛔ Bạn không có quyền (Staff) để sử dụng lệnh này!", ephemeral=True)

        try:
            days_int = parse_days(days)
            if days_int <= 0:
                return await interaction.response.send_message("❌ Số ngày gia hạn phải lớn hơn 0!", ephemeral=True)
        except ValueError:
            return await interaction.response.send_message("❌ **Định dạng thời gian không hợp lệ!**", ephemeral=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, expires_at FROM custom_roles WHERE role_id = ?", (role.id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return await interaction.response.send_message(f"❌ Role {role.mention} không tồn tại trong Database Custom Role!", ephemeral=True)

        user_id, current_expires = row
        base_time = max(int(time.time()), current_expires)
        new_expires = base_time + (days_int * 86400)

        cursor.execute("UPDATE custom_roles SET expires_at = ?, notified = 0 WHERE role_id = ?", (new_expires, role.id))
        conn.commit()
        conn.close()

        member = interaction.guild.get_member(user_id)
        if member and role not in member.roles:
            try: await member.add_roles(role)
            except: pass

        expires_str = datetime.fromtimestamp(new_expires).strftime("%d/%m/%Y %H:%M")
        await interaction.response.send_message(f"🔄 Đã gia hạn thành công Role {role.mention} thêm **`{days_int} ngày`**!\n📅 **Hạn mới:** `{expires_str}`")

        await self.log_to_mod_logs(
            interaction.guild, "🔄 Gia Hạn Custom Role",
            f"• **Staff thực hiện:** {interaction.user.mention}\n• **Role:** {role.mention} (`{role.id}`)\n• **Chủ sở hữu:** <@{user_id}>\n• **Gia hạn thêm:** `{days_int} ngày`\n• **Hạn mới:** `{expires_str}`",
            0xFEE75C
        )

    # --- /customrole delete ---
    @role_group.command(name="delete", description="Xóa role khỏi server và bỏ theo dõi trong database")
    @app_commands.describe(role="Role cần xóa")
    async def role_delete(self, interaction: discord.Interaction, role: discord.Role):
        if not is_staff_user(interaction):
            return await interaction.response.send_message("⛔ Bạn không có quyền (Staff) để sử dụng lệnh này!", ephemeral=True)

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

        try:
            await role.delete(reason=f"Staff {interaction.user} đã xóa Custom Role qua lệnh /customrole delete")
            await interaction.response.send_message(f"🗑️ Đã xóa hoàn toàn Role **{role_name}** khỏi Máy chủ và Database!")
        except discord.Forbidden:
            await interaction.response.send_message(f"⚠️ Đã xóa Role **{role_name}** khỏi Database, nhưng Bot không có quyền xóa Role này trên Server!", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"⚠️ Đã xóa khỏi Database nhưng gặp lỗi khi xóa role trên Server: {e}", ephemeral=True)

        await self.log_to_mod_logs(
            interaction.guild, "🗑️ Xóa Custom Role",
            f"• **Staff thực hiện:** {interaction.user.mention}\n• **Role đã xóa:** **{role_name}** (`{role_id}`)\n• **Chủ sở hữu:** {owner_str}",
            0xED4245
        )

    # ==========================================
    # 5. TASK KIỂM TRA HẾT HẠN & THÔNG BÁO DMS
    # ==========================================
    @tasks.loop(minutes=30)
    async def check_expires_task(self):
        await self.bot.wait_until_ready()
        now = int(time.time())
        one_day_later = now + 86400

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT role_id, user_id, expires_at FROM custom_roles WHERE expires_at <= ? AND expires_at > ? AND notified = 0", (one_day_later, now))
        expiring_soon = cursor.fetchall()

        for role_id, user_id, expires_at in expiring_soon:
            for guild in self.bot.guilds:
                role = guild.get_role(role_id)
                member = guild.get_member(user_id)
                if role and member:
                    expires_str = datetime.fromtimestamp(expires_at).strftime("%d/%m/%Y %H:%M")
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
                        pass

                    await self.log_to_mod_logs(
                        guild, "⏰ Thông Báo Gia Hạn Custom Role",
                        f"• **Role:** {role.mention} (`{role.id}`)\n• **Chủ sở hữu:** {member.mention} (`{member.id}`)\n• **Hạn cuối:** `{expires_str}`\n• **Trạng thái:** Đã gửi hệ thống cảnh báo DMS trước 1 ngày.",
                        0xFEE75C
                    )

                    cursor.execute("UPDATE custom_roles SET notified = 1 WHERE role_id = ?", (role_id,))
                    conn.commit()

        conn.close()

    @check_expires_task.before_loop
    async def before_check_task(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(CustomRolesCog(bot))