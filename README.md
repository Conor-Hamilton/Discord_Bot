# Discord Bingo Bot

A Python-based Discord bot designed to manage and automate bingo events. It features a user-friendly interface for submitting and tracking bingo progress, designed specifically for OSRS-themed bingo challenges.

## Features

- **Team Management:**
  - Randomise and order team captains for drafting.
  - Track team progress and update goals.

- **Drop Submission System:**
  - Submit drops for review with image attachments.
  - Staff commands to approve or reject submissions.
  - Automated notifications in relevant Discord channels.

- **Progress Tracking:**
  - Check and update progress for teams and categories.
  - Generate reports and reset data when needed.

- **Data Management:**
  - Stores data in a PostgreSQL database.
  - Export data in JSON format for external analysis.

## Prerequisites

- Python 3.10+  
- A PostgreSQL database  
- Discord bot token  
- Required Python packages (`discord.py`, `psycopg2`, `python-dotenv`)

## Commands

### User Commands

/randomise: Randomly order team captains for drafting.  
/submit: Submit a drop with category and image attachment.

### Staff Commands

/confirm: Approve a drop submission.  
/reject: Reject a submission with a reason.  
/check: Check team progress in a category.  
/update: Update progress for a team and category.  
/show_current_data: Display all drop data in a table.  
/reset_data: Reset all drop data and counter (Owner only).  
/download_data: Export data as JSON (Owner only).

## Database Schema

The bot uses a PostgreSQL database with the following table:

```sql
CREATE TABLE drops (  
    drop_id SERIAL PRIMARY KEY,  
    submitter_id BIGINT,  
    team_role TEXT,  
    category TEXT,  
    image_url TEXT,  
    status TEXT DEFAULT 'Pending',  
    progress TEXT DEFAULT NULL,  
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP  
);
```

## Configuration

- **Thumbnail URL:** Customise the thumbnail with your event's branding.  
- **Categories and Teams:** Modify `TEAM_NAMES`, `TEAM_CAPTAINS`, and `CATEGORIES` in the script.

## License

This project is licensed under the MIT License.

---

**Note:** This bot is tailored for OSRS-themed bingo events but can be customised for other themes or games with minor adjustments.
