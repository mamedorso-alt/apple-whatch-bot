MESSAGES = {
    "ru": {
        "start": (
            "Привет! Я AI-ассистент: здоровье/фокус и разбор продаж.\n"
            "Привяжите аккаунт: /link CODE из приложения.\n"
            "Здоровье: /today /week /insights /trends /profile /weight /mood /meal /coach\n"
            "Продажи: /weekly /month /plan /risks /actions /ask\n"
            "Голос и свободный текст поддерживаются. Кнопка «Сценарий рилса» — если включено. /lang ru|en /help"
        ),
        "help": (
            "Команды здоровье и фокус:\n"
            "/today /week — отчёты\n"
            "/insights или /day — инсайт дня\n"
            "/trends — недельные тренды\n"
            "/profile — профиль\n"
            "/weight 72.4 — вес\n"
            "/mood 3 2 — стресс и усталость 0–5 за сегодня\n"
            "/meal — как отправить фото еды\n"
            "/coach — AI-коуч (или /coach ваш вопрос)\n"
            "/reel — сценарий Reels (если включено на сервере)\n"
            "\nПродажи:\n"
            "/weekly /month /plan /risks /actions /ask ВОПРОС\n"
            "\nОбщее: /link CODE, /lang ru|en, /help"
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
        "weight_usage": "Использование: /weight 72.4",
        "weight_saved": "Вес сохранён.",
        "mood_usage": "Использование: /mood 3 2 (стресс и усталость от 0 до 5)",
        "mood_saved": "Записал самочувствие на сегодня.",
        "meal_help": "Сфотографируйте еду и отправьте фото сюда (после /link). Оценка ккал приблизительная.",
        "meal_disabled": "Лог еды выключен в профиле.",
        "meal_download_failed": "Не удалось скачать фото из Telegram.",
        "meal_ai_missing": "Анализ фото не настроен: задайте ANTHROPIC_API_KEY или OPENAI_API_KEY на сервере.",
        "meal_analyze_failed": "Не удалось разобрать фото. Попробуйте другое фото или свет.",
        "reels_disabled": "Сценарии Reels на сервере выключены.",
        "reels_not_allowed": "Команда /reel доступна только для разрешённых аккаунтов.",
        "reels_search_empty": "Не удалось найти достаточно материалов в интернете для сценария. Попробуйте позже.",
        "reels_ai_failed": "Поиск сработал, но не удалось сгенерировать текст. Проверьте ANTHROPIC_API_KEY и попробуйте снова.",
    },
    "en": {
        "start": (
            "Hi! I'm your AI assistant for health/focus and sales.\n"
            "Link: /link CODE from the app.\n"
            "Health: /today /week /insights /trends /profile /weight /mood /meal /coach\n"
            "Sales: /weekly /month /plan /risks /actions /ask\n"
            "Voice and free text work. «Reel script» button when enabled. /lang ru|en /help"
        ),
        "help": (
            "Health & focus:\n"
            "/today /week — reports\n"
            "/insights or /day — daily insight\n"
            "/trends — weekly trends\n"
            "/profile — profile summary\n"
            "/weight 72.4 — log weight\n"
            "/mood 3 2 — stress & fatigue 0–5 for today\n"
            "/meal — food photo how-to\n"
            "/coach — AI coach (or /coach your question)\n"
            "/reel — Reels script (if enabled on server)\n"
            "\nSales:\n"
            "/weekly /month /plan /risks /actions /ask QUESTION\n"
            "\nGeneral: /link CODE, /lang ru|en, /help"
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
        "weight_usage": "Usage: /weight 72.4",
        "weight_saved": "Weight saved.",
        "mood_usage": "Usage: /mood 3 2 (stress and fatigue 0–5)",
        "mood_saved": "Logged how you feel for today.",
        "meal_help": "Take a photo of your meal and send it here (after /link). Calorie estimate is approximate.",
        "meal_disabled": "Food logging is disabled in your profile.",
        "meal_download_failed": "Could not download the photo from Telegram.",
        "meal_ai_missing": "Food photo analysis is not configured (set ANTHROPIC_API_KEY or OPENAI_API_KEY).",
        "meal_analyze_failed": "Could not analyze the photo. Try another angle or lighting.",
        "reels_disabled": "Reels scripts are disabled on the server.",
        "reels_not_allowed": "/reel is only available for allowlisted accounts.",
        "reels_search_empty": "Could not gather enough web sources for a script right now. Try again later.",
        "reels_ai_failed": "Search worked but text generation failed. Check ANTHROPIC_API_KEY and retry.",
    },
}


def msg(lang: str, key: str) -> str:
    normalized = "en" if lang == "en" else "ru"
    return MESSAGES[normalized][key]
