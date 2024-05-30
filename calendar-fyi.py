import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Define the scope and the location of the credentials file
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'
load_dotenv()

def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    service = build('calendar', 'v3', credentials=creds)
    return service

def get_events(service, start, end):
    events_result = service.events().list(calendarId='primary', timeMin=start, timeMax=end,
                                          singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])
    return events

def format_datetime(date_str):
    try:
        dt = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%d %B %Y, %H:%M')
    except ValueError:
        return date_str

def format_events(events):
    email_body = "Next week's schedule:\n"
    if not events:
        email_body += "No events found for next week."
    else:
        for event in events:
            start_time = event['start'].get('dateTime', event['start'].get('date'))
            end_time = event['end'].get('dateTime', event['end'].get('date'))
            formatted_start_time = format_datetime(start_time)
            formatted_end_time = format_datetime(end_time)
            email_body += f"{formatted_start_time} - {formatted_end_time}: {event['summary']}\n"
    return email_body

def send_email(body):
    msg = MIMEMultipart()
    msg['From'] = os.getenv('SENDER_EMAIL_ADDRESS')
    msg['To'] = os.getenv('RECIPIENT_EMAIL_ADDRESS')
    msg['Subject'] = "Next Week's Schedule"

    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(os.getenv('SENDER_EMAIL_ADDRESS'), os.getenv('EMAIL_PASSWORD'))
    server.send_message(msg)
    server.quit()

def main():
    service = get_calendar_service()
    now = datetime.datetime.utcnow()
    start = (now + datetime.timedelta(days=(0 - now.weekday()))).isoformat() + 'Z'
    end = (now + datetime.timedelta(days=(7 - now.weekday()))).isoformat() + 'Z'

    events = get_events(service, start, end)
    email_body = format_events(events)
    print(email_body)
    send_email(email_body)

if __name__ == '__main__':
    main()
