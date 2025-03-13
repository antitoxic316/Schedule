from __future__ import print_function

import time
import json

import os.path

import argparse

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def read_raw_s(f_name):
    with open(f_name, 'r', encoding='utf-8') as f:
        return f.readlines()

def split_lines(lines):
    for i in range(0,len(lines)):
        line = list(lines[i])
        if line[len(line)-1] == '\n':
            line.pop(-1)
        lines[i] = "".join(line)

        lines[i] = lines[i].split('/')
    return lines

def trim_lines(lines):
    TIME_IND = 0
    DAYS_IND = 3
    for i in range(0, len(lines)):
        for j in lines[i][TIME_IND]:
            if j == " ":
                lines[i][TIME_IND] = lines[i][TIME_IND].replace(j, "")
        for j in lines[i][DAYS_IND]:
            if j == " ":
                lines[i][DAYS_IND] = lines[i][DAYS_IND].replace(j, "")
    return lines

def make_events(lines):
    events = []
    

    for line in lines:
        dates = line[-1].split(',')
        for date in dates:
            gmt = time.localtime(time.time()).tm_hour - time.gmtime().tm_hour
            year = date.split(".")[2]
            day = date.split(".")[0]
            month = date.split(".")[1]
            stHour =    int(line[0].split("-")[0].split(":")[0])-gmt
            if stHour < 10: stHour = "0" + str(stHour)
            stMinutes = line[0].split("-")[0].split(":")[1]
            enHour =    int(line[0].split("-")[1].split(":")[0])-gmt
            if enHour < 10: enHour = "0" + str(enHour)
            enMinutes = line[0].split("-")[1].split(":")[1]
            # google calendar adds time to the event's time so i am taking it back here

            startTime = f"{year}-{month}-{day}T{stHour}:{stMinutes}:00.000Z"
            endTime = f"{year}-{month}-{day}T{enHour}:{enMinutes}:00.000Z"
            events.append({
                            'summary': line[1],
                            'location': '',
                            'description': line[2],
                            'start': {
                                'dateTime': startTime,
                                'timeZone': 'GMT+01:00'
                            },
                            'end': {
                                'dateTime': endTime,
                                'timeZone': 'GMT+01:00'
                            },
                            'reminders': {
                                'useDefault': False,
                                'overrides': [
                                {'method': 'popup', 'minutes': '30'}
                                ]
                            }
                        })
    return events

def save_events(events):
    with open('events.json', 'w', encoding='utf-8') as f:
        json.dump(events,f,indent=6,ensure_ascii=False)

def load_events():
    with open('events.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def authorise_google():
    SCOPES = ['https://www.googleapis.com/auth/calendar.events']

    creds = None

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        print(creds)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds

def create_calender_resource(credentials):
    creds = authorise_google(credentials)
    if(not creds):
        raise Exception("credential not found")
    
    try:
        calendar = build('calendar', 'v3', credentials=creds)
    except HttpError as error:
        print('An error occurred: %s' % error)

    return calendar

def clear_google_calendar_events(cal_resource, calID):
    try:
        old_events = cal_resource.events().list(
            calendarId=calID
        ).execute()
        for old_event in old_events["items"]:
            cal_resource.events().delete(calendarId=calID, eventId=old_event["id"]).execute()
    except HttpError as error:
        print('An error occurred: %s' % error)

def add_events_to_google(events, cal_resource, calID):
    try:
        for event in events:
            cal_resource.events().insert(
                calendarId=calID,
                body=event
                            ).execute()
    except HttpError as error:
        print('An error occurred: %s' % error)

def main():
    parser = argparse.ArgumentParser(
                    prog='google-event-adder',
                    description='adds events from formated file for google calendar\n \
                    usage: \nadd-events filename calendarID'
                    )
    
    parser.add_argument('filename')
    parser.add_argument('calendarID')

    args = parser.parse_args()

    filename = args.filename
    calID = args.calendarID

    lines = trim_lines(split_lines(read_raw_s("s.txt")))
    save_events(make_events(lines))
    events = load_events()

    creds = authorise_google()
    cal_resource = create_calender_resource(creds)

    clear_google_calendar_events(cal_resource, calID)
    add_events_to_google(events, cal_resource, calID)

if __name__ == "__main__":
    main()