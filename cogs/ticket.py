import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import database as db

# ==========================================
# 1. MODAL ĐÓNG TICKET KÈM LÝ DO / GHI CHÚ
# ==========================================
class CloseReasonModal(discord.ui.Modal, title="Đóng Ticket"):
    reason = discord.ui.TextInput(
        label="Lý do / Ghi chú đóng ticket",
        style=discord.TextStyle.paragraph,
        placeholder="Ví dụ: Đã giải đáp xong / Khách không phản hồi...",
        required=False,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        close_reason = self.reason.value if self.reason.value else "Không có ghi chú"
        await interaction.response.send_message(
            f"🔒 **Ticket này sẽ tự động xóa sau 5 giây...**\n📝 **Lý do/Ghi chú:** {close_reason}"
        )
        
        # Gửi log vào channel Ticket Log nếu có cài đặt
        log_channel_id = os.getenv("TICKET_LOGS_CHANNEL")
        if log_channel_id:
            log_channel = interaction.guild.get_channel(int(log_channel_id))
            if log_channel:
                embed_log = discord.Embed(
                    title="📝 TICKET CLOSED",
                    description=(
                        f"**Kênh:** `{interaction.channel.name}`\n"
                        f"**Người đóng:** {interaction.user.mention}\n"
                        f"**Lý do:** {close_reason}"
                    ),
                    color=discord.Color.red()
                )
                await log_channel.send(embed=embed_log)

        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Đóng ticket bởi {interaction.user}: {close_reason}")


# ==========================================
# 2. GIAO DIỆN BÊN TRONG KÊNH TICKET (LAYOUT VIEW)
# ==========================================
class TicketControlView(discord.ui.LayoutView):
    def __init__(self, ticket_name: str, user: discord.User):
        super().__init__(timeout=None)
        self.ticket_name = ticket_name
        self.user = user

        created_timestamp = f"<t:{int(discord.utils.utcnow().timestamp())}:F>"

        # Tạo nút Claim & Close
        btn_claim = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Claim",
            emoji="🤚",
            custom_id="lavie_ticket_claim_btn"
        )
        btn_claim.callback = self.claim_callback

        btn_close = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Đóng với lí do/ ghi chú",
            emoji="🗑️",
            custom_id="lavie_ticket_close_btn"
        )
        btn_close.callback = self.close_callback

        self.container1 = discord.ui.Container(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media="https://cdn.discordapp.com/attachments/1529018147233861674/1529285734966493204/TICKET_rep.png?ex=6a65ff13&is=6a64ad93&hm=0dbb34bf7d5fbcd448db74f9bf3e5db7214ff28e992d9bd45b7861ba9b08005f&",
                ),
            ),
            discord.ui.TextDisplay(content="# Cảm ơn bạn đã tin tưởng và sử dụng dịch vụ của chúng tôi"),
            discord.ui.TextDisplay(content="Chờ một chút và đội ngũ hỗ trợ sẽ đến hỗ trợ bạn nhé! Và hãy đảm bảo rằng bạn đã đọc kĩ luật khi tạo ticket."),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.Section(
                discord.ui.TextDisplay(
                    content=(
                        f"<:blue_point:1270403608114102304> **Ticket ID:** `{self.ticket_name}`\n"
                        f"<:blue_point:1270403608114102304> **Người mở Ticket:** {self.user.mention}\n"
                        f"<:blue_point:1270403608114102304> **Thời gian mở:** {created_timestamp}"
                    )
                ),
                accessory=discord.ui.Thumbnail(
                    media=self.user.display_avatar.url,
                ),
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="-# LAVIE - Staff sẽ hỗ trợ bạn trong vòng 24h tới"),
        )

        self.action_row1 = discord.ui.ActionRow(btn_claim, btn_close)

    async def claim_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"🤚 Staff {interaction.user.mention} đã nhận xử lý ticket này!",
            ephemeral=False
        )

    async def close_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CloseReasonModal())


# ==========================================
# 3. GIAO DIỆN BẢNG TẠO TICKET CHÍNH (LAYOUT VIEW)
# ==========================================
class MainTicketPanel(discord.ui.LayoutView):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

        btn_gopy = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Góp Ý",
            emoji="🤚",
            custom_id="lavie_btn_gopy"
        )
        btn_gopy.callback = lambda i: self.cog.handle_create_ticket(i, "gop-y")

        btn_hotro = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Hỗ Trợ",
            emoji="📩",
            custom_id="lavie_btn_hotro"
        )
        btn_hotro.callback = lambda i: self.cog.handle_create_ticket(i, "ho-tro")

        btn_muahang = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Mua Hàng",
            emoji="🛒",
            custom_id="lavie_btn_muahang"
        )
        btn_muahang.callback = lambda i: self.cog.handle_create_ticket(i, "mua-hang")

        self.container1 = discord.ui.Container(
            discord.ui.TextDisplay(content="# <a:006_heart:1506352922277974266>  KHU VỰC TICKET - LAVIE <a:006_heart:1506352922277974266>"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.Section(
                discord.ui.TextDisplay(content="##💡 GÓP Ý\n- Bạn có ý tưởng, đề xuất sự kiện, hoặc nhận xét để server ngày càng tốt hơn? Ban Quản Trị luôn trân trọng và lắng nghe mọi phản hồi từ bạn."),
                accessory=btn_gopy,
            ),
            discord.ui.Section(
                discord.ui.TextDisplay(content="## <a:pinkstarbutton:1530670605026725928>  HỖ TRỢ\n- Gặp sự cố trong server, cần hỗ trợ về quyền hạn, kênh chat, hoặc có thắc mắc cần giải đáp? Đội ngũ Staff sẽ có mặt nhanh nhất có thể."),
                accessory=btn_hotro,
            ),
            discord.ui.Section(
                discord.ui.TextDisplay(content="## <a:shopping_cart:1529770120749121666> MUA HÀNG\n- Quan tâm đến Custom ROle, vật phẩm hoặc dịch vụ server đang cung cấp? Mở ticket để được tư vấn & báo giá chi tiết."),
                accessory=btn_muahang,
            ),
            discord.ui.TextDisplay(content="<a:Warning:1530473247223578665> *Vui lòng không spam ticket hoặc mở sai mục đích*"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="-# LAVIE - Hỗ trợ 24/7"),
        )


# ==========================================
# 4. MODULE COG CHÍNH XỬ LÝ TICKET
# ==========================================
class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    ticket_group = app_commands.Group(name="ticket", description="Quản lý hệ thống Ticket hỗ trợ")

    async def handle_create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        guild = interaction.guild

        # 1. Lấy cấu hình Category
        config = db.get_ticket_config(guild.id)
        category_id = config.get("category_id") or os.getenv("GIVEAWAY_CATEGORY")

        if not category_id:
            return await interaction.response.send_message(
                "❌ Chưa cài đặt Category ticket. Dùng `/ticket category` để cài đặt.", 
                ephemeral=True
            )

        # 2. Lấy danh sách Roles Support
        raw_roles = config.get("support_role_id") or os.getenv("TICKET_SUPPORT")
        support_roles = []
        if raw_roles:
            role_id_list = [r.strip() for r in str(raw_roles).split(",") if r.strip().isdigit()]
            for r_id in role_id_list:
                role_obj = guild.get_role(int(r_id))
                if role_obj:
                    support_roles.append(role_obj)

        category = guild.get_channel(int(category_id))

        # Phân quyền kênh
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        for role in support_roles:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Tạo kênh ticket theo loại (VD: gop-y-username)
        channel_name = f"{ticket_type}-{interaction.user.name}".lower().replace(" ", "-")
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"Ticket {ticket_type} bởi {interaction.user}"
        )

        await interaction.response.send_message(f"✅ Đã tạo ticket tại {ticket_channel.mention}!", ephemeral=True)

        # Tag người dùng & các Role Support
        support_mentions = " ".join([r.mention for r in support_roles])
        mention_content = f"{interaction.user.mention} vừa mới tạo ticket nè {support_mentions}".strip()

        # Gửi bảng giao diện phản hồi vào kênh vừa tạo
        reply_view = TicketControlView(ticket_name=channel_name, user=interaction.user)
        await ticket_channel.send(content=mention_content, view=reply_view)

    @ticket_group.command(name="send", description="Gửi bảng Ticket (Góp ý / Hỗ trợ / Mua hàng) vào kênh")
    @app_commands.default_permissions(administrator=True)
    async def ticket_send(self, interaction: discord.Interaction):
        view = MainTicketPanel(cog=self)
        await interaction.channel.send(view=view)
        await interaction.response.send_message("✅ Đã gửi bảng Ticket thành công!", ephemeral=True)

    @ticket_group.command(name="category", description="Cài đặt Danh mục (Category) chứa kênh ticket")
    @app_commands.default_permissions(administrator=True)
    async def ticket_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        db.set_ticket_category(interaction.guild_id, category.id)
        await interaction.response.send_message(f"✅ Đã lưu Category chứa Ticket: **{category.name}**!", ephemeral=True)

    @ticket_group.command(name="support", description="Cài đặt các Role Staff xử lý Ticket")
    @app_commands.describe(
        role1="Role Staff chính",
        role2="Role Staff phụ 1 (Tùy chọn)",
        role3="Role Staff phụ 2 (Tùy chọn)",
        role4="Role Staff phụ 3 (Tùy chọn)",
        role5="Role Staff phụ 4 (Tùy chọn)"
    )
    @app_commands.default_permissions(administrator=True)
    async def ticket_support(
        self, 
        interaction: discord.Interaction, 
        role1: discord.Role,
        role2: discord.Role = None,
        role3: discord.Role = None,
        role4: discord.Role = None,
        role5: discord.Role = None
    ):
        selected_roles = [r for r in [role1, role2, role3, role4, role5] if r is not None]
        role_ids_str = ",".join([str(r.id) for r in selected_roles])
        db.set_ticket_support(interaction.guild_id, role_ids_str)

        roles_mention_str = " ".join([r.mention for r in selected_roles])
        await interaction.response.send_message(
            f"✅ Đã lưu `{len(selected_roles)}` Role Staff Hỗ Trợ:\n{roles_mention_str}", 
            ephemeral=True
        )

    @app_commands.command(name="close", description="Đóng và xóa kênh ticket hiện tại")
    async def close_ticket(self, interaction: discord.Interaction):
        if not any(interaction.channel.name.startswith(p) for p in ["gop-y-", "ho-tro-", "mua-hang-", "ticket-"]):
            return await interaction.response.send_message("❌ Lệnh này chỉ có thể sử dụng bên trong kênh Ticket!", ephemeral=True)

        await interaction.response.send_modal(CloseReasonModal())


async def setup(bot):
    await bot.add_cog(TicketCog(bot))