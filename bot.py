import os
import pytz
import asyncio
from datetime import datetime, timedelta
# Changed to AsyncIOScheduler for async/await support
from apscheduler.schedulers.asyncio import AsyncIOScheduler 
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = "8982157709:AAESIhjiMcieVt5kcwIenjUbZDURdVq-Nuk"
CHANNEL_ID = "@cricketbotganeu"
TIMEZONE = pytz.timezone("Asia/Kolkata")

# Initialize the Async Scheduler
scheduler = AsyncIOScheduler(timezone=TIMEZONE)
scheduler.start()

last_poster_path = None

async def send_team_post(application, image_path, team_name):
    """Triggered by the scheduler to send the photo to the channel."""
    with open(image_path, "rb") as photo:
        await application.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=photo,
            caption=team_name
        )

def create_job(application, image_path, team_name, run_time):
    """Adds an async job to the scheduler."""
    scheduler.add_job(
        send_team_post,
        "date",
        run_date=run_time,
        args=[application, image_path, team_name] # Pass arguments safely here
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send poster first, then send:\n\nTeam 1\nTeam 2\n07:00 AM"
    )

async def save_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_poster_path
    os.makedirs("posters", exist_ok=True)
    
    photo = update.message.photo[-1]
    telegram_file = await photo.get_file()
    filename = f"poster_{update.message.message_id}.jpg"
    filepath = os.path.join("posters", filename)
    
    await telegram_file.download_to_drive(filepath)
    last_poster_path = filepath
    
    await update.message.reply_text(
        "✅ Poster saved.\n\nNow send:\n\nTeam 1\nTeam 2\n07:00 AM"
    )

async def save_match_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_poster_path
    if not last_poster_path:
        await update.message.reply_text("❌ Send a poster first.")
        return

    lines = update.message.text.strip().splitlines()
    if len(lines) < 3:
        await update.message.reply_text(
            "❌ Format:\n\nTeam 1\nTeam 2\n07:00 AM"
        )
        return

    team1 = lines[0].strip()
    team2 = lines[1].strip()
    match_time = lines[2].strip()

    try:
        # 1. Get current time in Kolkata
        now = datetime.now(TIMEZONE)
        
        # 2. Parse the string into a NAIVE datetime object first
        parsed_time = datetime.strptime(match_time, "%I:%M %p")
        
        # 3. Combine today's date with the parsed time (Naive)
        naive_dt = datetime(
            now.year,
            now.month,
            now.day,
            parsed_time.hour,
            parsed_time.minute
        )
        
        # 4. Localize it to Kolkata timezone properly
        match_dt = TIMEZONE.localize(naive_dt)

        # If the time has already passed today, assume it's for tomorrow
        if match_dt < now:
            match_dt += timedelta(days=1)

    except ValueError:
        await update.message.reply_text("❌ Invalid time format. Use exactly '07:00 AM' or '11:30 PM'")
        return

    # Calculate post times
    post1_time = match_dt - timedelta(hours=1)
    post2_time = post1_time + timedelta(minutes=1)

    # Schedule the jobs using context.application
    create_job(
        context.application,
        last_poster_path,
        team1,
        post1_time
    )

    create_job(
        context.application,
        last_poster_path,
        team2,
        post2_time
    )

    await update.message.reply_text(
        f"✅ Scheduled\n\n"
        f"{team1} -> {post1_time.strftime('%d-%m-%Y %I:%M %p')}\n"
        f"{team2} -> {post2_time.strftime('%d-%m-%Y %I:%M %p')}"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, save_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_match_details))
    
    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()