import os
from dotenv import load_dotenv
import discord
from discord.ext import commands


load_dotenv()
token = os.getenv("DISCORD_TOKEN")

# intents
intents = discord.Intents.default()
intents.message_content = True  

# specified intents
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")


@bot.command()
async def hello(ctx):
    await ctx.send("Hello! I'm your new bot.")


@bot.command()
async def ping(ctx):
    await ctx.send("Pong! 🏓")


bot.run(token)
