import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы состояний разговора
CONVERT_FILE, EXTRACT_AUDIO, REMOVE_AUDIO = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Конвертировать файл", callback_data=str(CONVERT_FILE))],
        [InlineKeyboardButton("Извлечь музыку из видео", callback_data=str(EXTRACT_AUDIO))],
        [InlineKeyboardButton("Удалить музыку из видео", callback_data=str(REMOVE_AUDIO))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        text="Привет! В этом боте ты можешь конвертировать любой файл в другой формат, "
            "извлечь музыку из видео или убрать музыку из видео!\n\nВоспользуйтесь кнопками ниже.",
        reply_markup=reply_markup
    )

async def convert_file_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса конвертации файла."""
    query = update.callback_query
    await query.answer()
    formats = ["mp3", "wav", "ogg", "flac", "mkv", "avi", "mp4"]
    buttons = [[InlineKeyboardButton(fmt, callback_data=f'source_{fmt}') for fmt in formats]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(text="Выберите исходный формат файла:", reply_markup=reply_markup)
    return CONVERT_FILE

async def select_target_format(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выбор целевого формата файла."""
    query = update.callback_query
    source_format = query.data.split('_')[1]
    context.user_data['source_format'] = source_format
    await query.answer()
    formats = ["mp3", "wav", "ogg", "flac", "mkv", "avi", "mp4"]  # Форматы кроме выбранного ранее
    buttons = [[InlineKeyboardButton(fmt, callback_data=f'target_{fmt}') for fmt in formats if fmt != source_format]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(text="Теперь выберите целевой формат файла:", reply_markup=reply_markup)
    return CONVERT_FILE

async def wait_for_file_to_convert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение файла для конвертации."""
    target_format = context.user_data['target_format']
    await update.callback_query.answer()
    await update.effective_chat.send_message("Отправьте файл для конвертации.")
    return CONVERT_FILE

async def handle_file_conversion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка файла и выполнение конвертации."""
    file_id = update.message.document.file_id
    file_name = update.message.document.file_name
    user_data = context.user_data
    
    # Получаем файл
    new_file = await context.bot.get_file(file_id)
    await new_file.download_to_drive(custom_path=file_name)
    
    # Выполняем конвертацию
    converted_file_name = f"{os.path.splitext(file_name)[0]}.{user_data['target_format']}"
    os.system(f"ffmpeg -i '{file_name}' '{converted_file_name}'")
    
    # Загружаем обратно в чат
    with open(converted_file_name, 'rb') as f:
        await update.effective_chat.send_document(document=f)
    
    # Очищаем временные файлы
    os.remove(file_name)
    os.remove(converted_file_name)
    
    await update.effective_chat.send_message("Спасибо, что пользуетесь нашим ботом!")
    return ConversationHandler.END

async def extract_audio_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса извлечения аудиодорожки."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Отправьте видео или кружок для извлечения звука.")
    return EXTRACT_AUDIO

async def process_extract_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Процесс извлечения аудиодорожки из видео."""
    video_id = update.message.video.file_id or update.message.animation.file_id
    video_name = f"temp_video.mp4"
    audio_name = "extracted_audio.mp3"
    
    # Скачиваем видео
    new_file = await context.bot.get_file(video_id)
    await new_file.download_to_drive(custom_path=video_name)
    
    # Извлекаем аудиодорожку
    os.system(f"ffmpeg -i '{video_name}' -vn -acodec libmp3lame '{audio_name}'")
    
    # Отправляем назад извлечённый звук
    with open(audio_name, 'rb') as f:
        await update.effective_chat.send_audio(audio=f)
        
    # Убираем временные файлы
    os.remove(video_name)
    os.remove(audio_name)
    
    await update.effective_chat.send_message("Спасибо, что пользуетесь нашим ботом!")
    return ConversationHandler.END

async def remove_audio_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса удаления аудиодорожки."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Отправьте видео или кружок для удаления звука.")
    return REMOVE_AUDIO

async def process_remove_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Процесс удаления аудиодорожки из видео."""
    video_id = update.message.video.file_id or update.message.animation.file_id
    video_name = f"temp_video.mp4"
    output_name = "no_audio_video.mp4"
    
    # Скачиваем видео
    new_file = await context.bot.get_file(video_id)
    await new_file.download_to_drive(custom_path=video_name)
    
    # Удаляем звуковую дорожку
    os.system(f"ffmpeg -i '{video_name}' -an '{output_name}'")
    
    # Отправляем видео без звука
    with open(output_name, 'rb') as f:
        await update.effective_chat.send_video(video=f)
        
    # Убираем временные файлы
    os.remove(video_name)
    os.remove(output_name)
    
    await update.effective_chat.send_message("Спасибо, что пользуетесь нашим ботом!")
    return ConversationHandler.END

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик неправильных запросов."""
    await update.message.reply_text("Используйте доступные опции меню.")
    return ConversationHandler.END

def main() -> None:
    application = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(convert_file_start, pattern="^" + str(CONVERT_FILE) + "$"),
            CallbackQueryHandler(select_target_format, pattern=r'^source_'),
            CallbackQueryHandler(wait_for_file_to_convert, pattern=r'^target_'),
            CallbackQueryHandler(extract_audio_start, pattern="^" + str(EXTRACT_AUDIO) + "$"),
            CallbackQueryHandler(remove_audio_start, pattern="^" + str(REMOVE_AUDIO) + "$"),
        ],
        states={
            CONVERT_FILE: [
                MessageHandler(filters.Document.ALL, handle_file_conversion),
            ],
            EXTRACT_AUDIO: [
                MessageHandler(filters.Video | filters.Animation, process_extract_audio),
            ],
            REMOVE_AUDIO: [
                MessageHandler(filters.Video | filters.Animation, process_remove_audio),
            ],
        },
        fallbacks=[MessageHandler(filters.ALL, fallback)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
