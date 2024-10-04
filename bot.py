import os
import re
from dotenv import load_dotenv
import discord
from discord.ext import commands
import random


load_dotenv()
token = os.getenv("DISCORD_TOKEN")

# intents
intents = discord.Intents.default()
intents.message_content = True

# specified intents
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Bingo! 🎱"))
    print(f"Logged in as {bot.user}!")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("That command does not exist! 😅")
    else:
        await ctx.send(f"An unexpected error occurred: {error}")


@bot.command()
async def hello(ctx):
    await ctx.send("Hello! I'm your new bot.")


@bot.command()
async def ping(ctx):
    await ctx.send("Pong! 🏓")


@bot.command()
async def roll(ctx):
    dice_roll = random.randint(1, 6)
    await ctx.send(f"🎲 You rolled a {dice_roll}!")


# submissions


# Drop submission command
@bot.command()
async def submit(ctx, image_url=None):
    # 1. Check if the user has a valid team role such as "Team 1", "Team 2", etc.
    team_role = next(
        (
            role.name
            for role in ctx.author.roles
            if role.name.lower().startswith("team")
        ),
        None,
    )
    if not team_role:
        await ctx.send(
            "⛔ You don't seem to have a valid team role. Please contact a staff member."
        )
        return

    # 2. Check if the user provided an image URL or attached an image
    if not image_url and len(ctx.message.attachments) == 0:
        await ctx.send(
            "⚠️ Please provide an image URL or attach a screenshot of your drop with the command."
        )
        return

    # 3. Validate the provided URL (if any)
    if image_url:
        # Basic validation to check if the URL ends with a common image extension
        if not re.match(r"^https?://.*\.(jpg|jpeg|png|gif)$", image_url, re.IGNORECASE):
            await ctx.send(
                "🚫 Invalid image URL. Please use a direct link to a valid image (.jpg, .jpeg, .png, .gif)."
            )
            return

    # 4. If no URL is provided, use the first attachment
    image = image_url
    if not image and len(ctx.message.attachments) > 0:
        image = ctx.message.attachments[0].url

    # 5. Post the submission in the staff-only channel
    staff_channel = discord.utils.get(ctx.guild.text_channels, name="drop-submissions")
    if not staff_channel:
        await ctx.send("🚫 Drop submission channel not found. Please contact an admin.")
        return

    # 6. Send the formatted message to the staff channel
    submission_message = await staff_channel.send(
        f"**New Drop Submission from {ctx.author.mention} ({team_role}):**\n{image}"
    )

    # 7. Delete the user's original message to keep the channel clean
    await ctx.message.delete()

    # 8. Send a confirmation message to the user
    confirmation_message = await ctx.send(
        f"✅ Your drop has been submitted and is pending review in {staff_channel.mention}."
    )

    # 9. Automatically delete the confirmation message after 10 seconds
    await confirmation_message.delete(delay=10)

    # 10. Notify staff members with a role tag
    staff_role = discord.utils.get(ctx.guild.roles, name="Staff")
    if staff_role:
        await staff_channel.send(
            f"{staff_role.mention}, a new drop has been submitted for review!"
        )


bot.run(token)
