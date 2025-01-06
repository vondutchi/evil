import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

# Kontrollera miljövariabler och visa varningar
required_env_vars = ["DISCORD_TOKEN", "LOG_CHANNEL_ID", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]

if missing_vars:
    print(f"Warning: The following environment variables are missing: {', '.join(missing_vars)}")
    print("Some features may not work correctly.")

TOKEN = os.getenv('DISCORD_TOKEN')
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', '0'))

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix='/', intents=intents)

# Ta bort det inbyggda help-kommandot
bot.remove_command("help")

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    print("Loaded commands:")
    for command in bot.tree.get_commands():
        print(f"- {command.name}: {command.description}")
    await bot.tree.sync()

async def load():
    for filename in os.listdir('./commands'):
        if filename.endswith('.py'):
            await bot.load_extension(f'commands.{filename[:-3]}')

async def main():
    await load()
    await bot.start(TOKEN)

import asyncio
asyncio.run(main())
