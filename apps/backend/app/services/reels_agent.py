from __future__ import annotations

import asyncio
import json
import logging
import random
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import User
from app.i18n.telegram import msg
from app.services.agent_usage import record_agent_usage
from app.services.ai_coach import _anthropic_usage, _clean_generated_text

logger = logging.getLogger(__name__)

REELS_TOPIC_FRAMING_RU = (
    "Задача для ролика (обязательно соблюдай смысл):\n"
    "- Разоблачаем в основном **вирусный/коммерческий хайп** вокруг слова «выгорание»: курсы, страх, размытые диагнозы в соцсетях, продажи «лечения» без опоры на факты.\n"
    "- **Одной короткой фразой** можно признать: длительный стресс и клиническое истощение — серьёзная тема, когда к ней подходят профессионально. Этот ролик **не** отрицает это ради шока.\n"
    "- **Нельзя** отказываться писать сценарий фразами вроде «не буду разносить» — вместо отказа переформулируй удар по **индустрии слов и денег**, а не по людям в беде.\n"
    "- Ведущий обращается к **обезличенной аудитории** в формате Reels, без «твоих» данных сна/шагов/скора из часов — этих цифр у тебя в контексте нет.\n"
)

REELS_TOPIC_FRAMING_EN = (
    "Reel angle (mandatory):\n"
    "- Debunk mainly **viral/commercial hype** around “burnout”: course mills, fear-selling, sloppy pop-psych labels on social.\n"
    "- In **one short sentence** you may acknowledge prolonged stress / clinical exhaustion is serious when handled properly. This reel does **not** deny that for shock value.\n"
    "- You must **not refuse** the script (no “I won’t tear this down…”). Reframe as attacking **industry wording and monetization**, not attacking sufferers.\n"
    "- Host speaks to a **generic audience** on camera. No private wearable stats (sleep/steps/score) — they are not in your context.\n"
)

REELS_REGENERATION_RU = (
    "=== ПЕРЕГЕНЕРАЦИЯ (второй черновик) ===\n"
    "Предыдущий ответ нарушил ТЗ: был отказ, уход в личный коучинг, выдуманные «твои» метрики сна/шагов/скора, или не было чёткого сценария Reels.\n"
    "Сейчас выдай **заново все 6 разделов** с нуля, строго по заголовкам. Только хайп/монетизация/мифы вокруг темы. "
    "Не отказывайся. Не выдумывай персональные цифры зрителя. Используй тот же Search JSON."
)

REELS_REGENERATION_EN = (
    "=== REGENERATION (second draft) ===\n"
    "The previous answer broke spec: refusal, personal wellness pivot, invented viewer sleep/steps/score, or missing the Reels script block.\n"
    "Regenerate **all six sections** from scratch with the exact headings. Focus on hype/monetization/myths only. "
    "Do not refuse. Do not invent private viewer metrics. Use the same Search JSON."
)


def _reels_output_failed_spec(text: str, lang: str) -> bool:
    """Detect refusals or coach-style hallucinated personal metrics so we can retry once."""
    raw = (text or "").strip()
    if not raw or len(raw) < 200:
        return False
    low = raw.lower()
    if lang == "en":
        refusal = ("i won't", "i will not", "i refuse", "can't tear", "cannot tear", "not fair to tear", "i can't in good faith")
        if any(m in low for m in refusal):
            return True
        if ("your sleep" in low or "your steps" in low) and ("score" in low or "/100" in low):
            return True
        return False
    refusal_ru = (
        "не буду",
        "не стану",
        "не могу разнести",
        "отказываюсь",
        "не буду разносить",
        "не разнесу",
        "не стану разносить",
    )
    if any(m in low for m in refusal_ru):
        return True
    if "не справедливо" in low and ("разнести" in low or "разнос" in low):
        return True
    if "интересная тема" in low and ("но я не буду" in low or "но не буду" in low or "но я не стану" in low):
        return True
    if ("у тебя" in low or "у вас" in low or "твой" in low or "твоё" in low or "твои " in low) and (
        ("сон" in low and ("мин" in low or "час" in low)) or "шаг" in low or "скор" in low or "/100" in low or " из 100" in low
    ):
        return True
    # Wellness pivot: several concrete "today" stats in one answer (hallucinated watch data)
    ru_stat_markers = sum(1 for k in ("сон", "шаг", "скор", "активност", "0 мин", " из 100", "/100") if k in low)
    if ru_stat_markers >= 3 and ("сегодня" in low or "сейчас" in low or "факт" in low):
        return True
    return False


MYTH_SEEDS_RU = [
    "миф многозадачность продуктивность исследования",
    "мотивация только деньгами бизнес миф",
    "работать 80 часов в неделю успех предприниматель",
    "positive thinking всегда лечит стресс психология",
    "миф поколение зумеры ленивые управление",
    "нужно любить свою работу чтобы преуспеть карьера",
    "миф left brain right brain креативность",
    "выгорание отдых выходные достаточно восстановление",
    "миф визуализация успеха без действий коучинг",
    "работа мечты страсть бизнес миф карьера",
    "эмоциональный интеллект тесты HR миф",
    "нужно найти страсть чтобы не выгореть психология",
]

MYTH_SEEDS_EN = [
    "multitasking productivity myth research",
    "money only motivation employees business myth",
    "hustle culture 80 hour week success debunked",
    "positive thinking alone cures stress psychology evidence",
    "generational stereotypes workplace myth research",
    "passion career success necessity debunk",
    "left brain right brain creativity myth",
    "weekend enough recovery burnout science",
    "manifestation visualization without action evidence",
    "dream job passion myth career psychology",
    "EQ workplace hiring pseudoscience criticism",
    "impostor syndrome always negative myth research",
]


def _search_ddgs(queries: list[str], max_per_query: int = 8) -> list[dict[str, str]]:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.warning("duckduckgo_search not installed")
        return []

    collected: list[dict[str, str]] = []
    seen: set[str] = set()
    with DDGS() as ddgs:
        for q in queries:
            q = (q or "").strip()
            if not q:
                continue
            try:
                for r in ddgs.text(q, max_results=max_per_query):
                    href = (r.get("href") or "").strip()
                    if not href or href in seen:
                        continue
                    seen.add(href)
                    collected.append(
                        {
                            "title": ((r.get("title") or "")[:400]).strip(),
                            "href": href[:2000],
                            "body": ((r.get("body") or "")[:600]).strip(),
                        }
                    )
            except Exception:
                logger.exception("ddgs query failed q=%s", q[:80])
                continue
            if len(collected) >= 22:
                break
    return collected[:22]


def _first_sentence_chunk(text: str, max_len: int = 160) -> str:
    """Take first sentence or a compact prefix — long monologue paragraphs are bad DDG queries."""
    t = " ".join((text or "").split())
    if not t:
        return ""
    for sep in ".!?":
        pos = t.find(sep)
        if 10 <= pos <= 400:
            return t[: pos + 1].strip()[:max_len]
    return t[:max_len].strip()


def _search_queries_from_user_hint(hint: str, lang: str) -> list[str]:
    """Build several short web queries from a long user draft (DDG works poorly on full paragraphs)."""
    raw = " ".join((hint or "").split())
    core = _first_sentence_chunk(raw, 200)
    short = core[:95].strip() if core else raw[:95].strip()
    out: list[str] = []
    seen: set[str] = set()

    def add(q: str) -> None:
        q = (q or "").strip()
        if len(q) < 6 or q in seen:
            return
        seen.add(q)
        out.append(q)

    low = raw.lower()
    if lang == "en":
        add(short)
        add(f"{short} wikipedia")
        add(f"{short} history OR origin")
        add(f"{short} myth OR debunk OR evidence")
        if "burnout" in low:
            add("burnout term history Freudenberger")
            add("burnout epidemic criticism psychology")
        if "german" in low or "psychiat" in low:
            add("burnout coined when psychiatry history")
    else:
        add(short)
        add(f"{short} википедия")
        add(f"{short} история термина")
        add(f"{short} миф правда факты")
        if "выгоран" in low:
            add("выгорание история термина психология")
            add("эмоциональное выгорание кто ввёл термин")
            add("Freudenberger выгорание")
            add("профессиональное выгорание история понятия")
        if "немец" in low or "психиатр" in low or "придуман" in low:
            add("история термина выгорание психиатр")
        # Extra English hits often help for names / science
        if "выгоран" in low or "немец" in low:
            add("burnout term origin history psychiatry")

    return out[:14]


def _gather_merged_for_seed(primary_q: str, lang: str) -> list[dict[str, str]]:
    primary_hits = _search_ddgs([primary_q], 7)
    if not primary_hits:
        return []

    anchor = primary_hits[0]
    anchor_title = anchor.get("title") or (anchor.get("body") or "")[:120] or primary_q
    if lang == "en":
        followups = [
            f"{anchor_title} debunk evidence study",
            f"{anchor_title} research meta-analysis criticism",
        ]
        evidence_qs = [
            f"{anchor_title} peer-reviewed systematic review evidence",
            f"{primary_q} fact check debunk",
        ]
    else:
        followups = [
            f"{anchor_title} опровержение исследование",
            f"{anchor_title} миф научные данные",
        ]
        evidence_qs = [
            f"{anchor_title} научные исследования метаанализ обзор",
            f"{primary_q} опровержение фактчек",
        ]

    secondary = _search_ddgs(followups, 6)
    tertiary = _search_ddgs(evidence_qs, 6)
    by_href: dict[str, dict[str, str]] = {}
    for item in primary_hits + secondary + tertiary:
        h = item.get("href")
        if h and h not in by_href:
            by_href[h] = item
    return list(by_href.values())[:20]


def _gather_merged_for_user_hint(hint: str, lang: str) -> list[dict[str, str]]:
    queries = _search_queries_from_user_hint(hint, lang)
    if not queries:
        queries = [_first_sentence_chunk(hint, 120) or hint[:120]]

    primary_hits = _search_ddgs(queries, 8)
    if not primary_hits:
        return []

    anchor = primary_hits[0]
    anchor_title = anchor.get("title") or (anchor.get("body") or "")[:120] or queries[0]
    short_seed = queries[0][:80] if queries else hint[:80]
    if lang == "en":
        followups = [
            f"{anchor_title} evidence study",
            f"{short_seed} criticism debate",
            "workplace stress history before burnout term",
        ]
    else:
        followups = [
            f"{anchor_title} исследование факты",
            f"{short_seed} критика мнения экспертов",
            "стресс на работе история до термина выгорание",
        ]
    tertiary = [
        f"{anchor_title} Wikipedia" if lang == "en" else f"{anchor_title} википедия",
    ]
    secondary = _search_ddgs(followups, 8)
    extra = _search_ddgs(tertiary, 6)
    by_href: dict[str, dict[str, str]] = {}
    for item in primary_hits + secondary + extra:
        h = item.get("href")
        if h and h not in by_href:
            by_href[h] = item
    return list(by_href.values())[:22]


async def _generate_reels_with_anthropic(
    lang: str,
    search_payload: list[dict[str, str]],
    *,
    user_id: UUID | None = None,
    creator_brief: str | None = None,
    correction_note: str | None = None,
    temperature: float = 0.45,
) -> str:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("Anthropic API key is not configured")

    allowed_urls = [item["href"] for item in search_payload if item.get("href")]
    system_prompt = (
        "You write content for Instagram Reels ONLY: a debunk / myth-busting short video about business or psychology. "
        "You are NOT a therapist, NOT a personal health coach, and NOT an Apple Watch / fitness app assistant. "
        "You receive JSON with real web search snippets (title, href, body). Follow this pipeline:\n"
        "STEP 1 — From the snippets, name one concrete popular or viral claim that looks false, "
        "oversimplified, or fairly questionable (business or psychology). Say why it is problematic in one short phrase.\n"
        "STEP 2 — Using ONLY the snippet bodies and titles, summarize counter-evidence: facts, research pointers, "
        "or clear logical flaws. If snippets only hint at science, say 'suggests' not 'proves'. "
        "If evidence is weak or mixed, say so briefly.\n"
        "STEP 3 — Write a Reels SHOOTING SCRIPT (spoken lines + beats), not an essay: strong hook (0–3s), "
        "middle builds tension, payoff delivers the debunk. Include on-screen text hints and rough timing. "
        "Optional one-line CTA (save / follow / comment). Address the generic viewer / audience, not one person's private life.\n"
        "Hard rules:\n"
        "- Do not invent URLs or paper titles. Every URL you cite MUST appear exactly in the provided JSON href list.\n"
        "- NEVER invent or mention the reader's private biometrics: sleep hours, steps, HRV, heart rate, daily score, "
        "recovery mode, wearable logs, or any personal health stats. Those values are NOT in your context — if you cite "
        "them you are hallucinating. You may only mention such numbers if they literally appear inside the Search JSON snippets.\n"
        "- Do NOT pivot into personal counselling, 'how are you feeling', or lifestyle coaching. Stay on the public claim / "
        "internet discourse and the debunk for a broad audience.\n"
        "- You must NEVER refuse to deliver the full six-section output (no moral 'I won't…' / 'не буду…' gatekeeping). "
        "If the creator brief targets hype, industry, or wording around a sensitive topic, debunk THAT responsibly instead of refusing.\n"
        "- No personal attacks; critique ideas and common claims, not named individuals unless they are clearly "
        "public figures tied to the claim in the snippets.\n"
        "Output structure (same language as requested), use these headings exactly — no extra sections before or after:\n"
        "1) Шаг 1 — Тема / Step 1 — Topic — one line\n"
        "2) Шаг 2 — Спорное утверждение / Step 2 — Dubious claim — 2–4 sentences\n"
        "3) Шаг 2 — Опровержение и опора / Step 2 — Refutation & support — 3–7 sentences, plain language\n"
        "4) Шаг 3 — Сценарий Reels / Step 3 — Reels script — Хук (0–3с) — Завязка — Развязка (on-screen text hints)\n"
        "5) Источники / Sources — bullet list: title — URL (only from input)\n"
        "6) One-line disclaimer: creator must verify links and claims before publishing.\n"
        "No markdown code fences; no --- separators."
    )
    user_prompt = (
        f"Language for the entire output: {'English' if lang == 'en' else 'Russian'}\n"
        f"Deliverable: a single Reel debunk script for social media, following the six headings. Not a chat reply.\n"
        f"Allowed URL list (you may only cite these): {json.dumps(allowed_urls, ensure_ascii=False)}\n"
        f"Search JSON:\n{json.dumps(search_payload, ensure_ascii=False)}"
    )
    if creator_brief:
        user_prompt += (
            "\n\nCreator direction — use ONLY as angle / hook ideas / which myth to attack. "
            "All factual points in sections 2–3 must still be grounded in the Search JSON, not invented. "
            "Do not treat the creator note as medical history or personal health data.\n"
            f"{creator_brief}"
        )
    if correction_note:
        user_prompt += "\n\n" + correction_note.strip() + "\n"

    timeout = max(30, int(settings.reels_agent_anthropic_timeout_sec))
    temp = max(0.0, min(1.0, float(temperature)))
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.anthropic_model,
                "max_tokens": max(800, min(4096, settings.reels_agent_anthropic_max_tokens)),
                "temperature": temp,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
        )
        response.raise_for_status()
        body = response.json()
        in_t, out_t = _anthropic_usage(body)
        for block in body.get("content", []):
            if block.get("type") == "text":
                text = (block.get("text") or "").strip()
                if text:
                    if user_id is not None:
                        record_agent_usage(
                            user_id,
                            provider="anthropic",
                            model=settings.anthropic_model,
                            operation="reels_script",
                            input_tokens=in_t,
                            output_tokens=out_t,
                        )
                    return _clean_generated_text(text)
    raise RuntimeError("Empty response from Anthropic")


async def compose_reels_script(
    lang: str,
    *,
    user_id: UUID | None = None,
    user_topic_hint: str | None = None,
) -> str:
    hint = (user_topic_hint or "").strip()
    if hint:
        hint = hint[:3500]
        merged: list[dict[str, str]] = []
        for attempt in range(4):
            merged = await asyncio.to_thread(_gather_merged_for_user_hint, hint, lang)
            # User drafts: DDG is noisy; allow 1+ URLs — model must stay conservative in claims.
            if len(merged) >= 1:
                break
            await asyncio.sleep(0.55)
        if len(merged) < 1:
            return msg(lang, "reels_search_empty")
        brief = hint
        if len(merged) == 1:
            brief = (
                f"{hint}\n\n[Сервис: найден только один URL в выдаче — формулируй осторожно, не раздувай факты "
                "за пределы сниппета, в блоке источников — только эта ссылка.]"
                if lang != "en"
                else f"{hint}\n\n[Service: only one search URL — stay cautious; Sources section may list only that URL.]"
            )
        framing = REELS_TOPIC_FRAMING_EN if lang == "en" else REELS_TOPIC_FRAMING_RU
        full_brief = f"{framing}\n\n---\n\n{brief}"
        try:
            text = await _generate_reels_with_anthropic(
                lang,
                merged,
                user_id=user_id,
                creator_brief=full_brief,
                correction_note=None,
                temperature=0.45,
            )
            if _reels_output_failed_spec(text, lang):
                logger.warning("reels output failed spec, one retry lang=%s", lang)
                regen = REELS_REGENERATION_EN if lang == "en" else REELS_REGENERATION_RU
                text = await _generate_reels_with_anthropic(
                    lang,
                    merged,
                    user_id=user_id,
                    creator_brief=full_brief,
                    correction_note=regen,
                    temperature=0.25,
                )
            return text
        except Exception:
            logger.exception("reels anthropic failed")
            return msg(lang, "reels_ai_failed")

    seeds = MYTH_SEEDS_EN if lang == "en" else MYTH_SEEDS_RU
    merged = []
    for _attempt in range(4):
        primary_q = random.choice(seeds)
        merged = await asyncio.to_thread(_gather_merged_for_seed, primary_q, lang)
        if len(merged) >= 3:
            break
        await asyncio.sleep(0.45)
    if len(merged) < 3:
        return msg(lang, "reels_search_empty")

    try:
        return await _generate_reels_with_anthropic(
            lang, merged, user_id=user_id, creator_brief=None, correction_note=None, temperature=0.55
        )
    except Exception:
        logger.exception("reels anthropic failed")
        return msg(lang, "reels_ai_failed")


async def compose_reels_script_for_telegram_user(
    db: Session, telegram_user_id: int, user_topic: str | None = None
) -> str:
    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    lang = user.language if user else "ru"
    uid = user.id if user else None
    return await compose_reels_script(lang, user_id=uid, user_topic_hint=user_topic)
