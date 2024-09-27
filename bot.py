import os
from dotenv import load_dotenv
import discord
from discord.ext import commands

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

bot = commands.Bot(command_prefix="!")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")


@bot.command()
async def hello(ctx):
    await ctx.send("Hello! I'm your new bot.")


bot.run(token)
