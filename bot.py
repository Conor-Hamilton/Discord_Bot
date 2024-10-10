import os
import re
from dotenv import load_dotenv
import discord
from discord.ext import commands
import random

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

drop_counter = 1
drop_submissions = {}


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


# Drop submission command
@bot.command()
async def submit(ctx, image_url=None):
    global drop_counter

    # Restrict to the specific channel
    if ctx.channel.name != "drop-submissions":
        await ctx.send(
            "🚫 You can only use the `!submit` command in the `#drop-submissions` channel."
        )
        return

    # Check for valid team role
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

    # Ensure an image URL or attachment is provided
    if not image_url and len(ctx.message.attachments) == 0:
        await ctx.send(
            "⚠️ Please provide an image URL or attach a screenshot of your drop with the command."
        )
        return

    # Validate the image URL if provided
    if image_url:
        if not re.match(r"^https?://.*\.(jpg|jpeg|png|gif)$", image_url, re.IGNORECASE):
            await ctx.send(
                "🚫 Invalid image URL. Please use a direct link to a valid image (.jpg, .jpeg, .png, .gif)."
            )
            return

    # Handle attachments properly
    image = image_url
    if not image and len(ctx.message.attachments) > 0:
        attachment = ctx.message.attachments[0]
        print(
            f"Attachment Debug Info: {attachment.filename}, {attachment.content_type}, {attachment.size}"
        )
        print(f"Attachment URL: {attachment.url}")

        # Use the attachment if it is a valid image type
        if attachment.content_type and attachment.content_type.startswith("image/"):
            image = attachment.url
            print(f"Using Attachment URL: {image}")
        else:
            await ctx.send(
                "🚫 The attached file is not a valid image. Please upload an image file (.jpg, .png, .gif)."
            )
            return

    drop_id = f"DROP-{drop_counter:03}"
    drop_counter += 1

    # Use the staff-review channel for submissions
    staff_channel = discord.utils.get(ctx.guild.text_channels, name="staff-review")
    if not staff_channel:
        await ctx.send("🚫 Staff review channel not found. Please contact an admin.")
        return

    # Post the drop submission in the staff-review channel
    submission_message = await staff_channel.send(
        f"**New Drop Submission from {ctx.author.mention} ({team_role}):**\nDrop ID: `{drop_id}`\n{image}"
    )

    drop_submissions[drop_id] = {
        "message_id": submission_message.id,
        "submitter_id": ctx.author.id,
        "team_role": team_role,
        "image_url": image,
        "status": "Pending",
    }

    await ctx.message.delete()

    confirmation_message = await ctx.send(
        f"✅ Your drop has been submitted with Drop ID: `{drop_id}` and is pending review in {staff_channel.mention}."
    )
    await confirmation_message.delete(delay=10)

    staff_role = discord.utils.get(ctx.guild.roles, name="Staff")
    if staff_role:
        await staff_channel.send(
            f"{staff_role.mention}, a new drop has been submitted for review!\n**Drop ID:** `{drop_id}`"
        )


bot.run(token)
