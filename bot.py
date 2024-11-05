import os
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
async def roll(ctx):
    dice_roll = random.randint(1, 6)
    await ctx.send(f"🎲 You rolled a {dice_roll}!")


# Drop submission command
@bot.command()
async def submit(ctx, image_url=None):
    global drop_counter, drop_submissions

    if ctx.channel.name != "drop-submissions":
        await ctx.send(
            "🚫 You can only use the `!submit` command in the `#drop-submissions` channel."
        )
        return

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

    if not image_url and len(ctx.message.attachments) == 0:
        await ctx.send(
            "⚠️ Please provide an image URL or attach a screenshot of your drop with the command."
        )
        return

    image = image_url
    if not image and len(ctx.message.attachments) > 0:
        attachment = ctx.message.attachments[0]
        print(
            f"Attachment Debug Info: {attachment.filename}, {attachment.content_type}, {attachment.size}"
        )
        print(f"Attachment URL: {attachment.url}")

        image = attachment.url
        print(f"Using Attachment URL: {image}")

    drop_id = f"DROP-{drop_counter:03}"
    drop_counter += 1

    staff_channel = discord.utils.get(ctx.guild.text_channels, name="staff-review")
    if not staff_channel:
        await ctx.send("🚫 Staff review channel not found. Please contact an admin.")
        return

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


# Drop confirm command
@bot.command()
async def confirm(ctx, drop_id: str):
    global drop_submissions

    drop_id = drop_id.upper()

    if drop_id not in drop_submissions:
        await ctx.send(f"⚠️ Drop ID `{drop_id}` not found.")
        return

    drop_data = drop_submissions[drop_id]
    staff_channel = discord.utils.get(ctx.guild.text_channels, name="staff-review")
    if not staff_channel:
        await ctx.send("🚫 Staff review channel not found. Please contact an admin.")
        return

    submission_message = await staff_channel.fetch_message(drop_data["message_id"])

    await submission_message.add_reaction("✅")

    team_channel = discord.utils.get(
        ctx.guild.text_channels, name=drop_data["team_role"].lower().replace(" ", "-")
    )
    if not team_channel:
        await ctx.send(f"🚫 Team channel for {drop_data['team_role']} not found.")
        return

    await team_channel.send(
        f"✅ Your drop with ID `{drop_id}` has been **approved** by staff!\nHere is your original submission:\n{drop_data['image_url']}"
    )
    await ctx.send(f"✅ Drop `{drop_id}` has been approved!")


# Drop reject command
@bot.command()
async def reject(ctx, drop_id: str, *, reason: str = "No reason provided"):
    global drop_submissions

    drop_id = drop_id.upper()

    if drop_id not in drop_submissions:
        await ctx.send(f"⚠️ Drop ID `{drop_id}` not found.")
        return

    drop_data = drop_submissions[drop_id]
    staff_channel = discord.utils.get(ctx.guild.text_channels, name="staff-review")
    if not staff_channel:
        await ctx.send("🚫 Staff review channel not found. Please contact an admin.")
        return

    submission_message = await staff_channel.fetch_message(drop_data["message_id"])

    await submission_message.add_reaction("❌")

    team_channel = discord.utils.get(
        ctx.guild.text_channels, name=drop_data["team_role"].lower().replace(" ", "-")
    )
    if not team_channel:
        await ctx.send(f"🚫 Team channel for {drop_data['team_role']} not found.")
        return

    submitter_id = drop_data["submitter_id"]
    try:
        submitter = await bot.fetch_user(submitter_id)
    except discord.NotFound:
        await ctx.send(
            f"⚠️ Could not find the user who submitted drop `{drop_id}`. They may have left the server."
        )
        return

    await team_channel.send(
        f"❌ {submitter.mention}, your drop with ID `{drop_id}` has been **rejected** by staff.\n"
        f"**Reason:** {reason}\nHere is your original submission:\n{drop_data['image_url']}"
    )

    await ctx.send(f"❌ Drop `{drop_id}` has been rejected with reason: {reason}")


bot.run(token)
