import discord
from discord.ext import commands
import random
import time
import asyncio
import os
import io
from datetime import datetime

# ==========================================
# 0. HÀM HỖ TRỢ LẤY ROLE PING TỪ .ENV
# ==========================================
def get_support_pings():
    """Đọc danh sách ID role từ TICKET_SUPPORT trong .env và chuyển thành chuỗi ping"""
    roles_env = os.getenv("TICKET_SUPPORT", "")
    if not roles_env:
        return ""
    
    pings = []
    for role_id_str in roles_env.split(","):
        role_id_str = role_id_str.strip()
        if role_id_str.isdigit():
            pings.append(f"<@&{role_id_str}>")
            
    return " ".join(pings)


# ==========================================
# 1. BẢNG FORM ĐIỀN LÝ DO ĐÓNG TICKET (MODAL)
# ==========================================
class CloseTicketModal(discord.ui.Modal, title="🔒 Đóng Ticket & Ghi Chú"):
    reason = discord.ui.TextInput(
        label="Lý do / Ghi chú đóng ticket:",
        style=discord.TextStyle.paragraph,
        placeholder="Nhập lý do đóng ticket hoặc ghi chú xử lý tại đây...",
        required=False,
        max_length=500
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        note = self.reason.value.strip() or "Không có ghi chú."
        await self.cog.close_ticket_with_transcript(interaction, note)


# ==========================================
# 2. CÁC VIEW GIAO DIỆN COMPONENT V2
# ==========================================

class TicketSetupView(discord.ui.LayoutView):    
    def __init__(self):
        super().__init__(timeout=None)
        # Giao diện chính theo mẫu mới
        container1 = discord.ui.Container(
            discord.ui.TextDisplay(content="# <a:006_heart:1506352922277974266>  KHU VỰC TICKET - LAVIE <a:006_heart:1506352922277974266>"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.Section(
                discord.ui.TextDisplay(content="## 💡 GÓP Ý\n- Bạn có ý tưởng, đề xuất sự kiện, hoặc nhận xét để server ngày càng tốt hơn? Ban Quản Trị luôn trân trọng và lắng nghe mọi phản hồi từ bạn."),
                accessory=discord.ui.Button(
                    style=discord.ButtonStyle.secondary,
                    label="Góp Ý",
                    emoji="<a:PinkRightArrowBounce:1524817060608086067>",
                    custom_id="e9f8143aac3f41a0c9eb64f3fa9050ef",
                ),
            ),
            discord.ui.Section(
                discord.ui.TextDisplay(content="## <a:pinkstarbutton:1530670605026725928>  HỖ TRỢ\n- Gặp sự cố trong server, cần hỗ trợ về quyền hạn, kênh chat, hoặc có thắc mắc cần giải đáp? Đội ngũ Staff sẽ có mặt nhanh nhất có thể."),
                accessory=discord.ui.Button(
                    style=discord.ButtonStyle.secondary,
                    label="Hỗ Trợ",
                    emoji="<a:PinkRightArrowBounce:1524817060608086067>",
                    custom_id="1c5eeafa69fc49e9ed483c387a30565f",
                ),
            ),
            discord.ui.Section(
                discord.ui.TextDisplay(content="## <a:shopping_cart:1529770120749121666> MUA HÀNG\n- Quan tâm đến Custom ROle, vật phẩm hoặc dịch vụ server đang cung cấp? Mở ticket để được tư vấn & báo giá chi tiết."),
                accessory=discord.ui.Button(
                    style=discord.ButtonStyle.secondary,
                    label="Mua Hàng",
                    emoji="<a:PinkRightArrowBounce:1524817060608086067>",
                    custom_id="6025a6b1be4d46fd96b87db4e8d839dd",
                ),
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.MediaGallery(
                            discord.MediaGalleryItem(
                                media="https://i.pinimg.com/originals/57/06/f6/5706f64a52a9409137084f2dc44d11dd.gif",
                            ),
                        ),
            discord.ui.TextDisplay(content="<a:Warning:1530473247223578665> *Vui lòng không spam ticket hoặc mở sai mục đích*"),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="-# LAVIE - Hỗ trợ 24/7"),
        )
        self.add_item(container1)


class TicketReplyView(discord.ui.LayoutView):    
    def __init__(self, user: discord.Member, ticket_name: str, created_at: int, status: str = ""):
        super().__init__(timeout=None)
        
        # Tạo chuỗi thông tin ticket kèm trạng thái (nếu đã được claim)
        info_content = (
            f"<:blue_point:1270403608114102304> **Ticket ID:** #{ticket_name}\n"
            f"<:blue_point:1270403608114102304> **Người mở Ticket:** {user.mention}\n"
            f"<:blue_point:1270403608114102304> **Thời gian mở:** <t:{created_at}:f> (<t:{created_at}:R>)"
        )
        if status:
            info_content += f"\n<:blue_point:1270403608114102304> **Trạng thái:** {status}"

        # Lấy avatar của người dùng làm Thumbnail, nếu không có dùng avatar mặc định
        avatar_url = user.display_avatar.url

        container1 = discord.ui.Container(
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(
                    media="https://cdn.discordapp.com/attachments/1529018147233861674/1529285734966493204/TICKET_rep.png?ex=6a65ff13&is=6a64ad93&hm=0dbb34bf7d5fbcd448db74f9bf3e5db7214ff28e992d9bd45b7861ba9b08005f&",
                ),
            ),
            discord.ui.TextDisplay(content="## Cảm ơn bạn đã tin tưởng chúng tôi"),
            discord.ui.TextDisplay(content="Chờ một chút và đội ngũ hỗ trợ sẽ đến hỗ trợ bạn nhé! Và hãy đảm bảo rằng bạn đã đọc kĩ luật khi tạo ticket."),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.Section(
                discord.ui.TextDisplay(content=info_content),
                accessory=discord.ui.Thumbnail(media=avatar_url),
            ),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content="-# LAVIE - Staff sẽ hỗ trợ bạn trong vòng 24h tới"),
        )
        
        action_row1 = discord.ui.ActionRow(
            discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label="Claim",
                emoji="🤚",
                custom_id="a31bd47b7d6b428ca50fdabc913f68e4",
            ),
            discord.ui.Button(
                style=discord.ButtonStyle.danger,
                label="Đóng với lí do/ ghi chú",
                emoji="🗑️",
                custom_id="89b6aee964664284a1d382b0ad6dd58e",
            ),
        )
        
        self.add_item(container1)
        self.add_item(action_row1)


# ==========================================
# 3. XỬ LÝ LÔ-GÍC MODULE TICKET
# ==========================================

class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(TicketSetupView())

    @commands.group(invoke_without_command=True)
    async def ticket(self, ctx):
        await ctx.send("⚠️ Cú pháp chưa đúng. Dùng: `!ticket set <#channel>`")

    @ticket.command(name="set")
    @commands.has_permissions(administrator=True)
    async def ticket_set(self, ctx, channel: discord.TextChannel):
        """Thiết lập bảng tạo ticket"""
        await channel.send(view=TicketSetupView())
        await ctx.send(f"✅ Đã thiết lập bảng Tạp Hóa LAVIE tại {channel.mention}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
            
        custom_id = interaction.data.get("custom_id")
        
        # --- CÁC NÚT TẠO TICKET GÓP Ý / HỖ TRỢ / MUA HÀNG ---
        if custom_id == "e9f8143aac3f41a0c9eb64f3fa9050ef":
            await self.process_ticket(interaction, "góp-ý")
        elif custom_id == "1c5eeafa69fc49e9ed483c387a30565f":
            await self.process_ticket(interaction, "hỗ-trợ")
        elif custom_id == "6025a6b1be4d46fd96b87db4e8d839dd":
            await self.process_ticket(interaction, "mua-hàng")
            
        # --- NÚT CLAIM (TIẾP NHẬN TICKET) ---
        elif custom_id == "a31bd47b7d6b428ca50fdabc913f68e4":
            try:
                history = [msg async for msg in interaction.channel.history(limit=5, oldest_first=True)]
                original_user = history[0].mentions[0] if history and history[0].mentions else interaction.user
            except Exception:
                original_user = interaction.user

            created_timestamp = int(interaction.channel.created_at.timestamp())
            status_text = f"✅ Đã tiếp nhận bởi {interaction.user.mention}"
            
            # Cập nhật lại View với trạng thái Claim
            new_view = TicketReplyView(original_user, interaction.channel.name, created_timestamp, status=status_text)
            await interaction.response.edit_message(view=new_view)
            await interaction.followup.send(f"🤚 Staff {interaction.user.mention} đã tiếp nhận (claim) hỗ trợ ticket này!")
            
        # --- NÚT ĐÓNG TICKET VỚI LÝ DO ---
        elif custom_id == "89b6aee964664284a1d382b0ad6dd58e":
            is_admin = interaction.user.guild_permissions.administrator
            is_manage = interaction.user.guild_permissions.manage_channels
            
            if not (is_admin or is_manage):
                return await interaction.response.send_message(
                    "❌ Bạn không có quyền đóng ticket! Chỉ Administrator hoặc Staff được giao quyền mới có thể thực hiện.",
                    ephemeral=True
                )
                
            await interaction.response.send_modal(CloseTicketModal(self))

    async def process_ticket(self, interaction: discord.Interaction, prefix: str):
        guild = interaction.guild
        user = interaction.user
        category = interaction.channel.category
        
        ticket_id = random.randint(1000, 9999)
        channel_name = f"{prefix}-{ticket_id}"

        # 1. Cấp quyền cơ bản (Người tạo, Bot và chặn @everyone)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        # 2. Cấp quyền xem cho các role trong biến môi trường TICKET_SUPPORT
        roles_env = os.getenv("TICKET_SUPPORT", "")
        if roles_env:
            for role_id_str in roles_env.split(","):
                role_id_str = role_id_str.strip()
                if role_id_str.isdigit():
                    role = guild.get_role(int(role_id_str))
                    if role:
                        # Cấp quyền cho role đọc & gửi tin nhắn vào trong dictionary overwrites
                        overwrites[role] = discord.PermissionOverwrite(
                            view_channel=True, 
                            send_messages=True, 
                            attach_files=True
                        )

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name, 
                category=category, 
                overwrites=overwrites
            )
            
            await interaction.response.send_message(f"✅ Đã tạo {ticket_channel.mention}", ephemeral=True)
            
            # Tạo chuỗi ping người dùng cùng các role support từ .env
            support_pings = get_support_pings()
            ping_message = f"{user.mention} vừa mới tạo ticket nè {support_pings}".strip()
            await ticket_channel.send(ping_message)
            
            # Gửi giao diện Component V2
            current_time = int(time.time())
            view_instance = TicketReplyView(user=user, ticket_name=channel_name, created_at=current_time)
            await ticket_channel.send(view=view_instance)
            
        except discord.Forbidden:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Bot không có quyền tạo kênh, vui lòng kiểm tra lại role!", ephemeral=True)

    async def close_ticket_with_transcript(self, interaction: discord.Interaction, note: str):
        channel = interaction.channel
        guild = interaction.guild
        
        transcript_lines = [
            "==================================================",
            f"TRANSCRIPT TICKET: #{channel.name}",
            f"Server: {guild.name}",
            f"Thời gian xuất log: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            "==================================================\n"
        ]
        
        opener = None
        
        async for msg in channel.history(limit=None, oldest_first=True):
            if not opener and msg.mentions:
                opener = msg.mentions[0]
                
            time_str = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            author_str = f"{msg.author.name}"
            content = msg.clean_content or ""
            
            if msg.attachments:
                attachments_str = " ".join([att.url for att in msg.attachments])
                content += f" [File đính kèm: {attachments_str}]"
                
            transcript_lines.append(f"[{time_str}] {author_str}: {content}")
            
        transcript_text = "\n".join(transcript_lines)
        file_buffer = io.BytesIO(transcript_text.encode('utf-8'))
        file = discord.File(file_buffer, filename=f"transcript-{channel.name}.txt")
        
        logs_channel_env = os.getenv("TICKET_LOGS_CHANNEL")
        
        if logs_channel_env:
            try:
                logs_channel_id = int(logs_channel_env)
                logs_channel = guild.get_channel(logs_channel_id)
                
                if logs_channel:
                    created_ts = int(channel.created_at.timestamp())
                    closed_ts = int(time.time())
                    
                    embed = discord.Embed(
                        title="📋 LOGS TICKET ĐÃ ĐÓNG",
                        color=0x2b2d31,
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="🎫 Tên Ticket", value=f"`#{channel.name}`", inline=True)
                    embed.add_field(name="👤 Người mở", value=opener.mention if opener else "Không xác định", inline=True)
                    embed.add_field(name="🔒 Người đóng", value=interaction.user.mention, inline=True)
                    embed.add_field(name="⏰ Mở lúc", value=f"<t:{created_ts}:f>", inline=True)
                    embed.add_field(name="⏰ Đóng lúc", value=f"<t:{closed_ts}:f>", inline=True)
                    embed.add_field(name="📝 Ghi chú / Lý do", value=f"```{note}```", inline=False)
                    embed.set_footer(text=f"ID Kênh: {channel.id}")
                    
                    await logs_channel.send(file=file, embed=embed)
            except ValueError:
                print("⚠️ [Warning] TICKET_LOGS_CHANNEL trong file .env không phải là ID chữ số hợp lệ!")

        await interaction.followup.send("🗑️ Đã ghi nhận logs! Kênh ticket này sẽ bị xóa sau 3 giây...")
        await asyncio.sleep(3)
        await channel.delete()


async def setup(bot):
    await bot.add_cog(TicketCog(bot))