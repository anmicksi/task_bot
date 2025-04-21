import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes
)
from db import create_db_and_tables, get_session
from models import User, Task
from utils import encrypt_password, check_password, format_task_list
from scheduler import start_scheduler, schedule_task_notifications

MAIN_MENU = 99
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

REGISTER, LOGIN, PASSWORD_REGISTER, PASSWORD_LOGIN, NEW_TASK, TASK_TITLE, TASK_DESC, TASK_DEADLINE, EDIT_TASK, DELETE_TASK, SET_PRIORITY = range(11)

users_logged_in = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Регистрация", callback_data='register')],
        [InlineKeyboardButton("Вход", callback_data='login')]
    ]
    await update.message.reply_text("Привет, я TaskBot!", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'register':
        await query.edit_message_text("Введите юзернейм:")
        return REGISTER
    elif query.data == 'login':
        await query.edit_message_text("Введите юзернейм:")
        return LOGIN

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['username'] = update.message.text
    await update.message.reply_text("Введите пароль:")
    return PASSWORD_REGISTER

async def password_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = get_session()
    username = context.user_data.get('username')

    if session.query(User).filter_by(username=username).first():
        await update.message.reply_text("Такой юзернейм уже занят! Введите другой:")
        return REGISTER

    password = encrypt_password(update.message.text)
    user = User(username=username, password=password)
    session.add(user)
    session.commit()

    users_logged_in[update.effective_user.id] = user.id
    await update.message.reply_text("Успешная регистрация!")
    return await show_main_menu(update, context)


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['username'] = update.message.text
    await update.message.reply_text("Введите пароль:")
    return PASSWORD_LOGIN

logging.basicConfig(level=logging.DEBUG)

async def password_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.debug("Password login started")
    session = get_session()
    username = context.user_data.get('username')
    user = session.query(User).filter_by(username=username).first()

    if not user:
        logging.debug(f"User {username} not found")
        await update.message.reply_text("Пользователь не найден.")
        return LOGIN

    if check_password(update.message.text, user.password):
        logging.debug(f"User {username} successfully logged in")
        users_logged_in[update.effective_user.id] = user.id
        await update.message.reply_text("Успешный вход!")
        return await show_main_menu(update, context)
    else:
        logging.debug(f"Incorrect password for user {username}")
        await update.message.reply_text("Неверный пароль. Попробуйте ещё раз:")
        return PASSWORD_LOGIN

async def new_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название задачи:")
    return TASK_TITLE

async def task_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['title'] = update.message.text
    await update.message.reply_text("Введите описание задачи:")
    return TASK_DESC

async def task_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("Введите дедлайн в формате: (YYYY-MM-DD HH:MM):")
    return TASK_DEADLINE

async def task_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import datetime
    try:
        deadline = datetime.strptime(update.message.text, "%Y-%m-%d %H:%M")
    except ValueError:
        await update.message.reply_text("Неправильный формат! Попробуйте снова.")
        return TASK_DEADLINE

    user_id = users_logged_in.get(update.effective_user.id)
    session = get_session()
    task = Task(title=context.user_data['title'], description=context.user_data['description'],
                deadline=deadline, user_id=user_id)
    session.add(task)
    session.commit()
    schedule_task_notifications(task)
    await update.message.reply_text("Задача создана!")
    return ConversationHandler.END

async def view_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = users_logged_in.get(update.effective_user.id)
    session = get_session()
    tasks = session.query(Task).filter_by(user_id=user_id).all()
    await update.message.reply_text(format_task_list(tasks))

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Создать задачу", callback_data='new_task')],
        [InlineKeyboardButton("Посмотреть задачи", callback_data='view_tasks')]
    ]

    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "Выберите действие:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif update.message:
            await update.message.reply_text(
                "Выберите действие:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            print("⚠️ Ни message, ни callback_query не найдены в update!")
    except Exception as e:
        print(f"Ошибка в show_main_menu: {e}")

    return MAIN_MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'new_task':
        await query.edit_message_text("Enter task title:")
        return TASK_TITLE
    elif query.data == 'view_tasks':
        await view_tasks(update, context)
        await query.edit_message_text("Выберите следующее действие:")
        return await show_main_menu(update, context)

async def handle_main_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пожалуйста, выберите действие, используя кнопки ниже ⬇️")
    return MAIN_MENU

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users_logged_in.pop(update.effective_user.id, None)
    context.user_data.clear()
    await start(update, context)
    return MAIN_MENU

def main():
    create_db_and_tables()
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(button_handler, pattern='^(register|login)$')],
        states={
            REGISTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, register)],
            LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, login)],
            PASSWORD_REGISTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_register)],
            PASSWORD_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_login)],
            TASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_title)],
            TASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_desc)],
            TASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_deadline)],
            MAIN_MENU: [
                CallbackQueryHandler(menu_handler, pattern='^(new_task|view_tasks)$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu_text)
            ],
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('restart', restart))
    app.add_handler(CommandHandler('newtask', new_task))
    app.add_handler(CommandHandler('tasks', view_tasks))

    start_scheduler()

    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    app.run_polling()

if __name__ == '__main__':
    main()
