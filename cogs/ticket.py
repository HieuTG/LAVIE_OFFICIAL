import os
import asyncio
import io
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
        await interaction.response.defer() # Phản hồi trước để có thời gian xử lý Transcript
        
        close_reason = self.reason.value if self.reason.value else "Không có ghi chú"
        channel = interaction.channel
        guild = interaction.guild

        # 1. Lấy dữ liệu người mở ticket (Dựa vào tag ở tin nhắn đầu tiên của Bot)
        opener_mention = "`Không rõ`"
        messages = [message async for message in channel.history(limit=None, oldest_first=True)]
        
        if messages and messages[0].author == interaction.client.user and messages[0].mentions:
            opener_mention = messages[0].mentions[0].mention

        # 2. Xây dựng nội dung file Transcript .txt
        transcript_content = f"TRANSCRIPT TICKET: #{channel.name}\n"
        transcript_content += f"Server: {guild.name}\n"
        transcript_content += f"Thời gian xuất log: {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M:%S')}\n"
        transcript_content += "=" * 60 + "\n\n"

        for msg in messages:
            timestamp = msg.created_at.strftime('%d/%m/%Y %H:%M:%S')
            content = msg.content
            if msg.attachments:
                content += f" [Đính kèm {len(msg.attachments)} tệp]"
            transcript_content += f"[{timestamp}] {msg.author.name}: {content}\n"

        transcript_file = discord.File(
            io.BytesIO(transcript_content.encode('utf-8')), 
            filename=f"transcript-{channel.name}.txt"
        )

        # 3. Gửi Log vào channel Ticket Log (Theo Database hoặc .env)
        config = db.get_guild_config(guild.id)
        log_channel_id = config.get("ticket_logs_id") or os.getenv("TICKET_LOGS_CHANNEL")

        if log_channel_id:
            log_channel = guild.get_channel(int(log_channel_id))
            if log_channel:
                open_time_str = f"<t:{int(channel.created_at.timestamp())}:f>"
                close_time_str = f"<t:{int(discord.utils.utcnow().timestamp())}:f>"

                embed_log = discord.Embed(
                    title="📋 LOGS TICKET ĐÃ ĐÓNG",
                    color=0x2b2d31 # Màu nền tối đồng bộ Discord
                )
                
                embed_log.add_field(name="🏷️ Tên Ticket", value=f"`#{channel.name}`", inline=True)
                embed_log.add_field(name="👤 Người mở", value=opener_mention, inline=True)
                embed_log.add_field(name="🔒 Người đóng", value=interaction.user.mention, inline=True)
                
                embed_log.add_field(name="⏰ Mở lúc", value=open_time_str, inline=True)
                embed_log.add_field(name="⏰ Đóng lúc", value=close_time_str, inline=True)
                embed_log.add_field(name="\u200b", value="\u200b", inline=True) # Cột rỗng để cân bằng bố cục 3 cột
                
                embed_log.add_field(name="📝 Ghi chú / Lý do", value=f"```\n{close_reason}\n```", inline=False)
                
                embed_log.set_footer(text=f"ID Kênh: {channel.id}")

                await log_channel.send(embed=embed_log, file=transcript_file)

        # 4. Gửi thông báo xóa kênh
        await interaction.followup.send(
            f"🔒 **Ticket này sẽ tự động xóa sau 5 giây...**\n📝 **Lý do/Ghi chú:** {close_reason}"
        )
        
        await asyncio.sleep(5)
        await channel.delete(reason=f"Đóng ticket bởi {interaction.user}: {close_reason}")


# ==========================================
# 2. GIAO DIỆN BÊN TRONG KÊNH TICKET (LAYOUT VIEW)
# ==========================================
class TicketControlView(discord.ui.LayoutView):
    def __init__(self, ticket_name: str = "Ticket", user: discord.User = None):
        super().__init__(timeout=None)
        self.ticket_name = ticket_name
        self.user = user

        created_timestamp = f"<t:{int(discord.utils.utcnow().timestamp())}:F>"
        user_mention = user.mention if user else "Người dùng"
        
        # Nếu user chưa được truyền vào (khi khởi tạo persistent view), dùng avatar mặc định của Discord
        avatar_url = user.display_avatar.url if user else "https://cdn.discordapp.com/embed/avatars/0.png"

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

        text_section = (
            f"<:blue_point:1270403608114102304> **Ticket ID:** `{self.ticket_name}`\n"
            f"<:blue_point:1270403608114102304> **Người mở Ticket:** {user_mention}\n"
            f"<:blue_point:1270403608114102304> **Thời gian mở:** {created_timestamp}"
        )

        # Đảm bảo accessory luôn luôn được truyền vào Section
        ticket_section = discord.ui.Section(
            discord.ui.TextDisplay(content=text_section),
            accessory=discord.ui.Thumbnail(media=avatar_url)
        )

        self.container1 = discord.ui.Container(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media="https://cdn.discordapp.com/attachments/1529018147233861674/1529285734966493204/TICKET_rep.png?ex=6a65ff13&is=6a64ad93&hm=0dbb34bf7d5fbcd448db74f9bf3e5db7214ff28e992d9bd45b7861ba9b08005f&",
                ),
            ),
            discord.ui.TextDisplay(content="# Cảm ơn bạn đã tin tưởng và sử dụng dịch vụ của chúng tôi"),
            discord.ui.TextDisplay(content="Chờ một chút và đội ngũ hỗ trợ sẽ đến hỗ trợ bạn nhé! Và hãy đảm bảo rằng bạn đã đọc kĩ luật khi tạo ticket."),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            ticket_section,
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="-# LAVIE - Staff sẽ hỗ trợ bạn trong vòng 24h tới"),
        )

        self.action_row1 = discord.ui.ActionRow(btn_claim, btn_close)

        self.add_item(self.container1)
        self.add_item(self.action_row1)

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
    def __init__(self): # Bỏ tham số cog
        super().__init__(timeout=None) # timeout=None giúp View không bị hết hạn

        btn_gopy = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Góp Ý",
            emoji="<a:PinkRightArrowBounce:1503069364029493382>",
            custom_id="lavie_btn_gopy"
        )
        btn_gopy.callback = lambda i: self.handle_click(i, "gop-y")

        btn_hotro = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Hỗ Trợ",
            emoji="<a:PinkRightArrowBounce:1503069364029493382>",
            custom_id="lavie_btn_hotro"
        )
        btn_hotro.callback = lambda i: self.handle_click(i, "ho-tro")

        btn_muahang = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="Mua Hàng",
            emoji="<a:PinkRightArrowBounce:1503069364029493382>",
            custom_id="lavie_btn_muahang"
        )
        btn_muahang.callback = lambda i: self.handle_click(i, "mua-hang")

        self.container1 = discord.ui.Container(
            discord.ui.TextDisplay(content="# <a:006_heart:1506352922277974266>  KHU VỰC TICKET - LAVIE <a:006_heart:1506352922277974266>"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.Section(
                discord.ui.TextDisplay(content="## 💡 GÓP Ý\n- Bạn có ý tưởng, đề xuất sự kiện, hoặc nhận xét để server ngày càng tốt hơn? Ban Quản Trị luôn trân trọng và lắng nghe mọi phản hồi từ bạn."),
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
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media="https://images-ext-1.discordapp.net/external/lNVjpYCXpb8KSRBNBlcj2gXWJXeK6iyfWktDc4haEG4/https/i.pinimg.com/originals/57/06/f6/5706f64a52a9409137084f2dc44d11dd.gif",
                ),
            ),
            discord.ui.TextDisplay(content="<a:Warning:1530473247223578665> *Vui lòng không spam ticket hoặc mở sai mục đích*"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="-# LAVIE - Hỗ trợ 24/7"),
        )

        self.add_item(self.container1)

    # Hàm xử lý lấy Cog động từ interaction
    async def handle_click(self, interaction: discord.Interaction, ticket_type: str):
        cog = interaction.client.get_cog("TicketCog")
        if cog:
            await cog.handle_create_ticket(interaction, ticket_type)
        else:
            await interaction.response.send_message("❌ Hệ thống Ticket tạm thời không khả dụng.", ephemeral=True)

# ==========================================
# 4. MODULE COG CHÍNH XỬ LÝ TICKET
# ==========================================
class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    ticket_group = app_commands.Group(name="ticket", description="Quản lý hệ thống Ticket hỗ trợ")

    async def handle_create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        guild = interaction.guild

        config = db.get_guild_config(guild.id)
        category_id = config.get("ticket_category_id")

        if not category_id:
            return await interaction.response.send_message(
                "❌ Chưa cài đặt Category ticket. Dùng `/ticket category` để cài đặt.", 
                ephemeral=True
            )

        raw_roles = config.get("ticket_support_role_id") or os.getenv("TICKET_SUPPORT")
        support_roles = []
        if raw_roles:
            role_id_list = [r.strip() for r in str(raw_roles).split(",") if r.strip().isdigit()]
            for r_id in role_id_list:
                role_obj = guild.get_role(int(r_id))
                if role_obj:
                    support_roles.append(role_obj)

        category = guild.get_channel(int(category_id))

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        for role in support_roles:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"{ticket_type}-{interaction.user.name}".lower().replace(" ", "-")
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"Ticket {ticket_type} bởi {interaction.user}"
        )

        await interaction.response.send_message(f"✅ Đã tạo ticket tại {ticket_channel.mention}!", ephemeral=True)

        support_mentions = " ".join([r.mention for r in support_roles])
        mention_content = f"{interaction.user.mention} vừa mới tạo ticket nè {support_mentions}".strip()

        await ticket_channel.send(content=mention_content)

        reply_view = TicketControlView(ticket_name=channel_name, user=interaction.user)
        await ticket_channel.send(view=reply_view)

    @ticket_group.command(name="send", description="Gửi bảng Ticket (Góp ý / Hỗ trợ / Mua hàng) vào kênh")
    @app_commands.default_permissions(administrator=True)
    async def ticket_send(self, interaction: discord.Interaction):
        view = MainTicketPanel() # Đã bỏ (cog=self)
        await interaction.channel.send(view=view)
        await interaction.response.send_message("✅ Đã gửi bảng Ticket thành công!", ephemeral=True)

    @ticket_group.command(name="category", description="Cài đặt Danh mục (Category) chứa kênh ticket")
    @app_commands.default_permissions(administrator=True)
    async def ticket_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        db.set_server_setting(interaction.guild_id, "ticket_category_id", category.id)
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
        db.set_server_setting(interaction.guild_id, "ticket_support_role_id", role_ids_str)

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

    bot.add_view(MainTicketPanel())
    bot.add_view(TicketControlView())