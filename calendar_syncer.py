import os
import pytz
import caldav
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv
from icalendar import Event as iCalEvent

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    filename='calendar_syncer.log',
                    filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Function to fetch time entries from Clockify
def fetch_time_entries(start_date: str, end_date: str) -> dict:
    
    url = f"{os.getenv('BASE_URL')}/workspaces/{os.getenv('WORKSPACE_ID')}/user/{os.getenv('USER_ID')}/time-entries?start={start_date}&end={end_date}&page-size=800"
    HEADERS = {'X-Api-Key': os.getenv('API_KEY')}
    response = requests.get(url, headers=HEADERS)
    logging.info(f"Fetching time entries from {start_date[:10]} to {end_date[:10]}")
    return response.json()

# Connect to iCloud and get the  calendar
def get_calendar(calendar_name: str) -> caldav.Calendar:
    """
    The function `get_calendar` takes a calendar name as input and returns the corresponding calendar
    object if found, otherwise it returns None.
    
    :param calendar_name: The `calendar_name` parameter is a string that represents the name of the
    calendar you want to retrieve
    :type calendar_name: str
    :return: a `caldav.Calendar` object.
    """
    
    client = caldav.DAVClient(url=os.getenv('ICLOUD_CALDAV_URL'), username=os.getenv('ICLOUD_USERNAME'), password=os.getenv('ICLOUD_PASSWORD'))
    principal = client.principal()
    calendars = principal.calendars()
    for calendar in calendars:
        if calendar.name.lower() == calendar_name.lower():
            return calendar
    
    return None

# Add entries to the 'work' calendar
def add_entries_to_calendar(calendar: caldav.Calendar, time_entries: list[dict], timezone: str = 'Europe/Rome') -> None:
    """
    The function `add_entries_to_calendar` adds time entries to a calendar using the CalDAV protocol.
    
    :param calendar: The `calendar` parameter is an instance of the `caldav.Calendar` class. It
    represents the calendar to which the time entries will be added
    :type calendar: caldav.Calendar
    :param time_entries: The `time_entries` parameter is a list of dictionaries, where each dictionary
    represents a time entry. Each time entry dictionary should have the following keys:
    :type time_entries: list[dict]
    :param timezone: The `timezone` parameter is a string that represents the timezone in which the
    calendar events should be saved. It defaults to 'Europe/Rome' if not provided, defaults to
    Europe/Rome
    :type timezone: str (optional)
    """
    
    for entry in time_entries:
        start = datetime.strptime(entry['timeInterval']['start'], '%Y-%m-%dT%H:%M:%SZ')
        end = datetime.strptime(entry['timeInterval']['end'], '%Y-%m-%dT%H:%M:%SZ')
        event = iCalEvent()
        event.add('summary', entry.get('description', 'Work Entry'))
        event.add('dtstart', start.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(timezone)))
        event.add('dtend', end.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(timezone)))
        event.add('dtstamp', datetime.now().replace(tzinfo=pytz.utc).astimezone(pytz.timezone(timezone)))
        event['uid'] = entry['id']  # Use Clockify entry ID as UID for the calendar event
        calendar.save_event(event.to_ical())
        logging.info(f"Added entry: {entry['description']} - Date: {start.strftime('%d-%m-%Y')} - Calendar: {calendar.name}")

# Main function to fetch entries and add them to the calendar
def main():
    """
    The main function fetches time entries within a specified date range and adds them to a calendar
    named 'work', logging an error if the calendar is not found.
    """
    start_date = '2024-01-01T00:00:00Z'
    end_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    calendar_name = 'work'
    timezone = 'Europe/Rome'

    time_entries = fetch_time_entries(start_date, end_date)
    calendar = get_calendar(calendar_name=calendar_name)
    if calendar:
        add_entries_to_calendar(calendar=calendar, time_entries=time_entries, timezone=timezone)
        logging.info(f"Entries for dates: {start_date[:10]} to {end_date[:10]} added to the '{calendar_name}' calendar.")
    else:
        logging.error("Work calendar not found.")

if __name__ == "__main__":
    main()
