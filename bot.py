import os
import discord
from dotenv import load_dotenv
from discord import app_commands
import json

DATA_FILE = "drop_data.json"
thumbnail_url = "https://i.imgur.com/RC3d1lr.png"

TEAM_NAMES = [
    "shadowless monkeys",
    "who are we",
    "tile snipers",
    "the noobs",
    "rocnars ramblers",
    "leagues waiting room",
]


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


intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)
drop_counter, drop_submissions = load_data()

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")


@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}!")


@tree.command(name="hello", description="Say hello!")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("Hello! I'm your new bot.")


@tree.command(name="submit", description="Submit a drop for review")
@app_commands.describe(
    image_url="URL of the image (optional, use an attachment instead if available)",
    image_attachment="Attach the image directly (preferred)",
)
async def submit(
    interaction: discord.Interaction,
    image_url: str = None,
    image_attachment: discord.Attachment = None,
):
    global drop_counter, drop_submissions

    team_role = next(
        (
            role.name.lower()
            for role in interaction.user.roles
            if role.name.lower() in TEAM_NAMES
        ),
        None,
    )
    if not team_role:
        await interaction.response.send_message(
            "⛔ You don't have a valid team role. Please contact a staff member.",
            ephemeral=True,
        )
        return

    if image_attachment:
        if not image_attachment.content_type.startswith("image/"):
            await interaction.response.send_message(
                "🚫 Only image files are allowed for attachments.", ephemeral=True
            )
            return
        image_url = image_attachment.url
    elif not image_url:
        await interaction.response.send_message(
            "⚠️ Please provide an image URL or attach an image to submit.",
            ephemeral=True,
        )
        return

    drop_id = f"DROP-{drop_counter:03}"
    drop_counter += 1

    embed = discord.Embed(
        title=f"New Drop Submission from {interaction.user} ({team_role.title()}):",
        description=f"Drop ID: `{drop_id}`",
        color=discord.Color.blue(),
    )
    embed.set_image(url=image_url)
    embed.set_thumbnail(url=thumbnail_url)

    staff_channel = discord.utils.get(
        interaction.guild.text_channels, name="staff-review"
    )
    if staff_channel:
        submission_message = await staff_channel.send(embed=embed)

        drop_submissions[drop_id] = {
            "message_id": submission_message.id,
            "channel_id": staff_channel.id,
            "submitter_id": interaction.user.id,
            "team_role": team_role,
            "image_url": image_url,
            "status": "Pending",
        }
        save_data()

    await interaction.response.send_message(
        f"✅ Your drop with ID `{drop_id}` has been submitted and is pending review in {staff_channel.mention}.",
        ephemeral=True,
    )


async def fetch_submission_message(guild, drop_data):
    try:
        channel = guild.get_channel(drop_data["channel_id"])
        if not channel:
            raise ValueError("Channel not found.")
        message = await channel.fetch_message(drop_data["message_id"])
        return message
    except Exception as e:
        return None


@tree.command(name="confirm", description="Confirm a drop submission")
@app_commands.describe(
    drop_id="ID of the drop to confirm", comment="Additional comment"
)
@app_commands.checks.has_role("Staff")
async def confirm(interaction: discord.Interaction, drop_id: str, comment: str = None):
    global drop_submissions
    drop_id = drop_id.upper()

    if drop_id not in drop_submissions:
        await interaction.response.send_message(
            f"⚠️ Drop ID `{drop_id}` not found.", ephemeral=True
        )
        return

    drop_data = drop_submissions[drop_id]
    if drop_data["status"] != "Pending":
        await interaction.response.send_message(
            f"⚠️ Drop `{drop_id}` has already been {drop_data['status'].lower()}.",
            ephemeral=True,
        )
        return

    submission_message = await fetch_submission_message(interaction.guild, drop_data)
    if submission_message:
        await submission_message.add_reaction("✅")
    else:
        await interaction.response.send_message(
            f"⚠️ Could not locate the original submission message for drop `{drop_id}`.",
            ephemeral=True,
        )
        return

    drop_data["status"] = "Confirmed"
    save_data()

    embed = discord.Embed(
        title="✅ Drop Approved!",
        description=f"**Drop ID:** `{drop_id}`\n**Approved by:** {interaction.user.mention}",
        color=discord.Color.green(),
    )
    embed.set_image(url=drop_data["image_url"])
    embed.set_thumbnail(url=thumbnail_url)
    if comment:
        embed.add_field(name="Comment", value=comment, inline=False)

    team_channel = discord.utils.get(
        interaction.guild.text_channels,
        name=drop_data["team_role"].replace(" ", "-"),
    )
    if team_channel:
        await team_channel.send(embed=embed)

    await interaction.response.send_message(
        f"✅ Drop `{drop_id}` has been approved.", ephemeral=True
    )


@tree.command(name="reset_data", description="Reset all drop data (Owner only)")
async def reset_data(interaction: discord.Interaction):
    owner_id = 252465642802774017
    if interaction.user.id != owner_id:
        await interaction.response.send_message(
            "⛔ You do not have permission to use this command.", ephemeral=True
        )
        return

    confirmation_message = await interaction.response.send_message(
        "⚠️ Are you sure you want to reset all drop data? Type `/confirm_reset` to proceed.",
        ephemeral=True,
    )

    def check(m: discord.Message):
        return (
            m.content == "/confirm_reset"
            and m.author.id == owner_id
            and m.channel == interaction.channel
        )

    try:
        confirm_message = await bot.wait_for("message", check=check, timeout=30)
        global drop_counter, drop_submissions
        drop_counter = 1
        drop_submissions.clear()
        save_data()

        await interaction.followup.send("✅ All drop data has been reset successfully.")
        await confirm_message.delete()
    except discord.ext.commands.errors.CommandInvokeError:
        await interaction.followup.send("❌ Error occurred during reset.")
    except discord.errors.NotFound:
        pass
    except:
        await interaction.followup.send(
            "❌ Reset cancelled due to no confirmation within time limit.",
            ephemeral=True,
        )


bot.run(TOKEN)
