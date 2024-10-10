import os
import re
from dotenv import load_dotenv
import discord
from discord.ext import commands
import random

# Load environment variables from .env file
load_dotenv()
token = os.getenv("DISCORD_TOKEN")

# Set up bot intents
intents = discord.Intents.default()
intents.message_content = True

# Initialize the bot with a command prefix
bot = commands.Bot(command_prefix="!", intents=intents)

# In-memory counter for drop submissions
drop_counter = 1  # Start the drop counter from 1
drop_submissions = (
    {}
)  # Dictionary to track submissions in the format { "DROP-001": metadata }


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


# Drop submission command with sequential ID
@bot.command()
async def submit(ctx, image_url=None):
    global drop_counter  

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
        if not re.match(r"^https?://.*\.(jpg|jpeg|png|gif)$", image_url, re.IGNORECASE):
            await ctx.send(
                "🚫 Invalid image URL. Please use a direct link to a valid image (.jpg, .jpeg, .png, .gif)."
            )
            return

    # 4. If no URL is provided, use the first attachment
    image = image_url
    if not image and len(ctx.message.attachments) > 0:
        image = ctx.message.attachments[0].url

    # 5. Generate a sequential drop ID using the counter
    drop_id = f"DROP-{drop_counter:03}"  # Format: DROP-001, DROP-002, etc.
    drop_counter += 1  

    # 6. Post the submission in the staff-only channel
    staff_channel = discord.utils.get(ctx.guild.text_channels, name="drop-submissions")
    if not staff_channel:
        await ctx.send("🚫 Drop submission channel not found. Please contact an admin.")
        return

    # 7. Send the formatted message to the staff channel with the sequential ID
    submission_message = await staff_channel.send(
        f"**New Drop Submission from {ctx.author.mention} ({team_role}):**\nDrop ID: `{drop_id}`\n{image}"
    )

    # 8. Store the submission in the dictionary with metadata
    drop_submissions[drop_id] = {
        "message_id": submission_message.id,
        "submitter_id": ctx.author.id,
        "team_role": team_role,
        "image_url": image,
        "status": "Pending",
    }

    # 9. Delete the user's original message to keep the channel clean
    await ctx.message.delete()

    # 10. Send a confirmation message to the user
    confirmation_message = await ctx.send(
        f"✅ Your drop has been submitted with Drop ID: `{drop_id}` and is pending review in {staff_channel.mention}."
    )

    # 11. Automatically delete the confirmation message after 10 seconds
    await confirmation_message.delete(delay=10)

    # 12. Notify staff members with a role tag
    staff_role = discord.utils.get(ctx.guild.roles, name="Staff")
    if staff_role:
        await staff_channel.send(
            f"{staff_role.mention}, a new drop has been submitted for review!\n**Drop ID:** `{drop_id}`"
        )


bot.run(token)
