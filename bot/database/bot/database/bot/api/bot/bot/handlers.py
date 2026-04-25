from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import asyncio
from datetime import datetime
from bot.database import SessionLocal
from bot.database.models import User, Generation
from bot.api.muapi_client import muapi
from bot.utils.helpers import split_long_message, format_credits
from bot.utils.decorators import require_auth, rate_limit, log_command
import os

ADMIN_ID = int(os.getenv("ADMIN_ID", "8478884644"))

# Вспомогательные функции
async def get_or_create_user(telegram_id, username, first_name, last_name):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_admin=(telegram_id == ADMIN_ID),
            credits=100
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.last_active = datetime.utcnow()
        db.commit()
    db.close()
    return user

async def notify_admin(context: ContextTypes.DEFAULT_TYPE, message: str):
    await context.bot.send_message(chat_id=ADMIN_ID, text=message)

# Команды
@log_command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = await get_or_create_user(user.id, user.username, user.first_name, user.last_name)
    
    welcome = f"""
✨ *Добро пожаловать в MiMi AI Studio* ✨

Привет, {user.first_name}! Я твой персональный AI-ассистент для создания контента нового поколения.

🎨 *Доступные возможности:*
• Генерация изображений (200+ моделей)
• Создание видео (текст → видео, картинка → видео)
• Lip sync — анимация портретов с аудио
• Кинематографический режим с настройкой камеры
• Workflow — конвейеры из нескольких шагов

💰 *Ваш баланс:* {db_user.credits} кредитов
🎁 *Бесплатно:* Первые 100 кредитов при регистрации

📌 *Начните прямо сейчас:*
/imagine — создайте изображение
/video — создайте видео
/help — все команды

*MiMi AI — где рождается творчество без границ* 🚀
    """
    await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)
    
    # Уведомление админу
    await notify_admin(context, f"🆕 Новый пользователь: {user.first_name} (@{user.username})\nID: {user.id}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📖 *Справочник команд MiMi AI*

*🎨 Генерация*
/imagine [текст] — создать изображение
/video [текст] — создать видео
/lipsync — синхронизация губ (фото + аудио)
/cinema — генерация с кинематографическими настройками

*🛠️ Инструменты*
/workflow — запустить конвейер
/models — список доступных моделей
/history — просмотр истории
/stats — моя статистика

*ℹ️ Прочее*
/start — приветствие
/help — помощь
/cancel — отменить текущую операцию

*Примеры:*
/imagine cyberpunk cat, neon lights, 8k
/video космический корабль летит через туманность
/lipsync — затем отправьте фото и аудио

❓ Вопросы: @MiMiSupport
    """
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

@rate_limit(limit=10, per=60)
async def imagine_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_or_create_user(update.effective_user.id, None, None, None)
    
    # Проверка кредитов
    if user.credits < 1:
        await update.message.reply_text("❌ Недостаточно кредитов. Пополните баланс у администратора.")
        return
    
    # Если промпт передан сразу
    if context.args:
        prompt = ' '.join(context.args)
        await generate_and_send_image(update, context, prompt, user)
    else:
        # Запрашиваем промпт
        await update.message.reply_text("✍️ *Напишите ваш промпт для генерации изображения:*\n\nПример: `киберпанк город, ночь, дождь, неон`", parse_mode=ParseMode.MARKDOWN)
        context.user_data['awaiting_prompt'] = 'image'
        return

async def generate_and_send_image(update, context, prompt, user):
    msg = await update.message.reply_text(f"🎨 *Генерация изображения...*\n⏳ Обычно 10-30 секунд\n\n📝 *Промпт:* `{prompt[:100]}...`", parse_mode=ParseMode.MARKDOWN)
    
    try:
        # Показываем выбор модели (через инлайн кнопки)
        keyboard = [
            [
                InlineKeyboardButton("🚀 Flux Dev", callback_data="model_flux"),
                InlineKeyboardButton("🎨 Midjourney v7", callback_data="model_mj"),
            ],
            [
                InlineKeyboardButton("✨ Nano Banana 2", callback_data="model_nano"),
                InlineKeyboardButton("🎭 Seedream 5.0", callback_data="model_seedream"),
            ],
            [
                InlineKeyboardButton("⚡ Быстрая генерация", callback_data="model_fast"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await msg.edit_text("🎨 *Выберите модель:*", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        
        # Сохраняем промпт в контекст
        context.user_data['pending_prompt'] = prompt
        context.user_data['pending_type'] = 'image'
        context.user_data['pending_message_id'] = msg.message_id
        
    except Exception as e:
        await msg.edit_text(f"❌ *Ошибка:* {str(e)}", parse_mode=ParseMode.MARKDOWN)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = await get_or_create_user(update.effective_user.id, None, None, None)
    
    if data.startswith("model_"):
        model_map = {
            "flux": "flux-dev",
            "mj": "midjourney-v7",
            "nano": "nano-banana-2",
            "seedream": "seedream-5.0",
            "fast": "flux-dev"  # можно заменить на более быструю
        }
        model_key = data.replace("model_", "")
        model = model_map.get(model_key, "flux-dev")
        
        prompt = context.user_data.get('pending_prompt')
        gen_type = context.user_data.get('pending_type')
        msg_id = context.user_data.get('pending_message_id')
        
        if not prompt:
            await query.edit_message_text("❌ Промпт не найден. Начните заново с /imagine")
            return
        
        # Списываем кредит
        db = SessionLocal()
        db_user = db.query(User).filter_by(telegram_id=user.telegram_id).first()
        if db_user.credits < 1:
            await query.edit_message_text("❌ Недостаточно кредитов.")
            db.close()
            return
        
        db_user.credits -= 1
        db.commit()
        
        # Создаем запись генерации
        generation = Generation(
            user_id=db_user.id,
            type=gen_type,
            model=model,
            prompt=prompt,
            status="processing"
        )
        db.add(generation)
        db.commit()
        gen_id = generation.id
        db.close()
        
        await query.edit_message_text(f"🎨 *Генерация с моделью {model}...*\n⏳ Пожалуйста, подождите.", parse_mode=ParseMode.MARKDOWN)
        
        try:
            if gen_type == 'image':
                result_url = await muapi.generate_image(prompt, model=model)
            elif gen_type == 'video':
                result_url = await muapi.generate_video(prompt, model=model)
            else:
                raise Exception("Unknown type")
            
            # Обновляем запись
            db = SessionLocal()
            gen = db.query(Generation).filter_by(id=gen_id).first()
            gen.status = "completed"
            gen.output_url = result_url
            gen.completed_at = datetime.utcnow()
            db.commit()
            db.close()
            
            # Отправляем результат
            if gen_type == 'image':
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=result_url,
                    caption=f"✅ *Готово!*\nМодель: {model}\nПромпт: {prompt[:150]}...\n💎 -1 кредит"
                )
            else:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=result_url,
                    caption=f"✅ *Готово!*\nМодель: {model}"
                )
            
            # Удаляем сообщение с выбором модели
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
            
        except Exception as e:
            # Возвращаем кредит при ошибке
            db = SessionLocal()
            db_user = db.query(User).filter_by(telegram_id=user.telegram_id).first()
            db_user.credits += 1
            gen = db.query(Generation).filter_by(id=gen_id).first()
            gen.status = "failed"
            gen.error_message = str(e)
            db.commit()
            db.close()
            
            await query.edit_message_text(f"❌ *Ошибка:* {str(e)}", parse_mode=ParseMode.MARKDOWN)

# Остальные обработчики (видео, lipsync, история и т.д.)
async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Аналогично imagine, но с проверкой кредитов (видео стоит 4-5)
    user = await get_or_create_user(update.effective_user.id, None, None, None)
    if user.credits < 4:
        await update.message.reply_text("❌ Недостаточно кредитов для видео (нужно 4 кредита).")
        return
    
    if context.args:
        prompt = ' '.join(context.args)
        context.user_data['pending_prompt'] = prompt
        context.user_data['pending_type'] = 'video'
        # Показать выбор модели и т.д.
        await update.message.reply_text("🎬 *Выберите модель видео:*\n(через кнопки)", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("✍️ *Напишите промпт для видео:*")
        context.user_data['awaiting_prompt'] = 'video'

async def lipsync_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎙️ *Для Lip Sync:*\n"
        "1. Отправьте портретное фото\n"
        "2. Затем отправьте аудиофайл или голосовое сообщение\n"
        "Бот анимирует фото под вашу аудиодорожку.\n\n"
        "Отправьте фото прямо сейчас 👇"
    )
    context.user_data['lipsync_step'] = 'waiting_photo'

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('lipsync_step') == 'waiting_photo':
        photo_file = await update.message.photo[-1].get_file()
        file_bytes = await photo_file.download_as_bytearray()
        # Загружаем фото на сервер
        img_url = await muapi.upload_file(bytes(file_bytes), "photo.jpg")
        context.user_data['lipsync_img_url'] = img_url
        await update.message.reply_text("✅ Фото получено! Теперь отправьте аудио (MP3 или голосовое)")
        context.user_data['lipsync_step'] = 'waiting_audio'
    else:
        # Обработка для multi-image режима
        pass

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('lipsync_step') == 'waiting_audio':
        audio = update.message.audio or update.message.voice
        if audio:
            file = await audio.get_file()
            audio_bytes = await file.download_as_bytearray()
            audio_url = await muapi.upload_file(bytes(audio_bytes), "audio.mp3")
            
            img_url = context.user_data.get('lipsync_img_url')
            await update.message.reply_text("🎬 Анимирую портрет... Ждите (до 1 минуты)")
            
            try:
                result_video = await muapi.lipsync(img_url, audio_url)
                await update.message.reply_video(video=result_video, caption="✅ Lip Sync готов!")
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка: {e}")
            
            context.user_data['lipsync_step'] = None

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()
    if not user:
        await update.message.reply_text("❌ Пользователь не найден.")
        db.close()
        return
    
    generations = db.query(Generation).filter_by(user_id=user.id).order_by(Generation.created_at.desc()).limit(10).all()
    if not generations:
        await update.message.reply_text("📭 У вас пока нет генераций.")
        db.close()
        return
    
    text = "📜 *Последние 10 генераций:*\n\n"
    for gen in generations:
        text += f"• {gen.type.upper()} | {gen.model}\n  {gen.created_at.strftime('%d.%m.%Y %H:%M')}\n  Статус: {gen.status}\n\n"
    
    await update.message.reply_text(text[:4000], parse_mode=ParseMode.MARKDOWN)
    db.close()

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()
    if not user:
        await update.message.reply_text("❌ Ошибка")
        db.close()
        return
    
    stats = f"""
📊 *Ваша статистика:*

💎 Кредитов: {user.credits}
🎨 Всего генераций: {user.total_generations}
📅 Дата регистрации: {user.joined_at.strftime('%d.%m.%Y')}
🕐 Последняя активность: {user.last_active.strftime('%d.%m.%Y %H:%M')}

💰 *Пополнить баланс:* /buy
    """
    await update.message.reply_text(stats, parse_mode=ParseMode.MARKDOWN)
    db.close()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Операция отменена.")
    context.user_data.clear()
