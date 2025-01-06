from discord.ext import commands
import discord
import os
import json

class StaffHelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="staff", description="Lists all commands available for staff members.")
    async def staff(self, ctx: commands.Context):
        """Send a help embed with all staff-specific commands and required permissions."""
        # Define staff commands with required permissions
        staff_commands = [
            {
                "name": "/mesa_reset",
                "description": "Reset HWID for Mesa users.",
                "permission": "Moderator"
            },
            {
                "name": "/vanity_reset",
                "description": "Reset HWID for Vanity users.",
                "permission": "Moderator"
            },
            {
                "name": "/addmanager",
                "description": "Add a new FAQ manager.",
                "permission": "Administrator"
            },
            {
                "name": "/removemanager",
                "description": "Remove an existing FAQ manager.",
                "permission": "Administrator"
            },
            {
                "name": "/add",
                "description": "Add a new FAQ entry.",
                "permission": "FAQ Manager"
            },
            {
                "name": "/remove",
                "description": "Remove an existing FAQ entry.",
                "permission": "FAQ Manager"
            }
        ]

        # Get exempt role IDs from environment variables
        exempt_role_ids = {
            int(role_id.strip()) for role_id in os.getenv("EXEMPT_ROLE_ID", "").split(",") if role_id.strip().isdigit()
        }

        # Check user's roles
        user_role_ids = {role.id for role in ctx.author.roles}

        embed = discord.Embed(
            title="Staff Commands",
            description="Here are the available staff commands and their required permissions:",
            color=discord.Color.blue()
        )

        if exempt_role_ids & user_role_ids:  # User has one of the exempt roles
            for command in staff_commands:
                embed.add_field(
                    name=f"{command['name']} (Permission: {command['permission']})",
                    value=command["description"],
                    inline=False
                )
        else:
            embed.description = "You don't have access to any staff commands!"

        await ctx.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(StaffHelpCog(bot))
