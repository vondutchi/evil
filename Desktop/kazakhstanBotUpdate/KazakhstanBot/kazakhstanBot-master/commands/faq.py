from discord.ext import commands
import json
import os
import discord
import aiohttp

class FAQCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_path = os.path.join(os.getcwd(), 'data', 'faq.json')
        self.managers_path = os.path.join(os.getcwd(), 'data', 'managers.json')
        self.pending_commands = {}
        self.webhook_url = os.getenv('LOG_WEBHOOK_URL')

        # Load FAQ data
        self.faq_data = self.load_json(self.data_path)
        self.managers = self.load_json(self.managers_path, default=[])

    def load_json(self, path, default=None):
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return default

    def save_json(self, path, data):
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)

    async def log_action(self, title: str, description: str):
        if not self.webhook_url:
            return

        async with aiohttp.ClientSession() as session:
            embed = {
                "title": title,
                "description": description,
                "color": 0x00ff00
            }
            await session.post(self.webhook_url, json={"embeds": [embed]})

    @commands.hybrid_command(name="faq", description="Get help or a guide for a common issue.")
    async def faq(self, ctx: commands.Context, query: str):
        allowed_channel_ids = [int(id.strip()) for id in os.getenv('HELP_CHANNEL_ID', '0').split(',')]
        exempt_role_ids = [int(id.strip()) for id in os.getenv('EXEMPT_ROLE_ID', '0').split(',')]

        if ctx.channel.id not in allowed_channel_ids:
            if not any(role.id in exempt_role_ids for role in ctx.author.roles):
                channel_name = ', '.join([f"<#{id}>" for id in allowed_channel_ids])
                embed = discord.Embed(
                    title="Permission Denied",
                    description=f"You don’t have permission to use this command outside of {channel_name}.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed, ephemeral=True)
                return

        query_key = query.lower().replace(" ", "_")
        if query_key in self.faq_data:
            response = self.faq_data[query_key]
            embed = discord.Embed(
                title=response.get("title", "FAQ Entry"),
                description=response.get('answer', "No answer available."),
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="FAQ Not Found",
                description="The requested information is not available. Please check your query and try again.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="add", description="Add a new FAQ entry.")
    async def add(self, ctx: commands.Context, command: str, title: str):
        if ctx.author.id not in self.managers:
            embed = discord.Embed(
                title="Permission Denied",
                description="You do not have permission to add FAQ entries.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        command_key = command.lower().replace(" ", "_")
        if command_key in self.faq_data:
            embed = discord.Embed(
                title="Duplicate Command",
                description="This command already exists in the FAQ.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        self.pending_commands[ctx.author.id] = {
            "command_key": command_key,
            "title": title,
            "channel_id": ctx.channel.id
        }
        embed = discord.Embed(
            title="Pending FAQ Creation",
            description="Now send the answer for the FAQ entry in this channel.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id in self.pending_commands:
            data = self.pending_commands[message.author.id]
            if message.channel.id != data["channel_id"]:
                return

            self.pending_commands.pop(message.author.id)
            answer = message.content.strip()

            self.faq_data[data["command_key"]] = {
                "title": data["title"],
                "answer": answer
            }

            self.save_json(self.data_path, self.faq_data)

            embed = discord.Embed(
                title="New FAQ Added",
                description=f"**Title:** {data['title']}\n**Command:** /faq {data['command_key']}\n**Answer:** {answer}",
                color=discord.Color.green()
            )
            await message.channel.send(embed=embed)

            # Log action
            await self.log_action("FAQ Added", f"**Added by:** {message.author.mention}\n**Command:** /faq {data['command_key']}\n**Title:** {data['title']}\n**Answer:** {answer}")

    @commands.hybrid_command(name="addmanager", description="Add a new FAQ manager.")
    async def addmanager(self, ctx: commands.Context, member: discord.Member):
        manager_role_id = int(os.getenv('FAQ_MANAGER_ROLE_ID', '0'))

        if not any(role.id == manager_role_id for role in ctx.author.roles):
            embed = discord.Embed(
                title="Permission Denied",
                description="You do not have permission to add managers.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        if member.id in self.managers:
            embed = discord.Embed(
                title="Already a Manager",
                description=f"{member.mention} is already a manager.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        self.managers.append(member.id)
        self.save_json(self.managers_path, self.managers)

        embed = discord.Embed(
            title="Manager Added",
            description=f"{member.mention} has been added as a FAQ manager.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed, ephemeral=True)

        # Log action
        await self.log_action("Manager Added", f"**Added by:** {ctx.author.mention}\n**Manager:** {member.mention}")

    @commands.hybrid_command(name="removemanager", description="Remove a FAQ manager.")
    async def removemanager(self, ctx: commands.Context, member: discord.Member):
        manager_role_id = int(os.getenv('FAQ_MANAGER_ROLE_ID', '0'))

        if not any(role.id == manager_role_id for role in ctx.author.roles):
            embed = discord.Embed(
                title="Permission Denied",
                description="You do not have permission to remove managers.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        if member.id not in self.managers:
            embed = discord.Embed(
                title="Not a Manager",
                description=f"{member.mention} is not a manager.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        self.managers.remove(member.id)
        self.save_json(self.managers_path, self.managers)

        embed = discord.Embed(
            title="Manager Removed",
            description=f"{member.mention} has been removed as a FAQ manager.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed, ephemeral=True)

        # Log action
        await self.log_action("Manager Removed", f"**Removed by:** {ctx.author.mention}\n**Manager:** {member.mention}")

    @commands.hybrid_command(name="remove", description="Remove a FAQ entry.")
    async def remove(self, ctx: commands.Context, command: str):
        if ctx.author.id not in self.managers:
            embed = discord.Embed(
                title="Permission Denied",
                description="You do not have permission to remove FAQ entries.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        command_key = command.lower().replace(" ", "_")
        if command_key not in self.faq_data:
            embed = discord.Embed(
                title="Command Not Found",
                description="This command does not exist in the FAQ.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        del self.faq_data[command_key]
        self.save_json(self.data_path, self.faq_data)

        embed = discord.Embed(
            title="FAQ Entry Removed",
            description=f"The FAQ entry `{command}` has been successfully removed.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed, ephemeral=True)

        # Log action
        await self.log_action("FAQ Removed", f"**Removed by:** {ctx.author.mention}\n**Command:** /faq {command}")

async def setup(bot: commands.Bot):
    await bot.add_cog(FAQCog(bot))
