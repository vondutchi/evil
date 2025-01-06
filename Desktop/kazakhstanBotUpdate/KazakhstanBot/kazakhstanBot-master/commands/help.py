from discord.ext import commands
import discord
import os
import json

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.faq_data_path = os.path.join(os.getcwd(), 'data', 'faq.json')
        self.faq_data = self.load_json(self.faq_data_path, default={})

    def load_json(self, path, default=None):
        """Ladda data från JSON-fil."""
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return default

    @commands.hybrid_command(name="help", description="Get a list of all available FAQ commands.")
    async def help(self, ctx):
        """Visa en lista med alla tillgängliga FAQ-kommandon."""
        # Ladda om FAQ-data för att säkerställa att den är uppdaterad
        self.faq_data = self.load_json(self.faq_data_path, default={})

        if not self.faq_data:
            embed = discord.Embed(
                title="No FAQs Available",
                description="There are currently no FAQ entries available. Use `/add` to create new FAQ entries.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="Available FAQ Commands",
            description="Here is a list of all available FAQ entries. Use `/faq <command>` to access the corresponding guide or information.",
            color=discord.Color.blue()
        )

        for command_key, data in self.faq_data.items():
            embed.add_field(
                name=f"/faq {command_key}",
                value=f"*{data['title']}*",
                inline=False
            )

        embed.set_footer(text="Use /faq <command> to get detailed information.")
        await ctx.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    """Lägg till HelpCog i boten."""
    await bot.add_cog(HelpCog(bot))
