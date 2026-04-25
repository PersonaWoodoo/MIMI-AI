#!/usr/bin/env python3
# bot/main.py

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в путь, чтобы импорты работали
sys.path.append(str(Path(__file__).parent.parent))

from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ConversationHandler
)
from telegram import BotCommand
from dotenv import load_dotenv
import os

# Импорты из нашего проекта (структура: bot/...)
from bot.database import init_db
from bot.database.models import User
from bot.handlers import (
    start, help_command, imagine_command, video_command,
    lipsync_command, cinema_command, workflow_command,
    models_command, history_command, stats_command,
    button_callback, handle_photo, handle_audio,
    cancel, handle_prompt, handle_multi_photo
)
from bot.utils.logger import setup_logger

load_dotenv()

# === Конфигурация ===
TOKEN = os.getenv("8218613181:AAFlArlfWy_cqMotETD2mEDoc5gPi_a2lOI")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8478884644"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # оставьте пустым для polling

# Состояния для ConversationHandler
(
    WAITING_PROMPT,
    WAITING_IMAGE,
    WAITING_AUDIO,
    WAITING_MODEL_SELECTION,
    WAITING_MULTI_IMAGES
) = range(5)

# === Инициализация ===
setup_logger()
init_db()

async def post_init(application: Application):
    """Установка команд меню"""
    commands = [
        BotCommand("start", "🚀 Запустить бота"),
        BotCommand("imagine", "🎨 Создать изображение"),
        BotCommand("video", "🎬 Создать видео"),
        BotCommand("lipsync", "🎙️ Анимировать портрет с аудио"),
        BotCommand("cinema", "🎥 Кинематографическая генерация"),
        BotCommand("workflow", "🔧 Запустить конвейер"),
        BotCommand("models", "📋 Список доступных моделей"),
        BotCommand("history", "📜 История генераций"),
        BotCommand("stats", "📊 Моя статистика"),
        BotCommand("help", "❓ Помощь"),
    ]
    await application.bot.set_my_commands(commands)
    print("✅ MiMi AI Bot запущен (polling режим)")

def main():
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN не задан в .env файле")

    app = Application.builder().token(TOKEN).post_init(post_init).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("imagine", imagine_command))
    app.add_handler(CommandHandler("video", video_command))
    app.add_handler(CommandHandler("lipsync", lipsync_command))
    app.add_handler(CommandHandler("cinema", cinema_command))
    app.add_handler(CommandHandler("workflow", workflow_command))
    app.add_handler(CommandHandler("models", models_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("stats", stats_command))

    # ConversationHandler для многошаговых процессов
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("imagine", imagine_command),
            CommandHandler("video", video_command),
            CommandHandler("lipsync", lipsync_command),
        ],
        states={
            WAITING_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_prompt)],
            WAITING_IMAGE: [MessageHandler(filters.PHOTO, handle_photo)],
            WAITING_AUDIO: [MessageHandler(filters.AUDIO | filters.VOICE, handle_audio)],
            WAITING_MODEL_SELECTION: [CallbackQueryHandler(button_callback)],
            WAITING_MULTI_IMAGES: [MessageHandler(filters.PHOTO, handle_multi_photo)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)

    # Обработчики callback-кнопок
    app.add_handler(CallbackQueryHandler(button_callback))

    # Запуск
    if WEBHOOK_URL:
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv("PORT", 8443)),
            webhook_url=WEBHOOK_URL
        )
    else:
        app.run_polling()

if __name__ == "__main__":
    main()
