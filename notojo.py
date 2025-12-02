from notion_utils import query_notion_database

import os
import sys
from datetime import datetime, timezone
import requests

# NOTION variables
NOTION_SECRET = os.getenv("NOTION_SECRET")
NOTION_ACTION_DATABASE_ID = os.getenv("NOTION_ACTION_DATABASE_ID")
NOTION_API_URL = "https://api.notion.com/v1/databases"
NOTION_VERSION = "2022-06-28"

# JOPLIN variables
JOPLIN_TOKEN = os.getenv("JOPLIN_TOKEN")
JOPLIN_BASE_URL = os.getenv("JOPLIN_BASE_URL", "http://127.0.0.1:41184")
JOPLIN_TODO_FOLDER_ID = "9bd030cb7cda47a5beac41da29a149db"


def query_notion_actions():
    """Query Notion for actions that are NOT done and due today or earlier."""

    if not NOTION_SECRET or not NOTION_ACTION_DATABASE_ID:
        print("❌ NOTION_SECRET or NOTION_ACTION_DATABASE_ID not set. Exiting.")
        sys.exit(1)

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

    print("\n⏳ Querying Notion for Pending Actions...\n")

    try:
        data = query_notion_database(NOTION_ACTION_DATABASE_ID, payload)
        return data.get("results", [])
    except Exception as e:
        print(f"❌ Error querying Notion database:\n{e}\n")
        return []

def query_notion_waiting():
    """Query Notion for actions that are NOT done and ARE marked as Waiting."""

    if not NOTION_SECRET or not NOTION_ACTION_DATABASE_ID:
        print("❌ NOTION_SECRET or NOTION_ACTION_DATABASE_ID not set. Exiting.")
        sys.exit(1)

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

    print("\n⏳ Querying Notion for Waiting-on-others actions...\n")

    try:
        data = query_notion_database(NOTION_ACTION_DATABASE_ID, payload)
        return data.get("results", [])
    except Exception as e:
        print(f"❌ Error querying Notion database for waiting items:\n{e}\n")
        return []

    print("\n⏳ Querying Notion for Awaiting Responses...\n")

    url = f"{NOTION_API_URL}/{NOTION_ACTION_DATABASE_ID}/query"
    try:
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error querying Notion database:\n{e}\n")
        # Print response content if available for debugging
        if e.response is not None:
            print("Response content:", e.response.text)
        return []

    data = resp.json()
    return data.get("results", [])


def extract_action_names(results):
    """Extract the 'Name' (title) property from each result."""
    print("📄 Extracting action names...\n")
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
    print("📝 Generating checklist section: {title}...\n")

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
    """Create a new note in Joplin via the Web Clipper API."""
    if not JOPLIN_TOKEN:
        print("⚠️ JOPLIN_TOKEN not set. Skipping Joplin note creation.")
        return

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
        print(f"✅ Created Joplin note with id: {note_id}")
    except Exception as e:
        print(f"❌ Error creating Joplin note: {e}")


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
        print("ℹ️ No actions to send to Joplin today.")
        return

    checklist_text = "\n\n".join(sections)

    # Print to console so you can see what we’re sending
    print(checklist_text)

    today_str = datetime.now().strftime("%d-%m-%Y")
    title = f"Notion To Dos – {today_str}"
    create_joplin_note(title, checklist_text)

if __name__ == "__main__":
    main()
