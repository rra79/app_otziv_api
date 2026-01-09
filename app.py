import time
import requests
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="App Store Reviews (RU)",
    page_icon="📱",
    layout="centered"
)

# ================= UI =================
st.title("📱 App Store — отзывы (RU)")
st.caption("Быстрый сбор всех доступных отзывов из региона 🇷🇺 через Apple RSS")

with st.container():
    APP_ID = st.text_input(
        "App ID приложения",
        placeholder="Например: 686449807",
        help="Только цифры, без id"
    )

    START = st.button("🚀 Начать сбор", use_container_width=True)

st.divider()

# ================= ЛОГИКА =================
COUNTRY = "ru"

if START:

    if not APP_ID or not APP_ID.isdigit():
        st.error("❌ App ID должен содержать только цифры")
        st.stop()

    progress = st.progress(0)
    status = st.empty()

    all_reviews = []
    seen_ids = set()

    page = 1
    max_pages = 500  # защита от бесконечного цикла

    status.info("🔄 Начинаем сбор отзывов из региона RU")

    while page <= max_pages:

        progress.progress(min(page / 50, 1.0))
        status.write(f"📄 Страница: {page}")

        url = (
            f"https://itunes.apple.com/{COUNTRY}/rss/customerreviews/"
            f"page={page}/id={APP_ID}/sortby=mostrecent/json"
        )

        try:
            r = requests.get(url, timeout=10)

            if r.status_code != 200:
                break

            feed = r.json().get("feed", {})
            entries = feed.get("entry", [])

            if not entries:
                break

            # первая запись — метаданные приложения
            if page == 1:
                entries = entries[1:]

            if not entries:
                break

            for e in entries:
                review_id = e["id"]["label"]
                if review_id in seen_ids:
                    continue

                all_reviews.append({
                    "review_id": review_id,
                    "author": e["author"]["name"]["label"],
                    "rating": int(e["im:rating"]["label"]),
                    "title": e["title"]["label"],
                    "review_text": e["content"]["label"],
                    "review_date": e["updated"]["label"],
                    "app_version": e["im:version"]["label"],
                    "region": "RU"
                })

                seen_ids.add(review_id)

            page += 1
            time.sleep(0.05)

        except Exception as ex:
            st.warning(f"⚠️ Ошибка на странице {page}: {ex}")
            break

    # ================= СОХРАНЕНИЕ =================
    df = pd.DataFrame(all_reviews).drop_duplicates(subset=["review_id"])

    if not df.empty:
        df["review_date"] = pd.to_datetime(
            df["review_date"],
            errors="coerce",
            utc=True
        ).dt.tz_localize(None)

    csv_data = df.to_csv(index=False, encoding="utf-8-sig")
    df.to_excel("appstore_reviews_ru.xlsx", index=False)

    st.success(f"✅ Готово! Собрано отзывов: {len(df)}")

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            "⬇️ Скачать CSV",
            data=csv_data,
            file_name="appstore_reviews_ru.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        with open("appstore_reviews_ru.xlsx", "rb") as f:
            st.download_button(
                "⬇️ Скачать XLSX",
                data=f,
                file_name="appstore_reviews_ru.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

    st.divider()
    st.subheader("📊 Пример данных")
    st.dataframe(df.head(100), use_container_width=True)
