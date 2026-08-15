import discord
from discord.ext import commands
from discord import app_commands

# ==========================================
# 1. TẠO DROPDOWN MENU (SELECT VIEW)
# ==========================================
class HelpSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot, guild: discord.Guild, author: discord.User):
        self.bot = bot
        self.guild = guild
        self.author = author

        options = [
            discord.SelectOption(
                label="Trang Chủ",
                value="home",
                description="Tổng quan hệ thống và hướng dẫn chung",
                emoji="🏡"
            ),
            discord.SelectOption(
                label="Giveaway & Nuke",
                value="giveaway",
                description="Các lệnh tổ chức Giveaway và Nuke kênh",
                emoji="🎉"
            ),
            discord.SelectOption(
                label="Custom Roles",
                value="customrole",
                description="Các lệnh quản lý Custom Role có thời hạn",
                emoji="🎫"
            )
        ]
        super().__init__(
            placeholder="📂 Chọn danh mục lệnh cần tra cứu...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("⛔ Bạn không thể điều khiển menu trợ giúp của người khác!", ephemeral=True)

        icon_url = self.guild.icon.url if (self.guild and self.guild.icon) else None
        selected = self.values[0]

        if selected == "home":
            embed = discord.Embed(
                title="<:lavie1:1534553030937018530><:lavie2:1534553133446070482><:lavie3:1534553194502557718><:lavie4:1534553262504808488><:lavie5:1534553319111000085>",
                description=(
                    "### 📚 HỆ THỐNG TRỢ GIÚP BOT L A V I E\n"
                    "Chọn danh mục từ **Dropdown Menu** bên dưới để xem danh sách chi tiết từng nhóm lệnh.\n\n"
                    "**Danh mục khả dụng:**\n"
                    "• 🏡 **Trang Chủ:** Tổng quan hệ thống.\n"
                    "• 🎉 **Giveaway & Nuke:** Tạo/Quản lý sự kiện quà tặng & Dọn dẹp kênh.\n"
                    "• 🎫 **Custom Roles:** Tạo và gia hạn vai trò tùy chỉnh có thời hạn."
                ),
                color=discord.Color.from_str("#00FFFF")
            )

        elif selected == "giveaway":
            embed = discord.Embed(
                title="🎉 Danh Mục: Giveaway & Nuke",
                description="Tổng hợp các lệnh quản lý sự kiện Giveaway và dọn dẹp kênh:",
                color=discord.Color.from_str("#00FFFF")
            )
            embed.add_field(
                name="`/giveaway start`",
                value="Tạo Giveaway mới (Các tham số: `time_str`, `prize`, `winners`, `required_role`).",
                inline=False
            )
            embed.add_field(
                name="`!ga end [Link/ID tin nhắn]`",
                value="Kết thúc sớm Giveaway gần nhất hoặc theo Link/ID tin nhắn được chỉ định.",
                inline=False
            )
            embed.add_field(
                name="`!ga reroll [Link/ID tin nhắn]`",
                value="Quay lại người chiến thắng cho Giveaway đã kết thúc.",
                inline=False
            )
            embed.add_field(
                name="`!nuke`",
                value="Xóa toàn bộ tin nhắn bằng cách Clone & Re-create kênh hiện tại (Chỉ hoạt động trong Category được cho phép).",
                inline=False
            )

        elif selected == "customrole":
            embed = discord.Embed(
                title="🎫 Danh Mục: Custom Roles",
                description="Tổng hợp các lệnh quản lý vai trò tùy chỉnh thời hạn dành cho Staff:",
                color=discord.Color.from_str("#00FFFF")
            )
            embed.add_field(
                name="`/customrole list`",
                value="Hiển thị danh sách tất cả Custom Roles dạng bảng giao diện tương tác (Component V2).",
                inline=False
            )
            embed.add_field(
                name="`/customrole add`",
                value="Cấp Custom Role cho thành viên kèm số ngày hết hạn (VD: `30d` hoặc `30`).",
                inline=False
            )
            embed.add_field(
                name="`/customrole renew`",
                value="Gia hạn thêm số ngày sử dụng cho Custom Role hiện có.",
                inline=False
            )
            embed.add_field(
                name="`/customrole delete`",
                value="Xóa hoàn toàn Custom Role khỏi Server và Database.",
                inline=False
            )

        embed.set_footer(text=f"L A V I E • Yêu cầu bởi {self.author.display_name}", icon_url=icon_url)
        await interaction.response.edit_message(embed=embed)


class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot, guild: discord.Guild, author: discord.User):
        super().__init__(timeout=120)
        self.add_item(HelpSelect(bot, guild, author))


# ==========================================
# 2. MODULE COG CHÍNH
# ==========================================
class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- PREFIX COMMAND: !help / !trogiup ---
    @commands.command(name="help", aliases=["trogiup"])
    async def help_prefix(self, ctx: commands.Context):
        """Hiển thị menu trợ giúp dạng Dropdown Menu"""
        icon_url = ctx.guild.icon.url if (ctx.guild and ctx.guild.icon) else None
        
        embed = discord.Embed(
            title="<:lavie1:1534553030937018530><:lavie2:1534553133446070482><:lavie3:1534553194502557718><:lavie4:1534553262504808488><:lavie5:1534553319111000085>",
            description=(
                "### 📚 HỆ THỐNG TRỢ GIÚP BOT L A V I E\n"
                "Chọn danh mục từ **Dropdown Menu** bên dưới để xem danh sách chi tiết từng nhóm lệnh.\n\n"
                "**Danh mục khả dụng:**\n"
                "• 🏡 **Trang Chủ:** Tổng quan hệ thống.\n"
                "• 🎉 **Giveaway & Nuke:** Tạo/Quản lý sự kiện quà tặng & Dọn dẹp kênh.\n"
                "• 🎫 **Custom Roles:** Tạo và gia hạn vai trò tùy chỉnh có thời hạn."
            ),
            color=discord.Color.from_str("#00FFFF")
        )
        embed.set_footer(text=f"L A V I E • Yêu cầu bởi {ctx.author.display_name}", icon_url=icon_url)

        view = HelpView(self.bot, ctx.guild, ctx.author)
        await ctx.reply(embed=embed, view=view)

    # --- SLASH COMMAND: /help ---
    @app_commands.command(name="help", description="Hiển thị bảng hướng dẫn sử dụng bot dạng Dropdown Menu")
    async def help_slash(self, interaction: discord.Interaction):
        icon_url = interaction.guild.icon.url if (interaction.guild and interaction.guild.icon) else None
        
        embed = discord.Embed(
            title="<:lavie1:1534553030937018530><:lavie2:1534553133446070482><:lavie3:1534553194502557718><:lavie4:1534553262504808488><:lavie5:1534553319111000085>",
            description=(
                "### 📚 HỆ THỐNG TRỢ GIÚP BOT L A V I E\n"
                "Chọn danh mục từ **Dropdown Menu** bên dưới để xem danh sách chi tiết từng nhóm lệnh.\n\n"
                "**Danh mục khả dụng:**\n"
                "• 🏡 **Trang Chủ:** Tổng quan hệ thống.\n"
                "• 🎉 **Giveaway & Nuke:** Tạo/Quản lý sự kiện quà tặng & Dọn dẹp kênh.\n"
                "• 🎫 **Custom Roles:** Tạo và gia hạn vai trò tùy chỉnh có thời hạn."
            ),
            color=discord.Color.from_str("#00FFFF")
        )
        embed.set_footer(text=f"L A V I E • Yêu cầu bởi {interaction.user.display_name}", icon_url=icon_url)

        view = HelpView(self.bot, interaction.guild, interaction.user)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    if bot.get_command("help"):
        bot.remove_command("help")
    await bot.add_cog(HelpCog(bot))