from passlib.hash import bcrypt
from models import Task

def encrypt_password(password: str) -> str:
    return bcrypt.hash(password)

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.verify(password, hashed)

def format_task_list(tasks: list[Task]) -> str:
    if not tasks:
        return "Задач не найдено."
    return '\\n'.join([
        f"📝 {task.title} | {'✅' if task.completed else '❌'} | Priority: {task.priority} | Deadline: {task.deadline.strftime('%Y-%m-%d %H:%M')}"
        for task in tasks
    ])