import discord
from discord.ext import commands
import aiohttp
import datetime
import os
import json
import pytz  # <-- tidszonshantering
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ALLOWED_ROLE_ID = int(os.getenv("ALLOWED_ROLE_ID", "0"))

class SelfReset(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reset_limit = 2
        self.data_path = os.path.join(os.getcwd(), 'data', 'reset_logs.json')

        if not os.path.exists(os.path.dirname(self.data_path)):
            os.makedirs(os.path.dirname(self.data_path))
        if not os.path.exists(self.data_path):
            with open(self.data_path, 'w') as f:
                json.dump({}, f)

    async def fetch_uid(self, username, base_url):
        """Hämta användarens UID som integer"""
        async with aiohttp.ClientSession() as session:
            async with session.post(base_url, data={'username': username}) as response:
                if response.status == 200:
                    try:
                        user_data = await response.json(content_type=None)
                        return int(user_data.get('id', -1))
                    except (json.JSONDecodeError, ValueError, TypeError):
                        return -1
                else:
                    return -1

    async def log_to_webhook(
        self,
        username,
        uid,
        service,
        logo_path,
        success,
        reason,
        resets_left,
        next_reset_date=None
    ):
        """Loggar HWID-reset till en Discord-webhook."""
        if not WEBHOOK_URL:
            return

        # Välj titel, färg och huvudtext beroende på success/fail
        if success:
            title = "✅ HWID Self Reset Log"
            description = "A self-reset action was successfully performed."
            color = discord.Color.green()
        else:
            title = "❌ HWID Self Reset Failure Log"
            description = f"{reason}."
            color = discord.Color.red()

        # Skapa embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            # Vi låter Discords egna tidsstämpel vara UTC i bakgrunden:
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(name="👤 **User**", value=username, inline=True)
        embed.add_field(name="🛠️ **Service**", value=service.capitalize(), inline=True)
        embed.add_field(name="🔑 **UID**", value=str(uid) if uid is not None else "N/A", inline=True)

        if next_reset_date:
            embed.add_field(name="📅 **Next Reset Available**", value=next_reset_date, inline=False)
        elif success:
            embed.add_field(name="📅 **Resets Left**", value=str(resets_left), inline=False)

        # Sätt fotnot med dagens datum/tid i CET
        cet_tz = pytz.timezone("CET")
        now_cet = datetime.datetime.now(cet_tz).strftime('%Y-%m-%d %H:%M:%S')
        embed.set_footer(text=f"Date: {now_cet} CET")

        embed.set_thumbnail(url=f"attachment://{os.path.basename(logo_path)}")

        async with aiohttp.ClientSession() as session:
            with open(logo_path, 'rb') as logo_file:
                form_data = aiohttp.FormData()
                form_data.add_field(
                    'payload_json',
                    json.dumps({
                        "embeds": [embed.to_dict()],
                        "username": "HWID Reset Bot",  # Webhook-namn
                    })
                )
                form_data.add_field('file', logo_file, filename=os.path.basename(logo_path))
                await session.post(WEBHOOK_URL, data=form_data)

    @commands.hybrid_command(name="self_reset", description="Reset your HWID for Mesa or Vanity.")
    async def self_reset_command(self, ctx: commands.Context, service: str):
        """
        Reset HWID för en specifik tjänst via slash-kommando:
        /self_reset <service>
        """
        await ctx.defer(ephemeral=True)

        user_roles = [role.id for role in ctx.author.roles]
        username = ctx.author.display_name

        # Kolla om användaren har rätt roll
        if ALLOWED_ROLE_ID not in user_roles:
            logo_path = "images/vanity.png" if service.lower() == 'vanity' else "images/mesa.png"
            embed = discord.Embed(
                title="❌ Access Denied",
                description=(
                    "You do not have the required role to use this command. "
                    "Please make sure you have an active subscription."
                ),
                color=discord.Color.red(),
            )
            embed.set_footer(text=f"User: {username} • UserID: {ctx.author.id}")
            embed.set_thumbnail(url=f"attachment://{os.path.basename(logo_path)}")

            await ctx.send(embed=embed, ephemeral=True)
            await self.log_to_webhook(
                username, None, service, logo_path,
                success=False, reason="User lacks required role",
                resets_left=0
            )
            return

        if service.lower() not in ["mesa", "vanity"]:
            await ctx.send("Invalid service. Specify 'mesa' or 'vanity'.", ephemeral=True)
            return

        if not username:
            await ctx.send("Set your Display Name to match your service username.", ephemeral=True)
            return

        logo_path = "images/vanity.png" if service.lower() == 'vanity' else "images/mesa.png"
        base_url = (
            "http://vanitycheats.xyz/UserAuthentication.php"
            if service.lower() == 'vanity' else
            "http://mesachanger.com/UserAuthentication.php"
        )

        uid = await self.fetch_uid(username, base_url)
        if uid == -1:
            embed = discord.Embed(
                title="❌ HWID Reset Failed",
                description=(
                    "Make sure that you entered the right service name "
                    "(and that your subscription is active)."
                ),
                color=discord.Color.red(),
            )
            embed.set_footer(text=f"User: {username} • UserID: {ctx.author.id}")
            embed.set_thumbnail(url=f"attachment://{os.path.basename(logo_path)}")

            await ctx.send(embed=embed, ephemeral=True)
            await self.log_to_webhook(
                username, uid, service, logo_path,
                success=False, reason="Invalid UID or service",
                resets_left=0
            )
            return

        # Hantera reset-logs
        with open(self.data_path, 'r+') as f:
            try:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
            except json.JSONDecodeError:
                data = {}

            user_data = data.get(str(ctx.author.id), {"username": username, service: []})
            user_resets = user_data.get(service, [])

            # Filtrera bort resets äldre än 30 dagar
            recent_resets = [
                datetime.datetime.strptime(date, '%Y-%m-%d')
                for date in user_resets
                if (datetime.datetime.now() - datetime.datetime.strptime(date, '%Y-%m-%d')).days <= 30
            ]

            if len(recent_resets) >= self.reset_limit:
                next_reset_date = (
                    min(recent_resets) + datetime.timedelta(days=30)
                ).strftime('%Y-%m-%d')

                embed = discord.Embed(
                    title="❌ Reset Limit Reached",
                    description=(
                        f"You have reached the reset limit of **2 resets per 30 days** "
                        f"for **{service.capitalize()}**.\n\n"
                        f"**Next Reset Available:** {next_reset_date}\n\n"
                        f"For more information, run `/faq hwid_reset`."
                    ),
                    color=discord.Color.red(),
                )
                embed.set_footer(text=f"User: {username} • UserID: {ctx.author.id}")
                embed.set_thumbnail(url=f"attachment://{os.path.basename(logo_path)}")

                await ctx.send(embed=embed, ephemeral=True)
                await self.log_to_webhook(
                    username, uid, service, logo_path,
                    success=False, reason="Reset limit reached",
                    resets_left=0,
                    next_reset_date=next_reset_date
                )
                return

            # Lägg till en ny reset
            user_resets.append(datetime.datetime.now().strftime('%Y-%m-%d'))
            user_data["username"] = username
            user_data[service] = user_resets
            data[str(ctx.author.id)] = user_data

            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()

        # Beräkna återstående resets
        resets_left = self.reset_limit - len(recent_resets) - 1

        # Meddelande till användaren – Lyckad reset
        embed = discord.Embed(
            title="✅ HWID Reset Successful",
            description="Your HWID has been successfully reset.",
            color=discord.Color.green(),
        )
        embed.add_field(name="🔑 **UID**", value=str(uid), inline=True)
        embed.add_field(name="📅 **Resets Left**", value=str(resets_left), inline=True)
        embed.set_footer(text=f"User: {username} • UserID: {ctx.author.id}")
        embed.set_thumbnail(url=f"attachment://{os.path.basename(logo_path)}")

        await ctx.send(embed=embed, file=discord.File(logo_path), ephemeral=True)

        # Skicka även loggen till din webhook
        await self.log_to_webhook(
            username, uid, service, logo_path,
            success=True,
            reason="Successful reset",
            resets_left=resets_left
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(SelfReset(bot))
