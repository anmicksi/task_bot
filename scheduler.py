from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot
from db import get_session
from models import Task
from datetime import datetime, timedelta
import os

bot = Bot(token=os.getenv(f"TELEGRAM_TOKEN"))
scheduler = BackgroundScheduler()

def notify_user(task: Task):
    try:
        user_id = task.user_id
        text = f"🔔 Reminder: '{task.title}' is due at {task.deadline.strftime('%Y-%m-%d %H:%M')}!"
        bot.send_message(chat_id=user_id, text=text)
    except Exception as e:
        print("Error sending notification:", e)

def schedule_task_notifications(task: Task):
    run_time = task.deadline - timedelta(minutes=10)
    if run_time > datetime.now():
        scheduler.add_job(notify_user, 'date', run_date=run_time, args=[task])

def start_scheduler():
    scheduler.start()
