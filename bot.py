import os
import discord
from dotenv import load_dotenv
from discord import app_commands
from datetime import datetime
import psycopg2
from psycopg2.extras import DictCursor
import random
import json

thumbnail_url = "https://i.imgur.com/RC3d1lr.png"

TEAM_NAMES = [
    "shadowless monkeys",
    "who are we",
    "tile snipers",
    "the noobs",
    "rocnars ramblers",
    "leagues waiting room",
    "always the nubs",
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

CATEGORIES = [
    "Smoke Battlestaff",
    "Any Jar Drop",
    "Kraken Tentacle",
    "Any Pet",
    "Dragon Pickaxe",
    "Huey Unique",
    "Make a Godsword",
    "Completed Wildy Shield",
    "Any Masori Armour Piece",
    "Bludgeon Piece",
    "Scurrius Spine",
    "Zombie Axe & Helmet",
    "Tbow/Scythe/Shadow",
    "Any Crystal Seed",
    "Any VW Piece",
    "Araxxor Unique",
    "Dex & Arcane Prayer Scroll",
    "Trio of Heads",
    "2 Million Thieving XP",
    "Lord of the Rings",
    "Zulrah Unique",
    "Justiciar Armour Piece",
    "Armadyl Crossbow & Staff of the Dead",
    "Nex Unique",
    "Perilous Moons Unique",
]

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")


def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor(cursor_factory=DictCursor)
    return conn, cursor


conn, cursor = get_db_connection()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS drops (
        drop_id SERIAL PRIMARY KEY,
        submitter_id BIGINT,
        team_role TEXT,
        category TEXT,
        image_url TEXT,
        status TEXT DEFAULT 'Pending',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
)

cursor.execute(
    """
    DO $$
    BEGIN
        -- Check and add 'category' column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name='drops' AND column_name='category'
        ) THEN
            ALTER TABLE drops ADD COLUMN category TEXT;
        END IF;

        -- Check and add 'progress' column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name='drops' AND column_name='progress'
        ) THEN
            ALTER TABLE drops ADD COLUMN progress TEXT DEFAULT NULL;
        END IF;
    END $$;
    """
)


conn.commit()
cursor.close()
conn.close()

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


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


from discord import app_commands


@tree.command(name="submit", description="Submit a drop for review")
@app_commands.describe(
    category="Category of the drop",
    image_url="URL of the image (optional, use an attachment instead if available)",
    image_attachment="Attach the image directly (preferred)",
)
@app_commands.choices(
    category=[app_commands.Choice(name=cat, value=cat) for cat in CATEGORIES]
)
async def submit(
    interaction: discord.Interaction,
    category: app_commands.Choice[str],
    image_url: str = None,
    image_attachment: discord.Attachment = None,
):
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

    conn, cursor = get_db_connection()

    try:
        cursor.execute(
            """
            INSERT INTO drops (submitter_id, team_role, category, image_url)
            VALUES (%s, %s, %s, %s)
            RETURNING drop_id;
            """,
            (interaction.user.id, team_role, category.value, image_url),
        )
        drop_id = cursor.fetchone()["drop_id"]
        conn.commit()

        embed = discord.Embed(
            title=f"New Drop Submission from {interaction.user} ({team_role.title()}):",
            description=f"**Drop ID:** `DROP-{drop_id}`\n**Category:** {category.value}",
            color=discord.Color.blue(),
        )
        embed.set_image(url=image_url)
        embed.set_thumbnail(url=thumbnail_url)

        staff_channel = discord.utils.get(
            interaction.guild.text_channels, name="staff-review"
        )
        if staff_channel:
            await staff_channel.send(embed=embed)

        team_channel = discord.utils.get(
            interaction.guild.text_channels, name=team_role.replace(" ", "-")
        )
        if team_channel:
            await team_channel.send(
                content=f"📥 {interaction.user.mention} has submitted a new drop for review!",
                embed=embed,
            )

        await interaction.response.send_message(
            f"✅ Your drop with ID `DROP-{drop_id}` has been submitted and is pending review in {staff_channel.mention}.",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ An error occurred: {e}", ephemeral=True
        )
    finally:
        cursor.close()
        conn.close()


@tree.command(name="confirm", description="Confirm a drop submission")
@app_commands.describe(
    drop_id="ID of the drop to confirm", comment="Additional comment"
)
@app_commands.checks.has_role("Staff")
async def confirm(interaction: discord.Interaction, drop_id: str, comment: str = None):
    conn, cursor = get_db_connection()
    try:
        # Strip "DROP-" prefix if present
        drop_id_clean = drop_id.upper().replace("DROP-", "").strip()
        cursor.execute("SELECT * FROM drops WHERE drop_id = %s;", (drop_id_clean,))
        drop_data = cursor.fetchone()

        if not drop_data:
            await interaction.response.send_message(
                f"⚠️ Drop ID `DROP-{drop_id_clean}` not found.", ephemeral=True
            )
            return

        cursor.execute(
            "UPDATE drops SET status = 'Confirmed' WHERE drop_id = %s;",
            (drop_id_clean,),
        )
        conn.commit()

        embed = discord.Embed(
            title="✅ Drop Approved!",
            description=f"**Drop ID:** `DROP-{drop_id_clean}`\n**Category:** {drop_data['category']}\n**Approved by:** {interaction.user.mention}",
            color=discord.Color.green(),
        )
        embed.set_image(url=drop_data["image_url"])
        embed.set_thumbnail(url=thumbnail_url)

        if comment:
            embed.add_field(name="Comment", value=comment, inline=False)

        staff_channel = discord.utils.get(
            interaction.guild.text_channels, name="staff-review"
        )
        if staff_channel:
            try:
                staff_message = await staff_channel.history().find(
                    lambda m: f"Drop ID: `DROP-{drop_id_clean}`"
                    in m.embeds[0].description
                )
                if staff_message:
                    await staff_message.add_reaction("✅")
            except Exception as e:
                print(f"Failed to add reaction: {e}")

        team_channel = discord.utils.get(
            interaction.guild.text_channels,
            name=drop_data["team_role"].replace(" ", "-"),
        )
        if team_channel:
            submitter = await bot.fetch_user(drop_data["submitter_id"])
            await team_channel.send(content=f"{submitter.mention}", embed=embed)

        await interaction.response.send_message(
            f"✅ Drop `DROP-{drop_id_clean}` has been approved.", ephemeral=True
        )

    finally:
        cursor.close()
        conn.close()


@tree.command(name="reject", description="Reject a drop submission")
@app_commands.describe(
    drop_id="ID of the drop to reject", reason="Reason for rejection"
)
@app_commands.checks.has_role("Staff")
async def reject(
    interaction: discord.Interaction, drop_id: str, reason: str = "No reason provided"
):
    conn, cursor = get_db_connection()
    try:
        drop_id_clean = drop_id.upper().replace("DROP-", "").strip()
        cursor.execute("SELECT * FROM drops WHERE drop_id = %s;", (drop_id_clean,))
        drop_data = cursor.fetchone()

        if not drop_data:
            await interaction.response.send_message(
                f"⚠️ Drop ID `DROP-{drop_id_clean}` not found.", ephemeral=True
            )
            return

        cursor.execute(
            "UPDATE drops SET status = 'Rejected' WHERE drop_id = %s;",
            (drop_id_clean,),
        )
        conn.commit()

        embed = discord.Embed(
            title="❌ Drop Rejected",
            description=f"**Drop ID:** `DROP-{drop_id_clean}`\n**Category:** {drop_data['category']}\n**Rejected by:** {interaction.user.mention}",
            color=discord.Color.red(),
        )
        embed.set_image(url=drop_data["image_url"])
        embed.set_thumbnail(url=thumbnail_url)
        embed.add_field(name="Reason", value=reason, inline=False)

        staff_channel = discord.utils.get(
            interaction.guild.text_channels, name="staff-review"
        )
        if staff_channel:
            try:
                staff_message = await staff_channel.history().find(
                    lambda m: f"Drop ID: `DROP-{drop_id_clean}`"
                    in m.embeds[0].description
                )
                if staff_message:
                    await staff_message.add_reaction("❌")
            except Exception as e:
                print(f"Failed to add reaction: {e}")

        team_channel = discord.utils.get(
            interaction.guild.text_channels,
            name=drop_data["team_role"].replace(" ", "-"),
        )
        if team_channel:
            submitter = await bot.fetch_user(drop_data["submitter_id"])
            await team_channel.send(content=f"{submitter.mention}", embed=embed)

        await interaction.response.send_message(
            f"❌ Drop `DROP-{drop_id_clean}` has been rejected.", ephemeral=True
        )

    finally:
        cursor.close()
        conn.close()


@tree.command(name="check", description="Check progress for a team and category.")
@app_commands.describe(
    team="Select the team",
    category="Select the category",
)
@app_commands.choices(
    team=[app_commands.Choice(name=team.title(), value=team) for team in TEAM_NAMES],
    category=[app_commands.Choice(name=cat, value=cat) for cat in CATEGORIES],
)
@app_commands.checks.has_role("Staff")
async def check(
    interaction: discord.Interaction,
    team: app_commands.Choice[str],
    category: app_commands.Choice[str],
):
    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            """
            SELECT progress, COUNT(*) AS count, status
            FROM drops
            WHERE team_role = %s AND category = %s
            GROUP BY progress, status;
            """,
            (team.value.lower(), category.value),
        )
        results = cursor.fetchall()

        if not results:
            await interaction.response.send_message(
                f"No submissions found for team `{team.name}` and category `{category.name}`.",
                ephemeral=True,
            )
            return

        progress_message = f"📊 **Progress for {team.name} in {category.name}:**\n\n"
        progress_tracker = None

        for row in results:
            if row["progress"] is not None:
                progress_tracker = row["progress"]
            progress_message += f"- **{row['status']}:** {row['count']} submissions\n"

        if progress_tracker:
            progress_message += f"\n📈 **Overall Progress:** {progress_tracker}\n"

        await interaction.response.send_message(progress_message, ephemeral=True)

    finally:
        cursor.close()
        conn.close()


@tree.command(
    name="update",
    description="Update the progress for a category in the database (Staff only).",
)
@app_commands.describe(
    team_role="Select the team",
    category="Select the category",
    progress="The updated progress value (e.g., 1/4, 2/4, etc.)",
)
@app_commands.choices(
    team_role=[
        app_commands.Choice(name=team.title(), value=team) for team in TEAM_NAMES
    ],
    category=[app_commands.Choice(name=cat, value=cat) for cat in CATEGORIES],
)
@app_commands.checks.has_role("Staff")
async def update(
    interaction: discord.Interaction,
    team_role: app_commands.Choice[str],
    category: app_commands.Choice[str],
    progress: str,
):
    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            """
            SELECT * FROM drops WHERE team_role = %s AND category = %s;
            """,
            (team_role.value.lower(), category.value),
        )
        existing_data = cursor.fetchall()

        if not existing_data:
            await interaction.response.send_message(
                f"No data found for team `{team_role.name}` and category `{category.name}`.",
                ephemeral=True,
            )
            return

        cursor.execute(
            """
            UPDATE drops
            SET progress = %s
            WHERE team_role = %s AND category = %s;
            """,
            (progress, team_role.value.lower(), category.value),
        )
        conn.commit()

        await interaction.response.send_message(
            f"✅ Progress for `{category.name}` in team `{team_role.name}` has been updated to `{progress}`.",
            ephemeral=True,
        )
    finally:
        cursor.close()
        conn.close()


@tree.command(
    name="show_current_data", description="Displays all current data in table format."
)
async def show_current_data(interaction: discord.Interaction):
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT * FROM drops")
        data = cursor.fetchall()

        if not data:
            await interaction.response.send_message(
                "No data available.", ephemeral=True
            )
            return

        table_header = (
            f"{'Drop ID':<10}{'Submitter ID':<20}{'Team Role':<25}{'Category':<15}{'Status':<10}{'Timestamp':<20}\n"
            + "-" * 120
            + "\n"
        )
        table_rows = ""

        for row in data:
            table_rows += (
                f"{row['drop_id']:<10}{row['submitter_id']:<20}{row['team_role']:<25}{row['category'] or 'None':<15}"
                f"{row['status']:<10}{row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'):<20}\n"
            )
            table_rows += f"Image URL: {row['image_url']}\n"

        full_table = table_header + table_rows

        chunks = []
        current_chunk = "```"
        for line in full_table.splitlines():
            if len(current_chunk) + len(line) + 3 > 2000:
                current_chunk += "```"
                chunks.append(current_chunk)
                current_chunk = "```" + table_header
            current_chunk += line + "\n"

        if current_chunk.strip():
            current_chunk += "```"
            chunks.append(current_chunk)

        await interaction.response.send_message(
            "Here is the current data:", ephemeral=True
        )
        for chunk in chunks:
            await interaction.followup.send(chunk, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ An error occurred while retrieving the data: {e}", ephemeral=True
        )
    finally:
        cursor.close()
        conn.close()


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
            self, button_interaction: discord.Interaction, button: discord.ui.Button
        ):
            if button_interaction.user.id != owner_id:
                await button_interaction.response.send_message(
                    "⛔ You do not have permission to use this button.", ephemeral=True
                )
                return

            try:
                conn, cursor = get_db_connection()

                cursor.execute("DELETE FROM drops;")

                cursor.execute("ALTER SEQUENCE drops_drop_id_seq RESTART WITH 1;")

                conn.commit()
                cursor.close()
                conn.close()

                await button_interaction.response.edit_message(
                    content="✅ All drop data and the drop counter have been reset successfully.",
                    view=None,
                )
                self.stop()
            except Exception as e:
                await button_interaction.response.send_message(
                    f"❌ An error occurred while resetting drop data: {e}",
                    ephemeral=True,
                )

    try:
        view = ConfirmButton()
        await interaction.response.send_message(
            "⚠️ Are you sure you want to reset all drop data and the drop counter? Click the button below to confirm.",
            view=view,
            ephemeral=True,
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


@tree.command(
    name="download_data",
    description="View or download the current drop data (Owner only)",
)
async def download_data(interaction: discord.Interaction):
    owner_id = 252465642802774017
    if interaction.user.id != owner_id:
        await interaction.response.send_message(
            "⛔ You do not have permission to use this command.", ephemeral=True
        )
        return

    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT * FROM drops;")
        drops = cursor.fetchall()

        if not drops:
            await interaction.response.send_message(
                "No drop data found.", ephemeral=True
            )
            return

        data = [
            {
                "drop_id": f"DROP-{row['drop_id']}",
                "submitter_id": row["submitter_id"],
                "team_role": row["team_role"],
                "category": row["category"],
                "image_url": row["image_url"],
                "status": row["status"],
                "timestamp": row["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            }
            for row in drops
        ]

        formatted_data = json.dumps(data, indent=4)

        with open("drop_data.json", "w") as f:
            f.write(formatted_data)

        await interaction.response.send_message(
            "Data has been exported. Downloading file...", ephemeral=True
        )

        with open("drop_data.json", "rb") as f:
            await interaction.followup.send(
                file=discord.File(f, "drop_data.json"), ephemeral=True
            )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error exporting data: {e}", ephemeral=True
        )
    finally:
        cursor.close()
        conn.close()


bot.run(TOKEN)
