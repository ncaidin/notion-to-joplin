from notion_utils import query_notion_database

import os
import sys
from datetime import datetime, timezone
import requests

from datetime import datetime
import sys

def log(msg):
    """Log a normal message with timestamp to stdout."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def log_error(msg):
    """Log an error message with timestamp to stderr."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", file=sys.stderr)

from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# NOTION variables
NOTION_SECRET = os.environ.get("NOTION_SECRET")
NOTION_ACTION_DATABASE_ID = os.environ.get("NOTION_ACTION_DATABASE_ID")
NOTION_API_URL = "https://api.notion.com/v1/databases"
NOTION_VERSION = "2022-06-28"

# JOPLIN variables
JOPLIN_TOKEN = os.environ.get("JOPLIN_TOKEN")
JOPLIN_BASE_URL = os.environ.get("JOPLIN_BASE_URL", "http://127.0.0.1:41184")
JOPLIN_TODO_FOLDER_ID = "9bd030cb7cda47a5beac41da29a149db"

REQUIRED_VARS = [
    "NOTION_SECRET",
    "NOTION_ACTION_DATABASE_ID",
    "JOPLIN_TOKEN",
]

missing = [v for v in REQUIRED_VARS if not os.environ.get(v)]

if missing:
    log_error("❌ Missing required environment variables:")
    for v in missing:
        log_error(f"   - {v}")
    sys.exit(1)


def query_notion_actions():
    """Query Notion for actions that are NOT done and due today or earlier."""

    # Today in ISO 8601 date format
    today_iso = datetime.now(timezone.utc).date().isoformat()

    payload = {
        "filter": {
            "and": [
                {"property": "Done", "checkbox": {"equals": False}},
                {"property": "Waiting", "checkbox": {"equals": False}},
                {"property": "Do Date", "date": {"on_or_before": today_iso}},
            ]
        }
    }

    # print("\n⏳ Querying Notion for Pending Actions...\n")

    try:
        data = query_notion_database(NOTION_ACTION_DATABASE_ID, payload)
        return data.get("results", [])
    except Exception as e:
        log_error(f"❌ Error querying Notion database:\n{e}\n")
        return []

def query_notion_waiting():
    """Query Notion for actions that are NOT done and ARE marked as Waiting."""

    # Today in ISO 8601 date format
    today_iso = datetime.now(timezone.utc).date().isoformat()

    payload = {
        "filter": {
            "and": [
                {"property": "Done", "checkbox": {"equals": False}},
                {"property": "Waiting", "checkbox": {"equals": True}},
                {"property": "Do Date", "date": {"on_or_before": today_iso}},
            ]
        }
    }

    # print("\n⏳ Querying Notion for Waiting-on-others actions...\n")

    try:
        data = query_notion_database(NOTION_ACTION_DATABASE_ID, payload)
        return data.get("results", [])
    except Exception as e:
        log_error(f"❌ Error querying Notion database for waiting items:\n{e}\n")
        return []


def extract_action_names(results):
    """Extract the 'Name' (title) property from each result."""
    # print("📄 Extracting action names...\n")
    actions = []

    for page in results:
        props = page.get("properties", {})
        name_prop = props.get("Name")

        if not name_prop:
            continue

        if name_prop["type"] == "title":
            title_parts = name_prop["title"]
            if title_parts:
                actions.append(title_parts[0]["plain_text"])

    return actions


def build_checklist_section(title: str,actions):
    """Build markdown checklist text from action names."""
    # print("📝 Generating checklist section: {title}...\n")

    empty_text = {
        "Pending Actions": "No pending actions.",
        "Awaiting Responses": "No items awaiting responses.",
    }.get(title, f"No {title.lower()}.")   # fallback for any new sections

    if not actions:
        return f"{title}:\n\n_{empty_text}_"

    lines = [f"{title}:", ""]
    for a in actions:
        lines.append(f"- [ ] {a}")

    return "\n".join(lines)


def create_joplin_note(title: str, body: str):
    notes_url = f"{JOPLIN_BASE_URL}/notes"
    params = {"token": JOPLIN_TOKEN}
    payload = {
        "title": title,
        "body": body,
	"parent_id": JOPLIN_TODO_FOLDER_ID, # <- send note to "To Dos" 
    }

    try:
        resp = requests.post(notes_url, params=params, json=payload)
        resp.raise_for_status()
        data = resp.json()
        note_id = data.get("id")
        # print(f"✅ Created Joplin note with id: {note_id}")
    except Exception as e:
        log_error(f"❌ Error creating Joplin note: {e}")


def main():
    # First step - Pending Actions
    pending_results = query_notion_actions()
    pending_actions = extract_action_names(pending_results)

    # Second step - Awaiting Responses
    waiting_results = query_notion_waiting()
    waiting_actions = extract_action_names(waiting_results)

    sections = []

    pending_section = build_checklist_section("Pending Actions", pending_actions)
    if pending_section:
        sections.append(pending_section)

    waiting_section = build_checklist_section("Awaiting responses", waiting_actions)
    if waiting_section:
        sections.append(waiting_section)

    if not sections:
        log("ℹ️ No actions to send to Joplin today.")
        return

    checklist_text = "\n\n".join(sections)

    # Print to console so you can see what we’re sending
    # print(checklist_text)

    today_str = datetime.now().strftime("%d-%m-%Y")
    title = f"Notion To Dos – {today_str}"
    create_joplin_note(title, checklist_text)

    log("✅ notojo.py completed successfully and synced to Joplin.")

if __name__ == "__main__":
    main()
