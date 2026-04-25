import time
from functools import wraps
from telegram import Update
from bot.database import SessionLocal
from bot.database.models import User

def rate_limit(limit: int, per: float):
    """Ограничение частоты запросов (limit запросов за per секунд)"""
    def decorator(func):
        # Словарь для хранения времени последних запросов
        last_called = {}
        
        @wraps(func)
        async def wrapper(update: Update, context, *args, **kwargs):
            user_id = update.effective_user.id
            now = time.time()
            
            if user_id in last_called:
                elapsed = now - last_called[user_id]
                if elapsed < per / limit:
                    await update.message.reply_text(f"⏳ Слишком часто! Подождите {int(per/limit - elapsed)} секунд.")
                    return
            
            last_called[user_id] = now
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

def require_auth(func):
    """Проверка, что пользователь есть в БД"""
    @wraps(func)
    async def wrapper(update: Update, context, *args, **kwargs):
        user_id = update.effective_user.id
        db = SessionLocal()
        user = db.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            # Создаем автоматически
            user = User(telegram_id=user_id)
            db.add(user)
            db.commit()
        db.close()
        return await func(update, context, *args, **kwargs)
    return wrapper

def log_command(func):
    """Логирование команд в консоль"""
    @wraps(func)
    async def wrapper(update: Update, context, *args, **kwargs):
        user = update.effective_user
        command = update.message.text.split()[0] if update.message else "unknown"
        print(f"[LOG] {user.first_name} (@{user.username}) -> {command}")
        return await func(update, context, *args, **kwargs)
    return wrapper
