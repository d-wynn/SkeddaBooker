# Skedda Booking Automation

Automate your Skedda bookings with GitHub Actions. Works for parking spaces, desks, meeting rooms, or any bookable space on Skedda.

## What it does

This script logs into Skedda and tries to book a space for you automatically. It goes through your list of preferred spaces in order and books the first available one.

Perfect for when spaces get booked out quickly and you want to secure one without having to remember to do it manually.

## Requirements

- A Skedda account with SSO authentication
- A GitHub account (free)
- 5 minutes to set it up

## Quick start

### 1. Add the script to your repo

Copy `skedda.py` to your GitHub repository.

### 2. Get your credentials

Open Chrome and log into Skedda, then:

1. Press F12 to open DevTools
2. Go to the Network tab
3. Make a test booking on Skedda
4. Find the request to `/bookings` (it'll be a POST request)
5. Right-click it and select "Copy as cURL"
6. You'll need to extract values from this curl command

From the curl command, grab:
- The `x-skedda-requestverificationtoken` header value (this is your token)
- Everything after `-b` or `Cookie:` (these are your cookies)

You'll also need:
- Your venue ID (in the URL or curl data)
- Your user ID (in the curl data as `venueuser`)
- Your space IDs (in the curl data as `spaces`)

### 3. Set up GitHub secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret

Add these 6 secrets:

**SKEDDA_BASE_URL**
```
https://your-instance.skedda.com
```

**SKEDDA_VENUE_ID**
```
your_venue_id_here
```

**SKEDDA_USER_ID**
```
your_user_id_here
```

**SKEDDA_COOKIES**
```
(paste the entire cookie string from your curl command)
```

**SKEDDA_TOKEN**
```
(paste the x-skedda-requestverificationtoken value)
```

**SKEDDA_SPACES**
```json
{"space_id_1": "Space 1", "space_id_2": "Space 2", "space_id_3": "Space 3"}
```
(adjust with your space IDs and names)

### 4. Create the workflow

Create `.github/workflows/book-skedda.yml` in your repo:

```yaml
name: Book Skedda Space

on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight UTC
  workflow_dispatch:

jobs:
  book:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install requests pytz
      
      - name: Run booking
        env:
          SKEDDA_BASE_URL: ${{ secrets.SKEDDA_BASE_URL }}
          SKEDDA_VENUE_ID: ${{ secrets.SKEDDA_VENUE_ID }}
          SKEDDA_USER_ID: ${{ secrets.SKEDDA_USER_ID }}
          SKEDDA_COOKIES: ${{ secrets.SKEDDA_COOKIES }}
          SKEDDA_TOKEN: ${{ secrets.SKEDDA_TOKEN }}
          SKEDDA_SPACES: ${{ secrets.SKEDDA_SPACES }}
        run: python skedda.py
```

### 5. Test it

Go to Actions tab → Book Skedda Space → Run workflow

Check the logs to see if it worked.

## Optional settings

You can add these secrets to customise the booking:

**DAYS_AHEAD** (default: 14)
```
14
```
How many days ahead to book. Use `0` for today, `14` for two weeks ahead.

**TIMEZONE** (default: Australia/Melbourne)
```
Australia/Melbourne
```
Your timezone. The script handles daylight saving automatically.

## How it works

The script runs at your scheduled time and:
1. Calculates the target date (14 days ahead by default)
2. Gets all existing bookings for that date
3. Goes through your space list in order
4. Books the first available space it finds
5. Stops once it successfully books something

## Troubleshooting

**"missing venue_id or user_id"**
- Check your GitHub secrets are set correctly
- Make sure the workflow file includes all the env vars

**"auth expired"**
- Your cookies or token have expired
- Get fresh ones from DevTools and update the secrets

**"all spaces taken"**
- All your preferred spaces are already booked
- Try adding more spaces to your list
- Or run the script earlier

**"missing spaces config"**
- Check your SKEDDA_SPACES secret is valid JSON
- Format: `{"space_id": "Space Name"}`

## Running locally

If you want to test locally:

```bash
python skedda.py --setup
```

This creates a `config.json` file. Edit it with your details, then:

```bash
python skedda.py
```

Don't commit `config.json` to git (add it to `.gitignore`).

## Notes

- Cookies and tokens expire, usually after a few days
- You'll need to refresh them when they do
- The script only works with SSO-enabled Skedda instances
- Your space list order matters - first available wins

## Credits

Built for automating Skedda bookings when manual booking gets tedious.