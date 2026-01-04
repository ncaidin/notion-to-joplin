from notion_utils import query_notion_database

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


def log(msg):
    """Log a normal message with timestamp to stdout."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")


def log_error(msg):
    """Log an error message with timestamp to stderr."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", file=sys.stderr)


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# NOTION variables
NOTION_SECRET = os.environ.get("NOTION_SECRET")
NOTION_ACTION_DATABASE_ID = os.environ.get("NOTION_ACTION_DATABASE_ID")
NOTION_CONTACTS_DATABASE_ID = os.environ.get("NOTION_CONTACTS_DATABASE_ID")
NOTION_INTERACTIONS_DATABASE_ID = os.environ.get("NOTION_INTERACTIONS_DATABASE_ID")
NOTION_ACTION_ZONE_PAGE_ID = os.environ.get("NOTION_ACTION_ZONE_PAGE_ID")

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# JOPLIN variables
JOPLIN_TOKEN = os.environ.get("JOPLIN_TOKEN")
JOPLIN_BASE_URL = os.environ.get("JOPLIN_BASE_URL", "http://127.0.0.1:41184")
JOPLIN_TODO_FOLDER_ID = "9bd030cb7cda47a5beac41da29a149db"

REQUIRED_VARS = [
    "NOTION_SECRET",
    "NOTION_ACTION_DATABASE_ID",
    "JOPLIN_TOKEN",
    "NOTION_CONTACTS_DATABASE_ID",
    "NOTION_INTERACTIONS_DATABASE_ID",
    "NOTION_ACTION_ZONE_PAGE_ID",
]

missing = [v for v in REQUIRED_VARS if not os.environ.get(v)]

if missing:
    log_error("❌ Missing required environment variables:")
    for v in missing:
        log_error(f"   - {v}")
    sys.exit(1)


# --------------------
# Notion query helpers
# --------------------


def query_notion_actions():
    """Query Notion for actions that are NOT done and due today or earlier."""
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

    try:
        data = query_notion_database(NOTION_ACTION_DATABASE_ID, payload)
        return data.get("results", [])
    except Exception as e:
        log_error(f"❌ Error querying Notion database for pending actions:\n{e}\n")
        return []


def unscheduled_count():
    """Query Notion for actions that are NOT scheduled (no Do Date)."""
    payload = {
        "filter": {
            "and": [
                {"property": "Done", "checkbox": {"equals": False}},
                {"property": "Waiting", "checkbox": {"equals": False}},
                {"property": "Do Date", "date": {"is_empty": True}},
            ]
        }
    }

    try:
        data = query_notion_database(NOTION_ACTION_DATABASE_ID, payload)
        return len(data.get("results", []))
    except Exception as e:
        log_error(f"❌ Error querying Notion database for unscheduled actions:\n{e}\n")
        return 0


def query_notion_waiting():
    """Query Notion for actions that are NOT done and ARE marked as Waiting."""
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

    try:
        data = query_notion_database(NOTION_ACTION_DATABASE_ID, payload)
        return data.get("results", [])
    except Exception as e:
        log_error(f"❌ Error querying Notion database for waiting items:\n{e}\n")
        return []


def count_contacts_needing_review():
    """Count Contacts with Needs Review == true."""
    payload = {
        "filter": {
            "property": "Needs Review",
            "checkbox": {"equals": True},
        }
    }

    try:
        data = query_notion_database(NOTION_CONTACTS_DATABASE_ID, payload)
        return len(data.get("results", []))
    except Exception as e:
        log_error(f"❌ Error querying Contacts needing review:\n{e}\n")
        return 0


def count_interactions_project_review():
    """Count Interactions with Project Review == true."""
    payload = {
        "filter": {
            "property": "Project Review",
            "checkbox": {"equals": True},
        }
    }

    try:
        data = query_notion_database(NOTION_INTERACTIONS_DATABASE_ID, payload)
        return len(data.get("results", []))
    except Exception as e:
        log_error(f"❌ Error querying Interactions for project review:\n{e}\n")
        return 0


def get_weekly_goals_markdown():
    """
    Fetch Weekly Goals from the Action Zone page.

    Assumes:
      - NOTION_ACTION_ZONE_PAGE_ID is a page
      - There is a toggle_heading_1 (or heading_1) whose text == "Weekly Goals"
      - Its nested children (for a toggle) are bulleted_list_item blocks
    """
    headers = {
        "Authorization": f"Bearer {NOTION_SECRET}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    # 1) Get top-level children of Action Zone page
    url = f"{NOTION_API_URL}/blocks/{NOTION_ACTION_ZONE_PAGE_ID}/children"

    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log_error(f"❌ Error fetching Action Zone blocks:\n{e}\n")
        return None

    blocks = data.get("results", [])

    weekly_toggle_block = None

    for block in blocks:
        btype = block.get("type")

        # Handle both toggle_heading_1 and plain heading_1, just in case
        if btype in {"toggle_heading_1", "heading_1"}:
            rich = block[btype]["rich_text"]
            text = "".join([r.get("plain_text", "") for r in rich]).strip()
            if text.lower() == "weekly goals":
                weekly_toggle_block = block
                break

    if weekly_toggle_block is None:
        # Could not find the Weekly Goals heading/toggle
        return None

    # If it's a toggle, its bullet children will be in its own children endpoint
    block_id = weekly_toggle_block["id"]

    # For a heading_1 that is not a toggle, you might instead look at subsequent siblings,
    # but per your description it's a toggle with nested bullets.
    child_url = f"{NOTION_API_URL}/blocks/{block_id}/children"

    try:
        resp = requests.get(child_url, headers=headers)
        resp.raise_for_status()
        child_data = resp.json()
    except Exception as e:
        log_error(f"❌ Error fetching Weekly Goals child blocks:\n{e}\n")
        return None

    child_blocks = child_data.get("results", [])
    items = []

    for block in child_blocks:
        if block.get("type") == "bulleted_list_item":
            rich = block["bulleted_list_item"]["rich_text"]
            text = "".join([r.get("plain_text", "") for r in rich]).strip()
            if text:
                items.append(f"- {text}")

    if not items:
        return None

    lines = ["Weekly Goals", ""]
    lines.extend(items)
    return "\n".join(lines)


# --------------------
# Formatting helpers
# --------------------


def extract_action_names(results):
    """Extract the 'Name' (title) property from each result."""
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


def build_checklist_section(title: str, actions):
    """Build markdown checklist text from action names."""
    empty_text = {
        "Pending Actions": "No pending actions.",
        "Awaiting Responses": "No items awaiting responses.",
    }.get(title, f"No {title.lower()}.")

    if not actions:
        return f"{title}:\n\n_{empty_text}_"

    lines = [f"{title}:", ""]
    for a in actions:
        lines.append(f"- [ ] {a}")

    return "\n".join(lines)


# --------------------
# Joplin integration
# --------------------


def create_joplin_note(title: str, body: str):
    notes_url = f"{JOPLIN_BASE_URL}/notes"
    params = {"token": JOPLIN_TOKEN}
    payload = {
        "title": title,
        "body": body,
        "parent_id": JOPLIN_TODO_FOLDER_ID,  # send note to "To Dos"
    }

    try:
        resp = requests.post(notes_url, params=params, json=payload)
        resp.raise_for_status()
        data = resp.json()
        note_id = data.get("id")
        log(f"✅ Created Joplin note with id: {note_id}")
    except Exception as e:
        log_error(f"❌ Error creating Joplin note: {e}")


# --------------------
# Main
# --------------------


def main():
    # Weekly Goals at the very top
    weekly_goals_md = get_weekly_goals_markdown()

    # Existing Notion queries
    pending_results = query_notion_actions()
    pending_actions = extract_action_names(pending_results)

    waiting_results = query_notion_waiting()
    waiting_actions = extract_action_names(waiting_results)

    unscheduled = unscheduled_count()

    # New CRM-related counts
    contacts_needing_review = count_contacts_needing_review()
    interactions_project_review = count_interactions_project_review()

    # Skip entirely only if absolutely nothing to say
    if (
        not weekly_goals_md
        and not pending_actions
        and not waiting_actions
        and unscheduled == 0
        and contacts_needing_review == 0
        and interactions_project_review == 0
    ):
        log("ℹ️ No actions or CRM items to send to Joplin today.")
        return

    sections = []

    # 1) Weekly Goals at top (if available)
    if weekly_goals_md:
        sections.append(weekly_goals_md)
        sections.append("---")

    # 2) Pending Actions section
    pending_section = build_checklist_section("Pending Actions", pending_actions)
    if pending_section:
        sections.append(pending_section)

    # 3) Waiting section
    waiting_section = build_checklist_section("Awaiting Responses", waiting_actions)
    if waiting_section:
        if pending_section:
            sections.append("---")
        sections.append(waiting_section)

    # 4) Unscheduled footer
    if unscheduled > 0:
        sections.append("---")
        sections.append("&nbsp;")  # spacer
        sections.append(
            f"Unscheduled actions in Notion (no Do Date): **{unscheduled}**"
        )

    # 5) CRM counts footer
    if contacts_needing_review > 0 or interactions_project_review > 0:
        sections.append("---")
        sections.append("CRM Review")
        if contacts_needing_review > 0:
            sections.append(f"- Contacts needing review: **{contacts_needing_review}**")
        if interactions_project_review > 0:
            sections.append(
                f"- Interactions marked for project review: "
                f"**{interactions_project_review}**"
            )

    checklist_text = "\n\n".join(sections)

    today_str = datetime.now().strftime("%d-%m-%Y")
    title = f"Notion To Dos – {today_str}"
    create_joplin_note(title, checklist_text)

    log("✅ notojo.py completed successfully and synced to Joplin.")


if __name__ == "__main__":
    main()