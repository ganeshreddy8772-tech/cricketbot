import os
import re
import easyocr
import pytz

from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

from telegram import Update
from telegram.ext import (
Application,
CommandHandler,
MessageHandler,
ContextTypes,
filters
)

# ======================================

# SETTINGS

# ======================================

TOKEN = "8982157709:AAESIhjiMcieVt5kcwIenjUbZDURdVq-Nuk"

CHANNEL_ID = "@cricketbotganeu"

TIMEZONE = pytz.timezone("Asia/Kolkata")

# ======================================

# OCR

# ======================================

reader = easyocr.Reader(['en'])

scheduler = BackgroundScheduler(timezone=TIMEZONE)
scheduler.start()

waiting_for_schedule = False

# ======================================

# HELPERS

# ======================================

def extract_match_info(text):

```
lines = []

for line in text.split("\n"):
    line = line.strip()

    if line:
        lines.append(line)

time_match = re.search(
    r'(\d{1,2}:\d{2}\s*[AP]M)',
    text,
    re.IGNORECASE
)

match_time = None

if time_match:
    match_time = time_match.group(1)

teams = []

for line in lines:

    lower = line.lower()

    if "starts at" in lower:
        continue

    if re.search(r'\d{1,2}:\d{2}', line):
        continue

    if any(
        x in lower
        for x in [
            "t20",
            "odi",
            "test",
            "cup",
            "league",
            "series",
            "match"
        ]
    ):
        continue

    teams.append(line)

if len(teams) >= 2:

    team1 = teams[0]
    team2 = teams[-1]

    return team1, team2, match_time

return None, None, None
```

async def send_team_post(
application,
image_path,
team_name
):

```
with open(image_path, "rb") as photo:

    await application.bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=photo,
        caption=team_name
    )
```

def create_job(
application,
image_path,
team_name,
run_time
):

```
scheduler.add_job(
    lambda: application.create_task(
        send_team_post(
            application,
            image_path,
            team_name
        )
    ),
    "date",
    run_date=run_time
)
```

# ======================================

# COMMANDS

# ======================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

```
await update.message.reply_text(
    "Bot is working."
)
```

async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):

```
global waiting_for_schedule

waiting_for_schedule = True

await update.message.reply_text(
    "Send today's schedule."
)
```

async def save_schedule(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

```
global waiting_for_schedule

if waiting_for_schedule:

    with open(
        "schedule.txt",
        "w",
        encoding="utf-8"
    ) as f:

        f.write(update.message.text)

    waiting_for_schedule = False

    await update.message.reply_text(
        "✅ Schedule saved."
    )
```

# ======================================

# PHOTO HANDLER

# ======================================

async def save_photo(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

```
os.makedirs("posters", exist_ok=True)

photo = update.message.photo[-1]

telegram_file = await photo.get_file()

filename = f"poster_{update.message.message_id}.jpg"

filepath = os.path.join(
    "posters",
    filename
)

await telegram_file.download_to_drive(
    filepath
)

result = reader.readtext(
    filepath,
    detail=0
)

detected_text = "\n".join(result)

await update.message.reply_text(
    f"✅ Poster saved: {filename}"
)

team1, team2, match_time = extract_match_info(
    detected_text
)

if not all([team1, team2, match_time]):

    await update.message.reply_text(
        f"❌ Could not detect teams/time.\n\n{detected_text}"
    )

    return

await update.message.reply_text(
    f"📖 OCR Result\n\n"
    f"Team 1: {team1}\n"
    f"Team 2: {team2}\n"
    f"Match Time: {match_time}"
)

now = datetime.now(TIMEZONE)

match_dt = datetime.strptime(
    match_time,
    "%I:%M %p"
)

match_dt = TIMEZONE.localize(
    datetime(
        now.year,
        now.month,
        now.day,
        match_dt.hour,
        match_dt.minute
    )
)

if match_dt < now:
    match_dt += timedelta(days=1)

post1_time = match_dt - timedelta(hours=1)
post2_time = post1_time + timedelta(minutes=1)

create_job(
    context.application,
    filepath,
    team1,
    post1_time
)

create_job(
    context.application,
    filepath,
    team2,
    post2_time
)

await update.message.reply_text(
    f"✅ Scheduled\n\n"
    f"{team1} -> {post1_time.strftime('%d-%m-%Y %I:%M %p')}\n"
    f"{team2} -> {post2_time.strftime('%d-%m-%Y %I:%M %p')}"
)
```

# ======================================

# APP

# ======================================

app = Application.builder().token(TOKEN).build()

app.add_handler(
CommandHandler(
"start",
start
)
)

app.add_handler(
CommandHandler(
"schedule",
schedule
)
)

app.add_handler(
MessageHandler(
filters.TEXT & ~filters.COMMAND,
save_schedule
)
)

app.add_handler(
MessageHandler(
filters.PHOTO,
save_photo
)
)

print("Bot started...")
app.run_polling()
