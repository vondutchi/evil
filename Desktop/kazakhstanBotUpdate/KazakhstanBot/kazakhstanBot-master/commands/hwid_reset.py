import discord
from discord.ext import commands
import asyncpg
import aiohttp
import asyncio
import logging
import json
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables with default values
LOG_CHANNEL_ID = os.getenv('LOG_CHANNEL_ID')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')  # Default PostgreSQL port
DB_NAME = os.getenv('DB_NAME', 'default_db')
DB_USER = os.getenv('DB_USER', 'default_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'default_password')

# Check if required variables are missing and log warnings
missing_vars = []
if not LOG_CHANNEL_ID:
    missing_vars.append("LOG_CHANNEL_ID")
if not DB_HOST or not DB_PORT or not DB_NAME or not DB_USER or not DB_PASSWORD:
    missing_vars += ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]

if missing_vars:
    logger.warning(f"Warning: The following environment variables are missing or incomplete: {', '.join(missing_vars)}")

# Convert DB_PORT to integer safely
try:
    DB_PORT = int(DB_PORT)
except ValueError:
    logger.warning("DB_PORT is not a valid integer. Using default value 5432.")
    DB_PORT = 5432

async def connect_db() -> asyncpg.Connection:
    """Connect to the database."""
    try:
        return await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    except asyncpg.InvalidAuthorizationSpecificationError as e:
        logger.error("Invalid database credentials: Check your username or password.")
        raise e
    except asyncpg.ConnectionDoesNotExistError as e:
        logger.error("Database host or port is incorrect. Ensure the database server is accessible.")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error occurred while connecting to the database: {str(e)}")
        raise e

async def reset_hwid(identifier: str, service: str, session: aiohttp.ClientSession, db_conn: asyncpg.Connection, requester: str) -> tuple[str, str, bool]:
    """Reset the HWID for a given user in a specific service."""
    if service == 'vanity':
        table_name = "AuthUserData"
        base_url = "http://vanitycheats.xyz/UserAuthentication.php"
        logo_path = "images/vanity.png"
    elif service == 'mesa':
        table_name = "AuthUserData-Mesachanger.com"
        base_url = "http://mesachanger.com/UserAuthentication.php"
        logo_path = "images/mesa.png"
    else:
        return f"Invalid service: {service}", "", False

    user_id = await fetch_user_id(identifier, base_url, session) if not identifier.isdigit() else int(identifier)
    if user_id is None or user_id == -1:
        logger.error(f"User {identifier} not found.")
        return f"**HWID reset failed for user {identifier}. Invalid username or user does not exist.**", logo_path, False

    query = f"""
        UPDATE public."{table_name}"
        SET "StorageIdentifier" = NULL, "BootIdentifier" = NULL
        WHERE "UID" = $1
    """
    await db_conn.execute(query, user_id)

    logger.info(f"HWID for user {identifier} (ID: {user_id}) has been reset in {service}. Requested by: {requester}.")
    return f"HWID for user **{identifier}** (ID: **{user_id}**) has been reset in {service}.", logo_path, True

async def fetch_user_id(username: str, base_url: str, session: aiohttp.ClientSession) -> int:
    """Fetch the user ID from the authentication service."""
    async with session.post(base_url, data={'username': username}) as response:
        if response.status == 200:
            try:
                user_data = json.loads(await response.text())
                return int(user_data.get('id', -1))
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON from {base_url}.")
                return -1
        else:
            logger.error(f"Failed to fetch user ID from {base_url}. Status code: {response.status}")
            return -1

class HWIDResetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def has_permissions(self, ctx: commands.Context) -> bool:
        """Check if the user has the required permissions."""
        allowed_roles = {"Moderator", "Administrator"}
        user_roles = {role.name for role in ctx.author.roles}
        return bool(allowed_roles & user_roles)

    @commands.hybrid_command(name='mesa_reset', description='Reset HWID for Mesa users.')
    async def mesa_reset(self, ctx: commands.Context, identifiers: str):
        """Reset HWID for Mesa users."""
        if not self.has_permissions(ctx):
            await self.send_permission_error(ctx)
            return
        await self.handle_reset(ctx, identifiers.split(','), 'mesa')

    @commands.hybrid_command(name='vanity_reset', description='Reset HWID for Vanity users.')
    async def vanity_reset(self, ctx: commands.Context, identifiers: str):
        """Reset HWID for Vanity users."""
        if not self.has_permissions(ctx):
            await self.send_permission_error(ctx)
            return
        await self.handle_reset(ctx, identifiers.split(','), 'vanity')

    async def handle_reset(self, ctx: commands.Context, identifiers: list[str], service: str):
        """Handle the HWID reset process."""
        requester = ctx.author.name
        async with aiohttp.ClientSession() as session:
            try:
                db_conn = await connect_db()
                results = []
                all_failed = True
                for identifier in identifiers:
                    result, logo_path, success = await reset_hwid(identifier.strip(), service, session, db_conn, requester)
                    all_failed = all_failed and not success
                    results.append(result)
                await db_conn.close()

                result_message = "\n".join(results)
                color = discord.Color.green() if not all_failed else discord.Color.red()
                embed = discord.Embed(
                    title="HWID Reset",
                    description=result_message,
                    color=color
                )
                embed.add_field(name="Service", value=service.capitalize(), inline=True)
                embed.add_field(name="Initiator", value=ctx.author.mention, inline=True)
                embed.add_field(name="Usernames/IDs", value=", ".join(identifiers), inline=False)
                embed.set_thumbnail(url=f"attachment://{os.path.basename(logo_path)}")
                await ctx.send(file=discord.File(logo_path), embed=embed, ephemeral=all_failed)
                await self.log_reset(ctx, identifiers, service, result_message)
            except Exception as e:
                logger.error(f"Error during HWID reset: {str(e)}")
                await ctx.send(f"An error occurred during the reset process: {str(e)}")

    async def log_reset(self, ctx: commands.Context, identifiers: list[str], service: str, result_message: str):
        """Log the HWID reset in the specified log channel."""
        log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title=f"HWID Reset Log | {service.capitalize()}",
                description=f"HWID reset performed by {ctx.author.mention} for service **{service.capitalize()}**.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Identifiers", value=", ".join(identifiers), inline=False)
            embed.add_field(name="Results", value=result_message, inline=False)
            embed.set_footer(text=f"User ID: {ctx.author.id}")
            await log_channel.send(embed=embed)

    async def send_permission_error(self, ctx: commands.Context):
        """Send a permission error message."""
        embed = discord.Embed(
            title="Insufficient Permissions",
            description="You do not have the required permissions to use this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    """Set up the HWIDResetCog."""
    await bot.add_cog(HWIDResetCog(bot))
