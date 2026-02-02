import os
import sys
from dotenv import load_dotenv
from notion_utils import query_notion_database

load_dotenv()

def inspect_database(db_id, label):
    print(f"\n=== Inspecting {label} ({db_id}) ===")
    try:
        # Query with page_size=1 just to get the schema from the first result
        data = query_notion_database(db_id, {"page_size": 1})
        results = data.get("results", [])
        
        if not results:
            print(f"No records found in the {label} database.")
            return

        properties = results[0].get("properties", {})
        print(f"{'Property Name':<30} | {'Type':<15}")
        print("-" * 50)
        for name, info in properties.items():
            p_type = info.get("type")
            print(f"{name:<30} | {p_type:<15}")
            
            # Special handling to show current values for tricky types
            if p_type == 'select':
                val = info.get("select")
                print(f"   └─ Current Value: {val['name'] if val else 'None'}")
            elif p_type == 'status':
                val = info.get("status")
                print(f"   └─ Current Value: {val['name'] if val else 'None'}")

    except Exception as e:
        print(f"Error inspecting {label}: {e}")

def main():
    databases = {
        "1": ("NOTION_ACTION_DATABASE_ID", "Actions"),
        "2": ("NOTION_PROJECTS_DATABASE_ID", "Projects"),
        "3": ("NOTION_CONTACTS_DATABASE_ID", "Contacts"),
        "4": ("NOTION_INTERACTIONS_DATABASE_ID", "Interactions"),
    }

    print("Which database would you like to inspect?")
    for key, (env_var, label) in databases.items():
        print(f"{key}. {label} ({env_var})")
    
    choice = input("\nEnter number: ").strip()
    
    if choice in databases:
        env_var, label = databases[choice]
        db_id = os.environ.get(env_var)
        if db_id:
            inspect_database(db_id, label)
        else:
            print(f"Error: {env_var} not found in .env file.")
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()