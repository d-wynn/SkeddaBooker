#!/usr/bin/env python3
"""
Skedda Booking Automation Script

This script automates bookings on Skedda for any bookable space (parking, desks, 
meeting rooms, etc.) using GitHub Actions or locally. It tries each available 
space in order until it finds one that's free and books it automatically.

Note: This script only works with Skedda instances that use SSO authentication.

Timezone: Uses pytz to handle daylight saving time automatically. Set TIMEZONE 
env var to your timezone (default: Australia/Melbourne).
"""

import os
import sys
import json
import requests
import urllib.parse
from datetime import datetime, timedelta

class SkeddaBooker:
    def __init__(self):
        # Load config from env vars or config file
        self.base_url = os.getenv('SKEDDA_BASE_URL', 'https://your-instance.skedda.com')
        self.venue_id = os.getenv('SKEDDA_VENUE_ID')
        self.user_id = os.getenv('SKEDDA_USER_ID')
        self.session = requests.Session()
        
        if not self.venue_id or not self.user_id:
            print("missing venue_id or user_id")
            sys.exit(1)
        
        # Set up headers for API requests
        self.headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json; charset=utf-8',
            'origin': self.base_url,
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        self.load_spaces()
        self.load_auth()

    def load_auth(self):
        # Try to get auth from env first, then config file
        cookies_str = os.getenv('SKEDDA_COOKIES')
        token = os.getenv('SKEDDA_TOKEN')
        
        if not cookies_str:
            try:
                with open('config.json', 'r') as f:
                    config = json.load(f)
                cookies_str = config['SKEDDA_COOKIES']
                token = config['SKEDDA_TOKEN']
            except:
                print("missing config - run --setup first")
                sys.exit(1)
        
        self.cookies = self.parse_cookies(cookies_str)
        self.token = token.strip()

    def parse_cookies(self, cookie_str):
        # Convert cookie string into a dict
        cookies = {}
        cookie_str = cookie_str.strip().strip('"')
        
        for cookie in cookie_str.split('; '):
            if '=' in cookie:
                k, v = cookie.split('=', 1)
                # Decode URL-encoded values
                if '%' in v:
                    v = urllib.parse.unquote(v)
                cookies[k] = v
        
        return cookies

    def load_spaces(self):
        # Load available spaces from env or config
        spaces_json = os.getenv('SKEDDA_SPACES')
        
        if not spaces_json:
            try:
                with open('config.json', 'r') as f:
                    config = json.load(f)
                spaces_json = config.get('SKEDDA_SPACES')
            except:
                pass
        
        if not spaces_json:
            print("missing spaces config")
            sys.exit(1)
        
        try:
            self.spaces = json.loads(spaces_json)
        except json.JSONDecodeError:
            print("invalid spaces json")
            sys.exit(1)

    def log(self, msg):
        # Simple timestamped logging
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def get_bookings(self, date):
        # Fetch all bookings for the given date
        headers = self.headers.copy()
        headers['x-skedda-requestverificationtoken'] = self.token
        
        params = {
            'start': f"{date}T00:00:00",
            'end': f"{date}T23:59:59.999"
        }
        
        try:
            r = self.session.get(f"{self.base_url}/bookingslists", headers=headers, cookies=self.cookies, params=params)
            
            if r.status_code == 200:
                return r.json().get('bookings', [])
            elif r.status_code == 401:
                self.log("auth expired")
                return None
            else:
                self.log(f"failed: {r.status_code}")
                return None
        except Exception as e:
            self.log(f"error: {e}")
            return None

    def space_is_free(self, space_id, start_time, end_time, bookings):
        # Check if a space is available during the requested time
        target_start = datetime.fromisoformat(start_time)
        target_end = datetime.fromisoformat(end_time)
        
        for booking in bookings:
            # Handle different space data formats
            spaces = booking.get('spaces', [])
            if isinstance(spaces, str):
                spaces = [spaces]
            if booking.get('space'):
                spaces.append(booking['space'])
            
            if str(space_id) in [str(s) for s in spaces]:
                try:
                    start_str = booking.get('start', '')
                    end_str = booking.get('end', '')
                    
                    # Handle timezone formats
                    if start_str.endswith('Z'):
                        booking_start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                        booking_end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                    else:
                        booking_start = datetime.fromisoformat(start_str)
                        booking_end = datetime.fromisoformat(end_str)
                    
                    # Check for time overlap
                    if target_start < booking_end and target_end > booking_start:
                        return False
                except:
                    continue
        
        return True

    def book_space(self, space_id, start_time, end_time):
        # Submit a booking request for the space
        headers = self.headers.copy()
        headers['x-skedda-requestverificationtoken'] = self.token
        
        # Build the booking payload
        data = {
            "booking": {
                "endOfLastOccurrence": None,
                "title": None,
                "price": 0,
                "chargeTransactionId": None,
                "invoiceId": None,
                "lockInMargin": None,
                "stripPrivateEventDetails": False,
                "unrecognizedOrganizer": False,
                "type": 1,
                "paymentStatus": 0,
                "recurrenceRule": None,
                "decoupleDate": None,
                "createdDate": None,
                "customFields": [],
                "piId": None,
                "checkInAudits": None,
                "allowInviteOthers": False,
                "addConference": False,
                "hideAttendees": True,
                "availabilityStatus": 1,
                "syncType": None,
                "attendees": [],
                "start": start_time,
                "end": end_time,
                "arbitraryerrors": None,
                "spaces": [space_id],
                "venueuser": self.user_id,
                "venue": self.venue_id,
                "decoupleBooking": None
            }
        }
        
        try:
            r = self.session.post(f"{self.base_url}/bookings",
                                headers=headers, cookies=self.cookies, json=data)
            
            if r.status_code == 200:
                return space_id
            elif r.status_code == 422:
                try:
                    err = r.json()
                    if 'errors' in err and err['errors']:
                        self.log(f"rejected: {err['errors'][0].get('detail', 'validation error')}")
                except:
                    self.log("rejected")
                return False
            else:
                self.log(f"failed: {r.status_code}")
                return False
                
        except Exception as e:
            self.log(f"error: {e}")
            return False

    def run(self, date, start_time="08:30:00", end_time="17:00:00"):
        # Main booking logic - try each space until one succeeds
        start_dt = f"{date}T{start_time}"
        end_dt = f"{date}T{end_time}"
        
        # Get existing bookings for the date
        bookings = self.get_bookings(date)
        if bookings is None:
            return False, "couldn't get bookings"
            
        self.log(f"{len(bookings)} bookings found")
        
        # Try each space in order
        for i, (space_id, space_name) in enumerate(self.spaces.items()):
            self.log(f"trying {space_name} ({i+1}/{len(self.spaces)})")
            
            if self.space_is_free(space_id, start_dt, end_dt, bookings):
                self.log(f"booking {space_name}...")
                result = self.book_space(space_id, start_dt, end_dt)
                if result:
                    self.log(f"booked {space_name}")
                    return result, f"booked {space_name}"
                else:
                    self.log(f"failed")
            else:
                self.log(f"occupied")
        
        self.log("no spaces available")
        return False, f"all {len(self.spaces)} spaces taken"

def setup():
    # Create a template config file for local use
    config = {
        "SKEDDA_BASE_URL": "https://your-instance.skedda.com",
        "SKEDDA_VENUE_ID": "your_venue_id_here",
        "SKEDDA_USER_ID": "your_user_id_here",
        "SKEDDA_COOKIES": "your_cookies_here",
        "SKEDDA_TOKEN": "your_token_here",
        "SKEDDA_SPACES": json.dumps({
            "space_id_1": "Space 1",
            "space_id_2": "Space 2",
            "space_id_3": "Space 3"
        }, indent=2),
        "note": "get from browser devtools"
    }
    
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2)
    print("config.json created")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--setup':
        setup()
        return
    
    # How many days ahead to book (0 = today, 14 = two weeks ahead)
    days_ahead = int(os.getenv('DAYS_AHEAD', '14'))
    
    # Timezone for date calculations (handles daylight saving automatically)
    timezone = os.getenv('TIMEZONE', 'Australia/Melbourne')
    
    # Calculate target date
    try:
        import pytz
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        target = now + timedelta(days=days_ahead)
        date_str = target.strftime("%Y-%m-%d")
        print(f"booking for {target.strftime('%a %d %b')}")
    except ImportError:
        # Fallback without timezone support (DST not handled)
        target = datetime.utcnow() + timedelta(days=days_ahead)
        date_str = target.strftime("%Y-%m-%d")
        print(f"booking for {date_str}")
    
    # Run the booking process
    booker = SkeddaBooker()
    result, details = booker.run(date_str)
    
    date_formatted = target.strftime('%d %B %Y')
    
    # Output results for GitHub Actions
    github_output = os.getenv('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as f:
            f.write(f"date={date_formatted}\n")
            
            if result:
                space_name = booker.spaces.get(result, f"Space {result}")
                f.write(f"message={space_name}\n")
                f.write(f"result=SUCCESS\n")
                f.write(f"details=Booked {space_name} for 8:30 AM - 5:00 PM\n")
            else:
                f.write(f"message=No Space\n")
                f.write(f"result=FAILED\n")
                f.write(f"details={details}\n")
    
    if result:
        print("SUCCESS")
    else:
        print("FAILED")

if __name__ == "__main__":
    main()
