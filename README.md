# Notion to Joplin (notojo)

Small Python utility to pull tasks from a Notion database and create a
Markdown checklist note in Joplin, using the Joplin Web Clipper API.

Current features:

- Query Notion for "Pending Actions"
- Query Notion for "Awaiting Responses"
- Query Notion for a count of unscheduled actions
- Generate a single Markdown note with multiple sections
- Create a daily Joplin note with a date-based title

## Requirements

- Python 3.9+ (tested with 3.13 on macOS)
- Notion API integration and database ID
- Joplin desktop with Web Clipper enabled

## Installation

Clone the repo and set up a virtual environment (optional but recommended):

```bash
git clone https://github.com/ncaidin/notion-to-joplin.git
cd notion-to-joplin

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

Configuration

This script expects secrets/config to come from environment variables
(or a .env file if you’re using python-dotenv):
	•	NOTION_SECRET
	•	NOTION_ACTION_DATABASE_ID
	•	NOTION_VERSION (e.g. 2022-06-28)
	•	JOPLIN_CLIPPER_URL
	•   JOPLIN_TOKEN

Usage

From the project root:
source .venv/bin/activate  # if using a venv
python notojo.py

The script will:
	1.	Query Notion for pending actions and items awaiting responses.
    2.  Count the number of unscheduled actions
	3.	Generate a Markdown checklist grouped into sections.
	4.	Create or update a daily note in Joplin with those sections.

You can run this manually or via a cron job / scheduled task.

License

MIT — see LICENSE file for details.
