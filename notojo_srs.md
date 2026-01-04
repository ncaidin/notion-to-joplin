# Software Requirements Specification (SRS)

**System:** Notion → Joplin Daily Sync (`notojo.py`)  
**Version:** 1.0  
**Author:** _[your name]_  
**Date:** _[fill in]_

---

## 1. Introduction

### 1.1 Purpose

This document specifies the requirements for the **Notion → Joplin Daily Sync** script (`notojo.py`).

The script automatically generates a daily Markdown note in Joplin that summarizes:

- Action items from a Notion Actions database
- Weekly Goals from a Notion Action Zone page
- CRM review counts from Notion Contacts and Interactions databases

This SRS is intended to guide development, testing, and future enhancements of the script.

### 1.2 Scope

The scope of `notojo.py` includes:

- Reading data from Notion via the Notion API using a single integration token.
- Transforming that data into a human-readable Markdown summary.
- Creating a daily note in a specified Joplin folder via the Joplin Web Clipper/Data API.
- Being invoked periodically (e.g., by macOS `launchd`) to run once per day.

Out of scope:

- Any GUI or interactive interface.
- Editing or deleting existing Joplin notes.
- Bi-directional sync (e.g., marking items done in Notion based on Joplin).
- Management of multiple users or workspaces.

### 1.3 Definitions, Acronyms, and Abbreviations

- **Notion**: A note-taking and database application providing an HTTP API.
- **Joplin**: An open-source note-taking application that exposes a Web Clipper/Data API.
- **Action Zone**: A specific Notion page that contains the user’s “Weekly Goals”.
- **Actions Database**: A Notion database used to track actions/tasks.
- **Contacts Database**: A Notion database used as a mini-CRM for contacts.
- **Interactions Database**: A Notion database used as a mini-CRM for interactions.
- **Weekly Goals**: A set of bulleted goals for the current week, stored as a Notion toggle/heading block with nested bullets.
- **LaunchAgent / launchd**: macOS system for scheduling and managing background processes.
- **`.env` file**: A file containing environment variables used to configure the script.
- **Integration Token / Notion Secret**: The secret token used to authenticate Notion API calls.

### 1.4 References

- Notion API reference (Blocks, Databases, Pages)
- Joplin Web Clipper / Data API documentation
- macOS `launchd` / LaunchAgent documentation

---

## 2. Overall Description

### 2.1 Product Perspective

`notojo.py` is a standalone command-line Python script that:

- Runs in a specific project directory with a `.env` file.
- Uses a virtual environment (Python venv) for dependencies.
- Communicates with external systems via HTTP/HTTPS.

It is typically triggered once per day by a macOS `launchd` LaunchAgent configuration and writes a new note into Joplin.

### 2.2 Product Functions (High-Level)

At a high level, the script:

1. Loads configuration from a `.env` file and validates required variables.
2. Queries Notion for:
   - Weekly Goals from a single page.
   - Pending and waiting actions from an Actions database.
   - Unscheduled actions count.
   - Counts for:
     - Contacts with “Needs Review” checked.
     - Interactions with “Project Review” checked.
3. Assembles a Markdown note with:
   - Weekly Goals.
   - Action checklists and counts.
   - CRM counts.
4. Creates a new note in Joplin with a date-specific title in a specified Joplin folder.

### 2.3 User Characteristics

- Primary (and currently only) user is a technically literate individual comfortable with:
  - Editing `.env` files.
  - Running Python scripts from the command line.
  - Configuring Notion integrations.
  - Setting up `launchd` jobs on macOS.

No non-technical end-users are expected at this time.

### 2.4 Constraints

- Must run on a system with:
  - Python 3.x.
  - Internet access to reach Notion’s API.
  - A running Joplin instance with Web Clipper/Data API enabled.
- Depends on:
  - Valid Notion integration token with access to relevant databases/pages.
  - Correct database/page IDs and Joplin token configured in `.env`.
- Uses environment variables rather than hard-coded secrets.
- Currently uses a hard-coded Joplin folder ID in the script.

### 2.5 Assumptions and Dependencies

- Joplin is running and its API is reachable at `JOPLIN_BASE_URL`.
- Notion integration has been explicitly added to:
  - The Actions database.
  - The Contacts database.
  - The Interactions database.
  - The Action Zone page.
- The structure of the Weekly Goals section remains:
  - A toggle or heading block labeled “Weekly Goals”.
  - With bullet items nested under that toggle.

---

## 3. System Features

### 3.1 Feature: Configuration & Startup Validation

**Description**

On startup, the script reads environment variables from `.env` and ensures required values are present.

**Inputs**

`.env` file in the same directory as `notojo.py`.

**Required environment variables**

- `NOTION_SECRET`
- `NOTION_ACTION_DATABASE_ID`
- `NOTION_CONTACTS_DATABASE_ID`
- `NOTION_INTERACTIONS_DATABASE_ID`
- `NOTION_ACTION_ZONE_PAGE_ID`
- `JOPLIN_TOKEN`

**Optional environment variables**

- `JOPLIN_BASE_URL` (default: `http://127.0.0.1:41184`)

**Processing**

1. Load variables via `dotenv`.
2. Check each variable in the required list.
3. If any are missing:
   - Log each missing variable name to stderr.
   - Exit with a non-zero status.

**Outputs**

- Error messages if configuration is incomplete.
- Normal execution continues only if all required variables are present.

---

### 3.2 Feature: Weekly Goals Extraction

**Description**

Fetch “Weekly Goals” from the Notion Action Zone page and convert them to Markdown.

**Inputs**

- `NOTION_ACTION_ZONE_PAGE_ID`
- `NOTION_SECRET`
- Notion blocks on the Action Zone page.

**Processing**

1. Call the Notion API:

   - `GET /v1/blocks/{NOTION_ACTION_ZONE_PAGE_ID}/children`

2. Search the returned blocks for the first block where:
   - `type` is `toggle_heading_1` or `heading_1`, and
   - The combined text equals “Weekly Goals” (case-insensitive).

3. If such a block is found:
   - Retrieve its children via:

     - `GET /v1/blocks/{block_id}/children`

   - Collect all child blocks of type `bulleted_list_item`.
   - Extract bullet text and form Markdown list items.

**Outputs**

If at least one bullet is found:

```markdown
Weekly Goals

- Goal 1
- Goal 2
...
```

**Error / Exceptional Conditions**

- If the page is not accessible or the Weekly Goals heading is not present, this feature is skipped (from the user’s point of view) and an error is logged to stderr.

---

### 3.3 Feature: Pending Actions Section

**Description**

Generate a checklist of pending actions based on the Notion Actions database.

**Inputs**

- `NOTION_ACTION_DATABASE_ID`
- Fields within that database:
  - `Done` (checkbox)
  - `Waiting` (checkbox)
  - `Do Date` (date)
  - `Name` (title)

**Processing**

1. Query Notion database with filter:
   - `Done == false`
   - `Waiting == false`
   - `Do Date on_or_before today (UTC date)`
2. Extract the `Name` property as the action label (first title fragment’s `plain_text`).
3. Build a Markdown checklist.

**Outputs**

If at least one result:

```markdown
Pending Actions:

- [ ] Action 1
- [ ] Action 2
```

If no results:

```markdown
Pending Actions:

_No pending actions._
```

**Error Handling**

On query error, log an error and treat as if there are no pending actions.

---

### 3.4 Feature: Awaiting Responses Section

**Description**

Generate a checklist of actions that are still pending and marked as “Waiting”.

**Inputs**

- Same Actions database as above.

**Processing**

1. Query Notion database with filter:
   - `Done == false`
   - `Waiting == true`
   - `Do Date on_or_before today (UTC date)`
2. Extract `Name` titles.
3. Build Markdown checklist.

**Outputs**

If non-empty:

```markdown
Awaiting Responses:

- [ ] Item 1
- [ ] Item 2
```

If empty:

```markdown
Awaiting Responses:

_No items awaiting responses._
```

---

### 3.5 Feature: Unscheduled Actions Count

**Description**

Show the count of actions that are neither done nor waiting, and have no “Do Date”.

**Inputs**

- Same Actions database.

**Processing**

1. Query database with filter:
   - `Done == false`
   - `Waiting == false`
   - `Do Date is_empty`
2. Count results.

**Outputs**

If count `> 0`, append:

```markdown
---
&nbsp;

Unscheduled actions in Notion (no Do Date): **N**
```

If count is `0`, omit this section.

---

### 3.6 Feature: CRM Counts (Contacts & Interactions)

**Description**

Compute and display two CRM-related counts in the daily note.

#### 3.6.1 Contacts Needing Review

**Inputs**

- `NOTION_CONTACTS_DATABASE_ID`
- Checkbox property `"Needs Review"` in that database.

**Processing**

1. Query database with filter:
   - `Needs Review == true`
2. Count matching entries.

**Outputs**

- Value `contacts_needing_review` used in the CRM section.

#### 3.6.2 Interactions Marked for Project Review

**Inputs**

- `NOTION_INTERACTIONS_DATABASE_ID`
- Checkbox property `"Project Review"` in that database.

**Processing**

1. Query database with filter:
   - `Project Review == true`
2. Count matching entries.

**Outputs**

- Value `interactions_project_review` used in the CRM section.

#### 3.6.3 CRM Review Section Assembly

**Behavior**

Let:

- `contacts_needing_review` = Contacts count.
- `interactions_project_review` = Interactions count.

If either count is greater than zero:

```markdown
---
CRM Review
- Contacts needing review: **X**       # only if X > 0
- Interactions marked for project review: **Y**   # only if Y > 0
```

If both counts are zero, this section is omitted.

---

### 3.7 Feature: Note Assembly & Creation in Joplin

**Description**

Combine all sections into a single Markdown document and create a new Joplin note.

**Inputs**

- Outputs from all other features (sections and counts).
- `JOPLIN_TOKEN`, `JOPLIN_BASE_URL`, `JOPLIN_TODO_FOLDER_ID`.

**Note Title**

- `Notion To Dos – DD-MM-YYYY`  
  (DD-MM-YYYY = current local date)

**Section Order**

1. Weekly Goals (if available), followed by `---`.
2. Pending Actions.
3. Awaiting Responses (with `---` separator if Pending also present).
4. Unscheduled Actions footer (if count > 0).
5. CRM Review section (if at least one CRM count > 0).

**Behavior for “No Content” Case**

If all of the following are true:

- No Weekly Goals content.
- No pending actions.
- No waiting actions.
- Unscheduled count == 0.
- Contacts needing review == 0.
- Interactions for project review == 0.

Then:

- Log an informational message such as “No actions or CRM items to send to Joplin today.”
- Do **not** create a note.

**Joplin API Call**

- `POST {JOPLIN_BASE_URL}/notes?token={JOPLIN_TOKEN}`

Payload:

```json
{
  "title": "<computed title>",
  "body": "<assembled markdown body>",
  "parent_id": "<JOPLIN_TODO_FOLDER_ID>"
}
```

---

## 4. External Interface Requirements

### 4.1 Software Interfaces

**Notion API**

- Endpoints used:
  - `GET /v1/blocks/{block_id}/children`
  - `GET /v1/databases/{database_id}`
  - `POST /v1/databases/{database_id}/query`
- Authentication:
  - `Authorization: Bearer <NOTION_SECRET>`
  - `Notion-Version: 2022-06-28` (or configured API version)

**Joplin API**

- Endpoint used:
  - `POST /notes?token={JOPLIN_TOKEN}`
- Base URL:
  - Configurable via `JOPLIN_BASE_URL`.

### 4.2 User Interfaces

- Command-line execution only.
- No GUI; feedback is via stdout/stderr logs.

### 4.3 Communications Interfaces

- HTTP/HTTPS over TCP/IP to:
  - Notion’s public API endpoint.
  - Joplin’s local API endpoint.

---

## 5. Non-Functional Requirements

### 5.1 Performance Requirements

- Under normal conditions, the script should:
  - Complete within a few seconds.
  - Make a small, bounded number of Notion and Joplin API calls.

### 5.2 Reliability & Fault Tolerance

- On Notion API errors for a particular feature (e.g., Weekly Goals, CRM counts):
  - That feature is skipped.
  - Other features still run.
- On Joplin API failure:
  - An error is logged.
  - The script terminates after logging (no retry logic yet).

### 5.3 Security Requirements

- Secrets (Notion token, Joplin token, IDs) are:
  - Stored in `.env`.
  - Not hard-coded in source.
- Script assumes local machine security is handled by the user (file permissions, etc.).

### 5.4 Maintainability

- Centralized configuration via `.env`.
- Clear decomposition into:
  - Data-fetching functions.
  - Formatting helpers.
  - A single `main()` orchestrator.
- Sufficient logging for debugging and future extension.

---

## 6. Other Requirements / Future Enhancements

Potential future features (not currently implemented, but relevant for roadmap):

- Schema dump utility for Notion databases (for introspection/debugging).
- Idempotent daily notes (update existing note instead of creating a new one).
- Optional always-visible CRM section (even when counts are zero).
- Configurable Joplin folder via `.env` rather than hard-coded ID.
- Additional Notion sections (e.g., Overdue vs Due-today separation).
- More robust error reporting and alerting.
