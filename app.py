import time
import requests
import pandas as pd
import streamlit as st
from io import BytesIO

# ================= CONFIG =================
st.set_page_config(
    page_title="App Store Reviews Dashboard",
    page_icon="📊",
    layout="wide"
)

# ================= UI =================
st.title("📱 App Store — Аналитика отзывов")
st.caption("Сбор + дашборды • Apple RSS API")

APP_ID = st.text_input("App ID приложения", placeholder="686449807")

REGIONS = st.multiselect(
    "Регионы App Store",
    options=[
        "ru","us","gb","de","fr","it","es","ca","au","jp","kr","br","mx",
        "pl","nl","se","no","fi","dk","tr","ae","sa","in"
    ],
    default=["ru"]
)

col1, col2 = st.columns(2)
START = col1.button("🚀 Начать сбор", use_container_width=True)
STOP = col2.button("⛔ Остановить", use_container_width=True)

st.divider()

# ================= STATE =================
if "stop" not in st.session_state:
    st.session_state.stop = False
if STOP:
    st.session_state.stop = True

# ================= SENTIMENT =================
POSITIVE = {"хорош", "отличн", "класс", "супер", "люблю", "удобн"}
NEGATIVE = {"плох", "ужас", "баг", "лага", "глюч", "ненавиж"}

def sentiment(text: str) -> str:
    t = text.lower()
    score = 0
    for w in POSITIVE:
        if w in t:
            score += 1
    for w in NEGATIVE:
        if w in t:
            score -= 1
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"

# ================= SCRAPER =================
@st.cache_data(show_spinner=False)
def fetch_reviews(app_id: str, regions: tuple):
    all_reviews = []
    seen = set()

    progress = st.progress(0)
    status = st.empty()

    total = len(regions) * 50
    step = 0

    for region in regions:
        for page in range(1, 51):

            if st.session_state.stop:
                return pd.DataFrame(all_reviews)

            url = (
                f"https://itunes.apple.com/{region}/rss/customerreviews/"
                f"page={page}/id={app_id}/sortby=mostrecent/json"
            )

            try:
                r = requests.get(url, timeout=10)
                if r.status_code != 200:
                    break

                entries = r.json().get("feed", {}).get("entry", [])
                if page == 1:
                    entries = entries[1:]
                if not entries:
                    break

                for e in entries:
                    rid = e["id"]["label"]
                    if rid in seen:
                        continue

                    text = e["content"]["label"]
                    all_reviews.append({
                        "review_id": rid,
                        "rating": int(e["im:rating"]["label"]),
                        "review_text": text,
                        "sentiment": sentiment(text),
                        "review_date": e["updated"]["label"],
                        "region": region.upper()
                    })
                    seen.add(rid)

                step += 1
                progress.progress(min(step / total, 1.0))
                status.write(f"🌍 {region.upper()} • стр. {page}")

                time.sleep(0.05)

            except Exception:
                break

    return pd.DataFrame(all_reviews)

# ================= RUN =================
if START:

    st.session_state.stop = False

    if not APP_ID.isdigit():
        st.error("❌ App ID должен быть числом")
        st.stop()

    if not REGIONS:
        st.error("❌ Выберите регион")
        st.stop()

    with st.spinner("🔄 Сбор отзывов..."):
        df = fetch_reviews(APP_ID, tuple(REGIONS))

    if df.empty:
        st.warning("⚠️ Нет данных")
        st.stop()

    df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
    df.dropna(subset=["review_date"], inplace=True)

    st.success(f"✅ Собрано отзывов: {len(df)}")

    # ================= DASHBOARD =================
    st.divider()
    st.header("📊 Дашборд")

    c1, c2, c3 = st.columns(3)
    c1.metric("Всего отзывов", len(df))
    c2.metric("Средний рейтинг", round(df["rating"].mean(), 2))
    c3.metric("Регионов", df["region"].nunique())

    st.subheader("⭐ Распределение рейтингов")
    st.bar_chart(df["rating"].value_counts().sort_index())

    st.subheader("💬 Тональность отзывов")
    st.bar_chart(df["sentiment"].value_counts())

    st.subheader("🌍 Отзывы по регионам")
    st.bar_chart(df["region"].value_counts())

    st.subheader("📈 Динамика отзывов")
    daily = df.groupby(df["review_date"].dt.date).size()
    st.line_chart(daily)

    st.subheader("🌎 Средний рейтинг по регионам")
    avg_region = df.groupby("region")["rating"].mean().sort_values()
    st.bar_chart(avg_region)

    # ================= EXPORT =================
    st.divider()
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    xlsx = BytesIO()
    with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    xlsx.seek(0)

    c1, c2 = st.columns(2)
    c1.download_button("⬇️ CSV", csv, "reviews.csv", "text/csv", use_container_width=True)
    c2.download_button("⬇️ XLSX", xlsx, "reviews.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       use_container_width=True)

    st.subheader("📄 Пример данных")
    st.dataframe(df.head(100), use_container_width=True)
