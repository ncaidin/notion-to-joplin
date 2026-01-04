import requests
import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

NOTION_SECRET = os.environ.get("NOTION_SECRET")
NOTION_CONTACTS_DATABASE_ID = os.environ.get("NOTION_CONTACTS_DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_SECRET}",
    "Notion-Version": "2022-06-28",
}

url = f"https://api.notion.com/v1/databases/{NOTION_CONTACTS_DATABASE_ID}"
resp = requests.get(url, headers=headers)
print(resp.json())
