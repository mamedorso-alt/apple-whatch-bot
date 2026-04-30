MESSAGES = {
    "ru": {
        "start": (
            "Привет! Я помогу с отчетами продуктивности.\n"
            "Привяжите аккаунт через /link CODE из iOS приложения.\n"
            "Команды: /today /week /coach [/вопрос] /ask ВОПРОС /lang ru|en /help\n"
            "Также можно писать просто текстом без команды."
        ),
        "help": (
            "Доступные команды:\n"
            "/start - приветствие\n"
            "/link CODE - привязать Telegram к приложению\n"
            "/today - отчет за сегодня\n"
            "/week - отчет за 7 дней\n"
            "/coach - персональная AI-рекомендация\n"
            "/coach ВОПРОС - AI-ответ по вашему вопросу\n"
            "/ask ВОПРОС - AI-диалог\n"
            "/lang ru|en - сменить язык\n"
            "/help - помощь\n"
            "Можно писать и без команды: я отвечу как AI-коуч."
        ),
        "link_usage": "Использование: /link CODE",
        "link_success": "Готово! Аккаунт успешно привязан.",
        "link_invalid": "Код не найден или уже использован.",
        "link_expired": "Срок действия кода истек. Сгенерируйте новый в приложении.",
        "already_linked_other": "Этот код принадлежит другому Telegram аккаунту.",
        "ask_usage": "Использование: /ask ВАШ_ВОПРОС",
        "voice_not_configured": "Голосовые сообщения пока не настроены. Используйте текст или настройте OPENAI_API_KEY на сервере.",
        "voice_transcription_failed": "Не удалось распознать голосовое сообщение. Попробуйте еще раз или отправьте текст.",
        "generic_processing_error": "Не удалось обработать сообщение. Попробуйте еще раз через несколько секунд.",
        "lang_usage": "Использование: /lang ru|en",
        "lang_updated_ru": "Язык переключен на русский.",
        "lang_updated_en": "Language switched to English.",
        "today_stub": "Отчет /today будет доступен на следующем шаге MVP.",
        "week_stub": "Отчет /week будет доступен на следующем шаге MVP.",
        "unknown": "Неизвестная команда. Используйте /help.",
    },
    "en": {
        "start": (
            "Hi! I help with productivity reports.\n"
            "Link your account using /link CODE from the iOS app.\n"
            "Commands: /today /week /coach [question] /ask QUESTION /lang ru|en /help\n"
            "You can also just send plain text."
        ),
        "help": (
            "Available commands:\n"
            "/start - greeting\n"
            "/link CODE - link Telegram with app account\n"
            "/today - today's report\n"
            "/week - 7-day report\n"
            "/coach - personal AI recommendation\n"
            "/coach QUESTION - AI answer for your question\n"
            "/ask QUESTION - AI dialogue\n"
            "/lang ru|en - switch language\n"
            "/help - help\n"
            "You can write without commands and I will reply as AI coach."
        ),
        "link_usage": "Usage: /link CODE",
        "link_success": "Done! Your account is linked.",
        "link_invalid": "Code not found or already used.",
        "link_expired": "Code has expired. Generate a new code in the app.",
        "already_linked_other": "This code belongs to another Telegram account.",
        "ask_usage": "Usage: /ask YOUR_QUESTION",
        "voice_not_configured": "Voice messages are not configured yet. Use text or configure OPENAI_API_KEY on the server.",
        "voice_transcription_failed": "Could not transcribe the voice message. Please try again or send text.",
        "generic_processing_error": "I couldn't process this message right now. Please try again in a few seconds.",
        "lang_usage": "Usage: /lang ru|en",
        "lang_updated_ru": "Язык переключен на русский.",
        "lang_updated_en": "Language switched to English.",
        "today_stub": "/today report will be available in the next MVP step.",
        "week_stub": "/week report will be available in the next MVP step.",
        "unknown": "Unknown command. Use /help.",
    },
}


def msg(lang: str, key: str) -> str:
    normalized = "en" if lang == "en" else "ru"
    return MESSAGES[normalized][key]
