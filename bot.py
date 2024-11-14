import os
import discord
from dotenv import load_dotenv
from discord import app_commands
import json
from datetime import datetime, timedelta
import random

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

TEAM_CAPTAINS = [
    "Joshua",
    "WiseOldGrant",
    "Roldeh",
    "Dewl Again",
    "Them Is Me",
    "Raathma",
    "Solo Dani",
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


@tree.command(
    name="randomise",
    description="Randomly pick and order team captains for the draft.",
)
async def randomise(interaction: discord.Interaction):
    shuffled_captains = TEAM_CAPTAINS.copy()
    random.shuffle(shuffled_captains)

    draft_order = "\n".join(
        [f"{i+1}. {captain}" for i, captain in enumerate(shuffled_captains)]
    )

    team_captains_role = discord.utils.get(
        interaction.guild.roles, name="team captains"
    )

    embed = discord.Embed(
        title="🎲 Team Captains Draft Order",
        description=draft_order,
        color=discord.Color.gold(),
    )
    embed.set_footer(text="Good luck!")

    await interaction.response.send_message(
        content=f"{team_captains_role.mention}, here is the draft order!",
        embed=embed,
        ephemeral=False,
    )


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

    if interaction.channel.name != "drop-submissions":
        await interaction.response.send_message(
            "🚫 This command can only be used in the `#drop-submissions` channel.",
            ephemeral=True,
        )
        return

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

    if not image_attachment and len(interaction.message.attachments) > 0:
        image_attachment = interaction.message.attachments[0]

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
    drop_submissions[drop_id] = {
        "submitter_id": interaction.user.id,
        "team_role": team_role,
        "image_url": image_url,
        "status": "Pending",
        "timestamp": datetime.utcnow().isoformat(),
    }
    save_data()

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
        message = await staff_channel.send(embed=embed)
        drop_submissions[drop_id]["message_id"] = message.id
        save_data()

    await interaction.response.send_message(
        f"✅ Your drop with ID `{drop_id}` has been submitted and is pending review in {staff_channel.mention}.",
        ephemeral=True,
    )


@tree.command(name="confirm", description="Confirm a drop submission")
@app_commands.describe(
    drop_id="ID of the drop to confirm", comment="Additional comment"
)
@app_commands.checks.has_role("Staff")
async def confirm(interaction: discord.Interaction, drop_id: str, comment: str = None):
    global drop_submissions

    if interaction.channel.name != "staff-review":
        await interaction.response.send_message(
            "🚫 This command can only be used in the `#staff-review` channel.",
            ephemeral=True,
        )
        return

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

    drop_data["status"] = "Confirmed"
    save_data()

    staff_channel = discord.utils.get(
        interaction.guild.text_channels, name="staff-review"
    )
    if staff_channel:
        try:
            submission_message = await staff_channel.fetch_message(
                drop_data["message_id"]
            )
            await submission_message.add_reaction("✅")
        except discord.NotFound:
            pass

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
        submitter = await bot.fetch_user(drop_data["submitter_id"])
        await team_channel.send(content=f"{submitter.mention}", embed=embed)

    await interaction.response.send_message(
        f"✅ Drop `{drop_id}` has been approved.", ephemeral=True
    )


@tree.command(name="reject", description="Reject a drop submission")
@app_commands.describe(
    drop_id="ID of the drop to reject", reason="Reason for rejection"
)
@app_commands.checks.has_role("Staff")
async def reject(
    interaction: discord.Interaction, drop_id: str, reason: str = "No reason provided"
):
    global drop_submissions

    if interaction.channel.name != "staff-review":
        await interaction.response.send_message(
            "🚫 This command can only be used in the `#staff-review` channel.",
            ephemeral=True,
        )
        return

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

    drop_data["status"] = "Rejected"
    save_data()

    staff_channel = discord.utils.get(
        interaction.guild.text_channels, name="staff-review"
    )
    if staff_channel:
        try:
            submission_message = await staff_channel.fetch_message(
                drop_data["message_id"]
            )
            await submission_message.add_reaction("❌")
        except discord.NotFound:
            pass

    embed = discord.Embed(
        title="❌ Drop Rejected",
        description=f"**Drop ID:** `{drop_id}`\n**Rejected by:** {interaction.user.mention}",
        color=discord.Color.red(),
    )
    embed.set_image(url=drop_data["image_url"])
    embed.set_thumbnail(url=thumbnail_url)
    embed.add_field(name="Reason", value=reason, inline=False)

    team_channel = discord.utils.get(
        interaction.guild.text_channels,
        name=drop_data["team_role"].replace(" ", "-"),
    )
    if team_channel:
        submitter = await bot.fetch_user(drop_data["submitter_id"])
        await team_channel.send(content=f"{submitter.mention}", embed=embed)

    await interaction.response.send_message(
        f"❌ Drop `{drop_id}` has been rejected.", ephemeral=True
    )


import logging

logging.basicConfig(level=logging.INFO)


@tree.command(name="reset_data", description="Reset all drop data (Owner only)")
async def reset_data(interaction: discord.Interaction):
    owner_id = 252465642802774017
    if interaction.user.id != owner_id:
        await interaction.response.send_message(
            "⛔ You do not have permission to use this command.", ephemeral=True
        )
        return

    class ConfirmButton(discord.ui.View):
        @discord.ui.button(label="Confirm Reset", style=discord.ButtonStyle.danger)
        async def confirm_reset(
            self, interaction: discord.Interaction, button: discord.ui.Button
        ):
            if interaction.user.id != owner_id:
                await interaction.response.send_message(
                    "⛔ You do not have permission to use this button.", ephemeral=True
                )
                return

            global drop_counter, drop_submissions

            try:
                drop_counter = 1
                drop_submissions.clear()
                save_data()

                await interaction.response.edit_message(
                    content="✅ All drop data has been reset successfully.", view=None
                )
                logging.info("Drop data successfully reset.")
                self.stop()
            except Exception as e:
                logging.error(f"Error while resetting drop data: {e}")
                await interaction.response.send_message(
                    "❌ An error occurred while resetting drop data.", ephemeral=True
                )

    try:
        view = ConfirmButton()
        await interaction.response.send_message(
            "⚠️ Are you sure you want to reset all drop data? Click the button below to confirm.",
            view=view,
            ephemeral=True,
        )
        logging.info("Reset confirmation sent.")
    except Exception as e:
        logging.error(f"Error while sending reset confirmation: {e}")
        await interaction.response.send_message(
            "❌ An error occurred while sending the reset confirmation.", ephemeral=True
        )


bot.run(TOKEN)
