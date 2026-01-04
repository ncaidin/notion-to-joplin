```markdown
# Notion to Joplin (notojo)

Small Python utility to pull data from Notion and create a
Markdown checklist note in Joplin, using the Joplin Web Clipper/Data API.

Current features:

- Query Notion "Actions" database for:
  - **Pending Actions** (not done, not waiting, due today or earlier)
  - **Awaiting Responses** (not done, waiting, due today or earlier)
  - **Unscheduled actions** (not done, not waiting, no Do Date)
- Query Notion CRM databases for:
  - **Contacts needing review** (Contacts with `Needs Review` checked)
  - **Interactions marked for project review** (Interactions with `Project Review` checked)
- Pull **Weekly Goals** from a Notion "Action Zone" page:
  - "Weekly Goals" toggle/heading + nested bullet list
- Generate a single Markdown note with multiple sections:
  - Weekly Goals
  - Pending Actions
  - Awaiting Responses
  - Unscheduled actions count
  - CRM Review counts
- Create a daily Joplin note with a date-based title in a specific folder

For a detailed description of behavior and requirements, see
[`notojo_srs.md`](./notojo_srs.md).

---

## Requirements

- Python 3.9+ (tested with 3.13 on macOS)
- Notion API integration with access to:
  - Actions database
  - Contacts database
  - Interactions database
  - Action Zone page
- Joplin desktop with Web Clipper/Data API enabled

---

## Installation

Clone the repo and set up a virtual environment (optional but recommended):

```bash
git clone https://github.com/ncaidin/notion-to-joplin.git
cd notion-to-joplin

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Configuration

This script expects secrets/config to come from environment variables
(or a `.env` file if you're using `python-dotenv`).

**Required environment variables:**

- `NOTION_SECRET`  
  Notion internal integration token.

- `NOTION_ACTION_DATABASE_ID`  
  Database ID for the Actions database.

- `NOTION_CONTACTS_DATABASE_ID`  
  Database ID for the Contacts (CRM) database.

- `NOTION_INTERACTIONS_DATABASE_ID`  
  Database ID for the Interactions (CRM) database.

- `NOTION_ACTION_ZONE_PAGE_ID`  
  Page ID for the Action Zone page that contains the "Weekly Goals" section.

- `JOPLIN_TOKEN`  
  Joplin Web Clipper/Data API token.

**Optional environment variables:**

- `JOPLIN_BASE_URL`  
  Base URL for the Joplin API.  
  Default: `http://127.0.0.1:41184`

> Note: The Joplin destination folder is currently configured via a hard-coded
> `JOPLIN_TODO_FOLDER_ID` constant in `notojo.py`.

Make sure your Notion integration is explicitly added to:

- The Actions database
- The Contacts database
- The Interactions database
- The Action Zone page

Otherwise the API calls will fail with access/validation errors.

---

## Usage

From the project root:

```bash
source .venv/bin/activate  # if using a venv
python notojo.py
```

The script will:

1. Fetch **Weekly Goals** from the Notion Action Zone page (if present).
2. Query the Actions database for:
   - Pending Actions
   - Awaiting Responses
   - Unscheduled actions count
3. Query CRM databases for:
   - Contacts needing review
   - Interactions marked for project review
4. Generate a Markdown note with these sections (if there is anything to report).
5. Create a new daily note in Joplin with a title like:

   ```text
   Notion To Dos – DD-MM-YYYY
   ```

If there are truly no items to report (no goals, no actions, no CRM counts),
the script logs an informational message and does **not** create a note.

You can run this manually or via a scheduled task (e.g. macOS `launchd`).

---

## Utilities

- `inspect_notion.py`: A helper script to print the schema (properties and types) of your Notion databases. Useful for debugging `400` errors or verifying property names.

---

## Scheduling (macOS `launchd`)

On macOS, you can use a LaunchAgent to run this script automatically once per day. 

1. Create a `.plist` file in `~/Library/LaunchAgents/` (e.g., `com.yourname.notojo.plist`).
2. Configure it to execute the Python interpreter from your virtual environment and point to the `notojo.py` script.
3. Load the agent using `launchctl load ~/Library/LaunchAgents/com.yourname.notojo.plist`.

This ensures your daily Joplin note is ready for you every morning.

---

## License

MIT — see `LICENSE` file for details.
```