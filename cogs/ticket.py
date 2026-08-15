import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import database as db

# --- GIAO DIỆN NÚT BẤM (BUTTON VIEW) ---
class TicketView(discord.ui.View):
    def __init__(self):
        # timeout=None giúp nút duy trì hoạt động kể cả khi bot restart
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Tạo Ticket Hỗ Trợ", 
        style=discord.ButtonStyle.primary, 
        custom_id="lavie_create_ticket_btn", 
        emoji="🎫"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        
        # 1. Lấy cấu hình từ Database hoặc .env
        config = db.get_ticket_config(guild.id)
        category_id = config.get("category_id")
        
        if not category_id:
            env_category = os.getenv("GIVEAWAY_CATEGORY")
            category_id = int(env_category) if env_category else None

        if not category_id:
            return await interaction.response.send_message(
                "❌ Hệ thống chưa được thiết lập Danh mục (Category) ticket. Vui lòng báo Admin dùng lệnh `/ticket category`.", 
                ephemeral=True
            )

        # 2. Xử lý lấy danh sách nhiều Role Staff Support (DB hoặc .env)
        raw_roles = config.get("support_role_id") or os.getenv("TICKET_SUPPORT")
        support_roles = []
        
        if raw_roles:
            # Hỗ trợ cả ID dạng số đơn lẻ, dạng chuỗi "123,456", hoặc list
            role_id_list = [r.strip() for r in str(raw_roles).split(",") if r.strip().isdigit()]
            for r_id in role_id_list:
                role_obj = guild.get_role(int(r_id))
                if role_obj:
                    support_roles.append(role_obj)

        category = guild.get_channel(category_id)

        # Thiết lập quyền hạn cơ bản cho Kênh Ticket
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        # Cấp quyền xem & nhắn tin cho tất cả các Role Staff Support
        for role in support_roles:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Tạo kênh ticket mới
        channel_name = f"ticket-{interaction.user.name}".lower().replace(" ", "-")
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"Ticket được tạo bởi {interaction.user}"
        )

        await interaction.response.send_message(f"✅ Đã tạo ticket hỗ trợ tại {ticket_channel.mention}!", ephemeral=True)

        # Tạo chuỗi tag tất cả role support
        support_mentions = " ".join([r.mention for r in support_roles])

        # Gửi Embed chào mừng trong kênh vừa tạo
        embed = discord.Embed(
            title="🎫 TRUNG TÂM HỖ TRỢ LAVIE",
            description=f"Xin chào {interaction.user.mention},\nVui lòng trình bày thắc mắc hoặc yêu cầu của bạn.\nĐội ngũ hỗ trợ sẽ phản hồi trong thời gian sớm nhất.\n\n*Dùng lệnh `/close` để đóng ticket khi hoàn tất.*",
            color=discord.Color.blue()
        )
        await ticket_channel.send(content=f"{interaction.user.mention} {support_mentions}".strip(), embed=embed)


# --- CLASS TICKET COG MAIN ---
class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Khởi tạo nhóm lệnh Slash Group: /ticket ...
    ticket_group = app_commands.Group(name="ticket", description="Quản lý hệ thống Ticket hỗ trợ")

    @ticket_group.command(name="send", description="Gửi bảng nút bấm tạo Ticket vào kênh hiện tại")
    @app_commands.default_permissions(administrator=True)
    async def ticket_send(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎫 TẠO TICKET HỖ TRỢ",
            description="Bạn gặp vấn đề cần trợ giúp hoặc góp ý cho Server?\nNhấn vào nút **Tạo Ticket Hỗ Trợ** bên dưới để mở kênh trò chuyện riêng với Ban Quản Trị.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Tạp hóa LAVIE • Hệ thống hỗ trợ tự động")
        
        await interaction.channel.send(embed=embed, view=TicketView())
        await interaction.response.send_message("✅ Đã gửi bảng tạo Ticket thành công!", ephemeral=True)

    @ticket_group.command(name="category", description="Cài đặt Danh mục (Category) chứa kênh ticket")
    @app_commands.default_permissions(administrator=True)
    async def ticket_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        db.set_ticket_category(interaction.guild_id, category.id)
        await interaction.response.send_message(f"✅ Đã lưu Category chứa Ticket: **{category.name}** vào Database!", ephemeral=True)

    @ticket_group.command(name="support", description="Cài đặt các Role Staff xử lý Ticket (Có thể chọn tối đa 5 role)")
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
        # Lọc danh sách các role không None
        selected_roles = [r for r in [role1, role2, role3, role4, role5] if r is not None]
        role_ids_str = ",".join([str(r.id) for r in selected_roles])

        # Lưu chuỗi ID dạng "1234,5678" vào database
        db.set_ticket_support(interaction.guild_id, role_ids_str)

        roles_mention_str = " ".join([r.mention for r in selected_roles])
        await interaction.response.send_message(
            f"✅ Đã lưu `{len(selected_roles)}` Role Staff Hỗ Trợ vào Database:\n{roles_mention_str}", 
            ephemeral=True
        )

    # --- LỆNH KIỂM SOÁT TICKET (CLOSE / RENAME) ---

    @app_commands.command(name="close", description="Đóng và xóa kênh ticket hiện tại")
    async def close_ticket(self, interaction: discord.Interaction):
        if not interaction.channel.name.startswith("ticket-"):
            return await interaction.response.send_message("❌ Lệnh này chỉ có thể sử dụng bên trong kênh Ticket!", ephemeral=True)

        await interaction.response.send_message("🔒 **Ticket này sẽ tự động xóa sau 5 giây...**")
        
        # Gửi log vào channel Ticket Log nếu có cài trong .env
        log_channel_id = os.getenv("TICKET_LOGS_CHANNEL")
        if log_channel_id:
            log_channel = interaction.guild.get_channel(int(log_channel_id))
            if log_channel:
                embed_log = discord.Embed(
                    title="📝 TICKET CLOSED",
                    description=f"Kênh: `{interaction.channel.name}`\nNgười đóng: {interaction.user.mention}",
                    color=discord.Color.red()
                )
                await log_channel.send(embed=embed_log)

        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Đóng ticket bởi {interaction.user}")

    @app_commands.command(name="rename", description="Đổi tên kênh ticket hiện tại")
    @app_commands.describe(new_name="Tên mới cho ticket (Ví dụ: da-giai-quyet)")
    async def rename_ticket(self, interaction: discord.Interaction, new_name: str):
        if not interaction.channel.name.startswith("ticket-"):
            return await interaction.response.send_message("❌ Lệnh này chỉ có thể sử dụng bên trong kênh Ticket!", ephemeral=True)

        formatted_name = f"ticket-{new_name.lower().replace(' ', '-')}"
        old_name = interaction.channel.name
        
        await interaction.channel.edit(name=formatted_name, reason=f"Đổi tên bởi {interaction.user}")
        await interaction.response.send_message(f"✅ Đã đổi tên kênh từ `{old_name}` ➔ `{formatted_name}`")


# --- ĐĂNG KÝ COG VÀ PERSISTENT VIEW ---
async def setup(bot):
    await bot.add_cog(TicketCog(bot))
    # Đăng ký View để nút bấm không bị "chết" sau khi restart bot
    bot.add_view(TicketView())