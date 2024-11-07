import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import random
import json

DATA_FILE = "drop_data.json"
thumbnail_url = "https://imgur.com/a/Lj2gWd7"


def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            return data.get("drop_counter", 1), data.get("drop_submissions", {})
    except FileNotFoundError:
        return 1, {}


def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(
            {"drop_counter": drop_counter, "drop_submissions": drop_submissions},
            f,
            indent=4,
        )


load_dotenv()
token = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

drop_counter = 1
drop_submissions = {}

drop_counter, drop_submissions = load_data()


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Bingo! 🎱"))
    print(f"Logged in as {bot.user}!")


@bot.event
async def on_command_error(ctx, error):
    await ctx.message.delete()
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("That command does not exist! 😅")
    else:
        await ctx.send(f"An unexpected error occurred: {error}")


@bot.command()
async def roll(ctx):
    await ctx.message.delete()
    dice_roll = random.randint(1, 6)
    await ctx.send(f"🎲 You rolled a {dice_roll}!")


@bot.command()
async def submit(ctx, image_url=None):
    global drop_counter, drop_submissions

    if ctx.channel.name != "drop-submissions":
        error_message = await ctx.send(
            "🚫 You can only use the `!submit` command in the `#drop-submissions` channel."
        )
        await error_message.delete(delay=10)
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
        error_message = await ctx.send(
            "⛔ You don't seem to have a valid team role. Please contact a staff member."
        )
        await error_message.delete(delay=10)
        return

    if len(ctx.message.attachments) > 1:
        error_message = await ctx.send(
            "🚫 Only one attachment is allowed per submission. Please attach only one image."
        )
        await error_message.delete(delay=10)
        return

    image = image_url
    if not image and len(ctx.message.attachments) == 1:
        image = ctx.message.attachments[0].url
    if not image:
        error_message = await ctx.send(
            "⚠️ Please provide an image URL or attach a screenshot of your drop with the command."
        )
        await error_message.delete(delay=10)
        return

    drop_id = f"DROP-{drop_counter:03}"
    drop_counter += 1

    staff_channel = discord.utils.get(ctx.guild.text_channels, name="staff-review")
    if not staff_channel:
        error_message = await ctx.send(
            "🚫 Staff review channel not found. Please contact an admin."
        )
        await error_message.delete(delay=10)
        return

    embed = discord.Embed(
        title=f"New Drop Submission from {ctx.author} ({team_role}):",
        description=f"Drop ID: `{drop_id}`",
        color=discord.Color.blue(),
    )
    embed.set_image(url=image)
    embed.set_thumbnail(url=thumbnail_url)

    submission_message = await staff_channel.send(embed=embed)

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

    team_channel = discord.utils.get(
        ctx.guild.text_channels, name=team_role.lower().replace(" ", "-")
    )
    if team_channel:
        await team_channel.send(
            f"📥 {ctx.author.mention}, your drop with ID `{drop_id}` has been submitted and is currently under review by the staff team."
        )
    else:
        await ctx.send(f"🚫 Team channel for {team_role} not found.")

    save_data()


@bot.command()
@commands.has_role("Staff")
async def confirm(ctx, drop_id: str, *, comment: str = None):
    global drop_submissions

    drop_id = drop_id.upper()
    await ctx.message.delete()

    if drop_id not in drop_submissions:
        error_message = await ctx.send(f"⚠️ Drop ID `{drop_id}` not found.")
        await error_message.delete(delay=10)
        return

    drop_data = drop_submissions[drop_id]

    if drop_data["status"] != "Pending":
        error_message = await ctx.send(
            f"⚠️ Drop `{drop_id}` has already been {drop_data['status'].lower()} by staff member <@{drop_data['staff_member_id']}>."
        )
        await error_message.delete(delay=10)
        return

    drop_data["status"] = "Confirmed"
    drop_data["staff_member_id"] = ctx.author.id

    staff_channel = discord.utils.get(ctx.guild.text_channels, name="staff-review")
    if not staff_channel:
        error_message = await ctx.send(
            "🚫 Staff review channel not found. Please contact an admin."
        )
        await error_message.delete(delay=10)
        return

    submission_message = await staff_channel.fetch_message(drop_data["message_id"])
    await submission_message.add_reaction("✅")

    team_channel = discord.utils.get(
        ctx.guild.text_channels, name=drop_data["team_role"].lower().replace(" ", "-")
    )
    if not team_channel:
        error_message = await ctx.send(
            f"🚫 Team channel for {drop_data['team_role']} not found."
        )
        await error_message.delete(delay=10)
        return

    embed = discord.Embed(
        title=f"✅ Drop Approved!",
        description=f"**Drop ID:** `{drop_id}`\n**Approved by:** {ctx.author.mention}",
        color=discord.Color.green(),
    )
    embed.set_image(url=drop_data["image_url"])
    embed.set_thumbnail(url=thumbnail_url)
    if comment:
        embed.add_field(name="Comment", value=comment, inline=False)

    await team_channel.send(embed=embed)
    confirmation_message = await ctx.send(f"✅ Drop `{drop_id}` has been approved!")
    await confirmation_message.delete(delay=10)

    save_data()


@bot.command()
@commands.has_role("Staff")
async def reject(ctx, drop_id: str, *, reason: str = "No reason provided"):
    global drop_submissions

    drop_id = drop_id.upper()
    await ctx.message.delete()

    if drop_id not in drop_submissions:
        error_message = await ctx.send(f"⚠️ Drop ID `{drop_id}` not found.")
        await error_message.delete(delay=10)
        return

    drop_data = drop_submissions[drop_id]

    if drop_data["status"] != "Pending":
        error_message = await ctx.send(
            f"⚠️ Drop `{drop_id}` has already been {drop_data['status'].lower()} by staff member <@{drop_data['staff_member_id']}>."
        )
        await error_message.delete(delay=10)
        return

    drop_data["status"] = "Rejected"
    drop_data["staff_member_id"] = ctx.author.id

    staff_channel = discord.utils.get(ctx.guild.text_channels, name="staff-review")
    if not staff_channel:
        error_message = await ctx.send(
            "🚫 Staff review channel not found. Please contact an admin."
        )
        await error_message.delete(delay=10)
        return

    submission_message = await staff_channel.fetch_message(drop_data["message_id"])
    await submission_message.add_reaction("❌")

    team_channel = discord.utils.get(
        ctx.guild.text_channels, name=drop_data["team_role"].lower().replace(" ", "-")
    )
    if not team_channel:
        error_message = await ctx.send(
            f"🚫 Team channel for {drop_data['team_role']} not found."
        )
        await error_message.delete(delay=10)
        return

    submitter_id = drop_data["submitter_id"]
    try:
        submitter = await bot.fetch_user(submitter_id)
    except discord.NotFound:
        error_message = await ctx.send(
            f"⚠️ Could not find the user who submitted drop `{drop_id}`. They may have left the server."
        )
        await error_message.delete(delay=10)
        return

    embed = discord.Embed(
        title=f"❌ Drop Rejected",
        description=f"**Drop ID:** `{drop_id}`\n**Rejected by:** {ctx.author.mention}",
        color=discord.Color.red(),
    )
    embed.set_image(url=drop_data["image_url"])
    embed.set_thumbnail(url=thumbnail_url)
    embed.add_field(name="Reason", value=reason, inline=False)

    await team_channel.send(f"{submitter.mention}", embed=embed)
    rejection_message = await ctx.send(
        f"❌ Drop `{drop_id}` has been rejected with reason: {reason}"
    )
    await rejection_message.delete(delay=10)

    save_data()


@bot.command()
async def reset_data(ctx):
    owner_id = 252465642802774017

    if ctx.author.id != owner_id:
        await ctx.send("⛔ You do not have permission to use this command.")
        await ctx.message.delete(delay=5)
        return

    confirmation_message = await ctx.send(
        "⚠️ Are you sure you want to reset all drop data? Type `!confirm_reset` to proceed."
    )
    await ctx.message.delete()

    def check(m):
        return (
            m.content == "!confirm_reset"
            and m.author.id == owner_id
            and m.channel == ctx.channel
        )

    try:
        confirm_message = await bot.wait_for("message", check=check, timeout=30)

        global drop_counter, drop_submissions
        drop_counter = 1
        drop_submissions.clear()
        save_data()

        await ctx.send("✅ All drop data has been reset successfully.")
        await confirm_message.delete()
        await confirmation_message.delete()
    except discord.ext.commands.errors.CommandInvokeError:
        await ctx.send("❌ Error occurred during reset.")
    except discord.errors.NotFound:
        pass
    except:
        await ctx.send("❌ Reset cancelled due to no confirmation within time limit.")
        await confirmation_message.delete(delay=5)


bot.run(token)
