import time
import hashlib
import requests
import pandas as pd
import streamlit as st
import re

st.set_page_config(page_title="App Store Reviews Scraper", layout="centered")

st.title("📱 App Store — сбор русских отзывов")
st.write("Сбор всех доступных русских отзывов через официальный Apple RSS API")

# ===== ВВОД =====
APP_ID = st.text_input(
    "App ID приложения (только цифры)",
    placeholder="например: 686449807"
)

START_BUTTON = st.button("🚀 Начать сбор")

# ===== РЕГИОНЫ =====
COUNTRIES = [
    "ru","us","gb","de","fr","it","es","ca","au","br","mx","jp","kr",
    "ua","kz","by","pl","nl","se","no","fi","dk","tr","il","ae","sa",
    "in","id","th","vn","ph","my","sg","hk","tw","cz","sk","hu","ro",
    "bg","hr","rs","lt","lv","ee","pt","ch","at","be","ie","gr","za","eg"
]

# ===== ФИЛЬТР РУССКОГО ТЕКСТА (БЕЗ langdetect) =====
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

# ===== СБОР =====
if START_BUTTON:

    if not APP_ID or not APP_ID.isdigit():
        st.error("❌ App ID должен содержать только цифры")
        st.stop()

    progress = st.progress(0)
    status = st.empty()

    all_reviews = []
    seen_ids = set()

    for i, country in enumerate(COUNTRIES, start=1):
        status.write(f"🌍 Регион: **{country}**")
        progress.progress(i / len(COUNTRIES))

        page = 1
        while True:
            url = (
                f"https://itunes.apple.com/{country}/rss/customerreviews/"
                f"page={page}/id={APP_ID}/sortby=mostrecent/json"
            )

            try:
                r = requests.get(url, timeout=15)
                if r.status_code != 200:
                    break

                feed = r.json().get("feed", {})
                entries = feed.get("entry", [])

                if not entries:
                    break

                # первая запись — метаданные приложения
                if page == 1:
                    entries = entries[1:]

                for e in entries:
                    review_id = e["id"]["label"]
                    text = e["content"]["label"]

                    if review_id in seen_ids:
                        continue

                    if is_russian(text):
                        all_reviews.append({
                            "review_id": review_id,
                            "author": e["author"]["name"]["label"],
                            "rating": int(e["im:rating"]["label"]),
                            "title": e["title"]["label"],
                            "review_text": text,
                            "review_date": e["updated"]["label"],
                            "app_version": e["im:version"]["label"],
                            "region": country
                        })
                        seen_ids.add(review_id)

                page += 1
                time.sleep(0.25)

            except Exception as ex:
                st.warning(f"⚠️ Ошибка {country}, стр. {page}: {ex}")
                break

    # ===== СОХРАНЕНИЕ =====
    df = pd.DataFrame(all_reviews).drop_duplicates(subset=["review_id"])

    if not df.empty and "review_date" in df.columns:
        df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce", utc=True)
        df["review_date"] = df["review_date"].dt.tz_localize(None)

    csv_data = df.to_csv(index=False, encoding="utf-8-sig")
    df.to_excel("appstore_reviews_ru.xlsx", index=False)

    st.success(f"✅ Готово! Русских отзывов: {len(df)}")

    st.download_button(
        "⬇️ Скачать CSV",
        data=csv_data,
        file_name="appstore_reviews_ru.csv",
        mime="text/csv"
    )

    with open("appstore_reviews_ru.xlsx", "rb") as f:
        st.download_button(
            "⬇️ Скачать XLSX",
            data=f,
            file_name="appstore_reviews_ru.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.dataframe(df.head(50))
