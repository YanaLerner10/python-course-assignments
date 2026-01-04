import os
import datetime
from dateutil import parser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# =====================
# USER SETTINGS
# =====================
YOUR_NAME = "רפאל"  # your name in the sheet
COLUMNS_OF_INTEREST = ["מיון", "עוזר ססיה"]
SPREADSHEET_ID = "1MhKxOBPTulc3Bg0ag9jK0aODjBXN0q_3UAJw2W8xYNA"
SHEET_TAB_NAME = "Sheet1"
TIMEZONE = "Asia/Jerusalem"
DRY_RUN = False  # True = test only, False = create events

# =====================
# GOOGLE API SCOPES
# =====================
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]

# =====================
# AUTHENTICATION
# =====================
def get_credentials():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w", encoding="utf-8") as token:
            token.write(creds.to_json())
    return creds

def get_services():
    creds = get_credentials()
    sheets_service = build("sheets", "v4", credentials=creds)
    calendar_service = build("calendar", "v3", credentials=creds)
    return sheets_service, calendar_service

# =====================
# READ SHEET
# =====================
def read_sheet(sheets, tab_name):
    """
    Reads a Google Sheet tab safely, handling Hebrew tab names and spaces.
    Returns headers and rows.
    """
    tab_name = tab_name.strip().strip("'").strip('"')
    range_str = f"{tab_name}!A:Z"  # read all columns A-Z
    result = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=range_str
    ).execute()
    values = result.get("values", [])
    if not values:
        raise Exception(f"Sheet tab '{tab_name}' is empty or not found.")
    headers = values[0]
    rows = values[1:]
    return headers, rows

# =====================
# CREATE CALENDAR EVENT
# =====================
def create_event(calendar, date_str, role):
    """
    Creates an all-day Google Calendar event.
    Parses dates flexibly.
    """
    # Try multiple formats
    try:
        # e.g., 02-02-26
        date = datetime.datetime.strptime(date_str, "%d-%m-%y").date()
    except ValueError:
        try:
            # e.g., 02.02.2026
            date = datetime.datetime.strptime(date_str, "%d.%m.%Y").date()
        except ValueError:
            # fallback to dateutil parser
            date = parser.parse(date_str, dayfirst=True).date()

    event = {
        "summary": f"תורנות – {role}",
        "start": {"date": date.isoformat(), "timeZone": TIMEZONE},
        "end": {"date": (date + datetime.timedelta(days=1)).isoformat(), "timeZone": TIMEZONE},
    }

    calendar.events().insert(calendarId="primary", body=event).execute()

# =====================
# MAIN
# =====================
def main():
    sheets, calendar = get_services()

    # Read the sheet
    headers, rows = read_sheet(sheets, SHEET_TAB_NAME)

    # Get column indexes
    col_indexes = {}
    for col in COLUMNS_OF_INTEREST:
        if col not in headers:
            raise Exception(f"Column '{col}' not found in the sheet.")
        col_indexes[col] = headers.index(col)

    # Loop through rows and create events
    for row in rows:
        if not row:
            continue

        date_str = row[0]  # first column must be date

        for role, idx in col_indexes.items():
            if len(row) > idx and row[idx].strip() == YOUR_NAME:
                if DRY_RUN:
                    print(f"[DRY RUN] {date_str} – {role}")
                else:
                    create_event(calendar, date_str, role)
                    print(f"Added {date_str} – {role}")

if __name__ == "__main__":
    main()
