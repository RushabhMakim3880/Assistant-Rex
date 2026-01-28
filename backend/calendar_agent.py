import os
import datetime
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

class CalendarAgent:
    def __init__(self, credentials_path="credentials.json", token_path="token.pickle"):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.scopes = ['https://www.googleapis.com/auth/calendar']
        
        # Try to authenticate on init, but don't fail if creds are missing (user might not have set them up)
        try:
            self.authenticate()
        except Exception as e:
            print(f"[CalendarAgent] Init Warning: {e}")

    def authenticate(self):
        """Authenticates the user and creates/loads the token.pickle."""
        creds = None
        
        # Resolve paths robustness (Root vs Backend)
        if not os.path.exists(self.credentials_path):
             # Try checking backend/ folder
             alt_path = os.path.join("backend", self.credentials_path)
             if os.path.exists(alt_path):
                 self.credentials_path = alt_path
                 print(f"[CalendarAgent] Found credentials at: {self.credentials_path}")
        
        # Handle token path similarly
        if not os.path.exists(self.token_path):
             alt_token = os.path.join("backend", self.token_path)
             if os.path.exists(alt_token):
                 self.token_path = alt_token

        # The file token.pickle stores the user's access and refresh tokens
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                print(f"[CalendarAgent] Error loading token: {e}. Re-authenticating.")
                creds = None
                
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"[CalendarAgent] Error refreshing token: {e}. Re-authenticating.")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_path):
                    print(f"[CalendarAgent] [ERR] Credentials file not found at '{self.credentials_path}' or 'backend/{os.path.basename(self.credentials_path)}'. Cannot authenticate.")
                    raise FileNotFoundError(f"Credentials file '{self.credentials_path}' not found. Please download it from Google Cloud Console and place it in the backend folder.")
                
                print("[CalendarAgent] Starting local server for OAuth...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.scopes)
                creds = flow.run_local_server(port=0)
                
            # Save the credentials for the next run
            # Force save to backend if not absolute
            save_path = self.token_path
            if not os.path.exists(os.path.dirname(save_path)) and "backend" not in save_path:
                 save_path = os.path.join("backend", "token.pickle")
            
            with open(save_path, 'wb') as token:
                pickle.dump(creds, token)
            print(f"[CalendarAgent] Token saved to {save_path}")

        self.service = build('calendar', 'v3', credentials=creds)
        print("[CalendarAgent] Successfully authenticated with Google Calendar.")

    def list_upcoming_events(self, max_results=10):
        """Lists the next 10 upcoming events from the primary calendar."""
        if not self.service:
            return "Calendar service not initialized. Please authenticate."

        now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
        print(f"[CalendarAgent] Fetching {max_results} upcoming events")
        
        events_result = self.service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=max_results, singleEvents=True,
            orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            return "No upcoming events found."
        
        event_list = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No Title')
            event_list.append(f"- {start}: {summary}")
            
        return "\n".join(event_list)

    def create_event(self, summary, start_time, end_time=None, description=""):
        """Creates a new event. start_time expected in ISO format or datetime object."""
        if not self.service:
            return "Calendar service not initialized."
            
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC', # Should ideally be parameterized
            },
            'end': {
                'dateTime': end_time if end_time else (datetime.datetime.fromisoformat(start_time) + datetime.timedelta(hours=1)).isoformat(),
                'timeZone': 'UTC',
            },
        }

        event = self.service.events().insert(calendarId='primary', body=event).execute()
        return f"Event created: {event.get('htmlLink')}"
