import streamlit as st
import pandas as pd
import requests
import time
import re
import hashlib
from collections import Counter
from io import BytesIO

# ================= НАСТРОЙКИ =================
st.set_page_config(
    page_title="App Store Reviews Analyzer",
    layout="wide"
)

st.title("📱 Анализ отзывов App Store")
st.caption("Сбор и анализ русских отзывов через Apple RSS API")

# ================= ВСПОМОГАТЕЛЬНЫЕ =================
CYRILLIC_RE = re.compile(r"[а-яА-ЯёЁ]")
_lang_cache = {}

def is_russian(text: str) -> bool:
    if not text:
        return False
    key = hashlib.md5(text.encode("utf-8")).hexdigest()
    if key in _lang_cache:
        return _lang_cache[key]
    result = bool(CYRILLIC_RE.search(text))
    _lang_cache[key] = result
    return result


NEGATIVE = {
    "баг": "Баги",
    "ошиб": "Ошибки",
    "вылет": "Краши",
    "не работает": "Не работает",
    "медлен": "Производительность",
    "лага": "Производительность",
    "реклама": "Реклама",
    "подпис": "Подписка",
}

POSITIVE = {
    "удоб": "Удобство",
    "отлич": "Качество",
    "класс": "Качество",
    "полез": "Польза",
    "быстро": "Скорость",
}

def extract_problems_and_pluses(texts):
    problems = Counter()
    pluses = Counter()
    for t in texts:
        low = t.lower()
        for k, v in NEGATIVE.items():
            if k in low:
                problems[v] += 1
        for k, v in POSITIVE.items():
            if k in low:
                pluses[v] += 1
    return problems, pluses


def collect_reviews(app_id: str, regions: list, stop_flag):
    all_reviews = []
    seen = set()

    for country in regions:
        page = 1
        while True:
            if stop_flag():
                return all_reviews

            url = (
                f"https://itunes.apple.com/{country}/rss/customerreviews/"
                f"page={page}/id={app_id}/sortby=mostrecent/json"
            )

            try:
                r = requests.get(url, timeout=15)
                if r.status_code != 200:
                    break

                feed = r.json().get("feed", {})
                entries = feed.get("entry", [])
                if not entries:
                    break

                if page == 1:
                    entries = entries[1:]  # metadata

                for e in entries:
                    rid = e["id"]["label"]
                    if rid in seen:
                        continue

                    text = e["content"]["label"]
                    if is_russian(text):
                        all_reviews.append({
                            "review_id": rid,
                            "author": e["author"]["name"]["label"],
                            "rating": int(e["im:rating"]["label"]),
                            "title": e["title"]["label"],
                            "review_text": text,
                            "review_date": e["updated"]["label"],
                            "version": e["im:version"]["label"],
                            "region": country
                        })
                        seen.add(rid)

                page += 1
                time.sleep(0.2)

            except Exception:
                break

    return all_reviews


# ================= UI =================
APP_ID = st.text_input("App ID (только цифры)", placeholder="686449807")

REGIONS = st.multiselect(
    "Выберите регионы",
    ["ru", "us", "kz", "ua", "by", "de", "fr"],
    default=["ru"]
)

if "stop" not in st.session_state:
    st.session_state.stop = False

col1, col2 = st.columns(2)
with col1:
    start_btn = st.button("🚀 Начать сбор")
with col2:
    stop_btn = st.button("🛑 Остановить")
    if stop_btn:
        st.session_state.stop = True

def stop_flag():
    return st.session_state.stop


@st.cache_data(show_spinner=False)
def load_data(app_id, regions):
    return collect_reviews(app_id, list(regions), stop_flag)


# ================= ЛОГИКА =================
if start_btn:
    st.session_state.stop = False

    if not APP_ID.isdigit():
        st.error("❌ App ID должен содержать только цифры")
        st.stop()

    with st.spinner("⏳ Сбор отзывов..."):
        data = load_data(APP_ID, tuple(REGIONS))

    if not data:
        st.warning("Отзывы не найдены")
        st.stop()

    df = pd.DataFrame(data).drop_duplicates("review_id")

    # ⚠️ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ
    df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
    df["review_date"] = df["review_date"].dt.strftime("%Y-%m-%d %H:%M:%S")

    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

    st.success(f"✅ Собрано отзывов: {len(df)}")

    # ===== Метрики =====
    st.subheader("📊 Общая статистика")
    st.metric("Средний рейтинг", round(df["rating"].mean(), 2))

    st.subheader("🌍 Средний рейтинг по регионам")
    st.bar_chart(df.groupby("region")["rating"].mean())

    st.subheader("⭐ Распределение оценок")
    st.bar_chart(df["rating"].value_counts().sort_index())

    # ===== Анализ =====
    problems, pluses = extract_problems_and_pluses(df["review_text"])

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("❌ Основные проблемы")
        for k, v in problems.most_common(5):
            st.write(f"{k}: {v}")

    with c2:
        st.subheader("✅ Основные плюсы")
        for k, v in pluses.most_common(5):
            st.write(f"{k}: {v}")

    # ===== Экспорт =====
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("⬇️ Скачать CSV", csv, "reviews.csv")

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Reviews")

    st.download_button(
        "⬇️ Скачать XLSX",
        buffer.getvalue(),
        "reviews.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.subheader("🔍 Пример отзывов")
    st.dataframe(df.head(50))
