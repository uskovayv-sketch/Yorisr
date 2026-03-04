# -*- coding: utf-8 -*-
"""
Юридический бот-помощник на базе YandexGPT
Работает через переменные окружения (безопасно!)
"""

import os
import asyncio
import logging
import aiohttp
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import nest_asyncio
# Добавь ЭТО в самый верх bot.py (после импортов)
import asyncio
import logging
from aiohttp import web

# Простой HTTP сервер для Health Check Render
async def handle_health(request):
    return web.Response(text="OK")

async def run_health_server():
    app = web.Application()
    app.router.add_get('/', handle_health)
    app.router.add_get('/health', handle_health)
    
    # Render передает порт в переменной PORT (обычно 10000)
    port = int(os.environ.get('PORT', 10000))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Health check server started on port {port}")
    

# В функции main() добавь запуск health сервера:
async def main():
    # Запускаем health check сервер (чтобы Render не ругался)
    asyncio.create_task(run_health_server())
    
    logging.info("Бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
# Разрешаем asyncio в Colab (если будешь тестировать)
nest_asyncio.apply()

# ================== БЕРЕМ ТОКЕНЫ ИЗ ОКРУЖЕНИЯ ==================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
YANDEX_API_KEY = os.environ.get('YANDEX_API_KEY')
YANDEX_FOLDER_ID = os.environ.get('YANDEX_FOLDER_ID')

# Проверяем, что токены загрузились
if not TELEGRAM_TOKEN:
    raise ValueError("Нет TELEGRAM_TOKEN! Добавь в переменные окружения.")
if not YANDEX_API_KEY:
    raise ValueError("Нет YANDEX_API_KEY! Добавь в переменные окружения.")
if not YANDEX_FOLDER_ID:
    raise ValueError("Нет YANDEX_FOLDER_ID! Добавь в переменные окружения.")

# URL для YandexGPT
YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# ================== КЛАВИАТУРА ==================
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Перевести текст"), KeyboardButton(text="📚 Объяснить термин")],
        [KeyboardButton(text="ℹ️ О боте"), KeyboardButton(text="❓ Помощь")]
    ],
    resize_keyboard=True
)

# ================== ФУНКЦИИ YANDEXGPT ==================

async def call_yandex_gpt(prompt, system_prompt=None, temperature=0.3, max_tokens=1000):
    """
    Отправляет запрос к YandexGPT и возвращает ответ
    """
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    if system_prompt is None:
        system_prompt = """
        Ты - юридический помощник, который переводит сложные юридические тексты на понятный язык.
        Отвечай дружелюбно, но профессионально. Используй примеры, где это уместно.
        """
    
    data = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": max_tokens
        },
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": prompt}
        ]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(YANDEX_GPT_URL, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['result']['alternatives'][0]['message']['text']
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка API: {response.status} - {error_text}")
                    return f"❌ Ошибка API. Код: {response.status}"
    except Exception as e:
        logger.error(f"Исключение: {e}")
        return "❌ Ошибка соединения с нейросетью."

async def translate_legal_to_human(text):
    """Переводит юридический текст на человеческий язык"""
    system_prompt = """
    Ты - эксперт по юридическому переводу. Твоя задача - переводить сложные юридические тексты 
    на простой, понятный язык. Сохраняй суть, но убирай юридическую сложность.
    Формат ответа:
    🟢 Перевод на человеческий:
    [понятное объяснение]
    
    💡 Важные термины (если есть):
    - термин: объяснение
    """
    return await call_yandex_gpt(text, system_prompt, temperature=0.3, max_tokens=1500)

async def explain_term(term):
    """Объясняет юридический термин"""
    system_prompt = """
    Ты - юридический словарь. Объясняй юридические термины простым языком.
    Формат ответа:
    📚 Термин: [термин]
    
    Простое объяснение:
    [объяснение простыми словами]
    
    Пример использования:
    [пример]
    """
    return await call_yandex_gpt(term, system_prompt, temperature=0.2, max_tokens=800)

# ================== ОБРАБОТЧИКИ КОМАНД ==================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 *Привет! Я юридический помощник*\n\n"
        "🔵 Переведу юридический текст на понятный язык\n"
        "📚 Объясню юридические термины\n\n"
        "Выбери действие на клавиатуре!",
        parse_mode="Markdown",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
@dp.message(lambda message: message.text == "❓ Помощь")
async def cmd_help(message: types.Message):
    await message.answer(
        "📌 *Как пользоваться:*\n\n"
        "• Отправь текст - переведу\n"
        "• /term [термин] - объясню термин\n"
        "• Кнопки для навигации",
        parse_mode="Markdown",
        reply_markup=main_keyboard
    )

@dp.message(lambda message: message.text == "ℹ️ О боте")
async def about_bot(message: types.Message):
    await message.answer(
        "🤖 *О боте*\n\n"
        "Технологии: YandexGPT + Aiogram\n"
        "Работает 24/7 на Render.com",
        parse_mode="Markdown",
        reply_markup=main_keyboard
    )

@dp.message(lambda message: message.text == "📝 Перевести текст")
async def ask_for_text(message: types.Message):
    await message.answer("Отправь текст, а я переведу его с юридического на человеческий.")

@dp.message(lambda message: message.text == "📚 Объяснить термин")
async def ask_for_term(message: types.Message):
    await message.answer("Напиши термин, например: *ипотека*", parse_mode="Markdown")

@dp.message(Command("term"))
async def handle_term_command(message: types.Message):
    term = message.text[6:].strip()
    if not term:
        await message.answer("Напиши термин после /term")
        return
    
    await bot.send_chat_action(message.chat.id, action="typing")
    explanation = await explain_term(term)
    await message.answer(explanation, reply_markup=main_keyboard)

# ================== ОСНОВНОЙ ОБРАБОТЧИК ==================

@dp.message()
async def handle_message(message: types.Message):
    # Игнорируем команды и кнопки
    if message.text.startswith('/') or message.text in main_keyboard_buttons:
        return
    
    if len(message.text) > 5000:
        await message.answer("❌ Текст слишком длинный. Максимум 5000 символов.")
        return
    
    await bot.send_chat_action(message.chat.id, action="typing")
    
    try:
        # Определяем тип запроса
        if len(message.text.split()) < 10 and not any(
            word in message.text.lower() for word in ['статья', 'закон', 'кодекс']
        ):
            response = await explain_term(message.text)
        else:
            response = await translate_legal_to_human(message.text)
        
        await message.answer(response, reply_markup=main_keyboard)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer("❌ Что-то пошло не так. Попробуй еще раз.")

# ================== ЗАПУСК ==================

async def main():
    logger.info("Бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
