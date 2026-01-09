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
st.title("📱 App Store — аналитика отзывов")
st.caption("Apple RSS API • мульти-регионы • дашборды")

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

# ================= CLEAN FOR EXCEL =================
def prepare_for_export(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "review_date" in df.columns:
        df["review_date"] = pd.to_datetime(
            df["review_date"], errors="coerce"
        ).dt.tz_localize(None)

    df = df.fillna("")

    for col in df.columns:
        df[col] = df[col].astype(str)

    if "review_text" in df.columns:
        df["review_text"] = df["review_text"].str.slice(0, 32000)

    return df

# ================= SCRAPER =================
@st.cache_data(show_spinner=False)
def fetch_reviews(app_id: str, regions: tuple):
    all_reviews = []
    seen_ids = set()

    progress = st.progress(0)
    status = st.empty()

    total_steps = len(regions) * 50
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
                    if rid in seen_ids:
                        continue

                    text = e["content"]["label"]

                    all_reviews.append({
                        "review_id": rid,
                        "rating": int(e["im:rating"]["label"]),
                        "review_text": text,
                        "sentiment": sentiment(text),
                        "review_date": e["updated"]["label"],
                        "app_version": e["im:version"]["label"],
                        "region": region.upper()
                    })

                    seen_ids.add(rid)

                step += 1
                progress.progress(min(step / total_steps, 1.0))
                status.write(f"🌍 {region.upper()} • стр. {page}")

                time.sleep(0.05)

            except Exception:
                break

    return pd.DataFrame(all_reviews)

# ================= RUN =================
if START:

    st.session_state.stop = False

    if not APP_ID.isdigit():
        st.error("❌ App ID должен содержать только цифры")
        st.stop()

    if not REGIONS:
        st.error("❌ Выберите хотя бы один регион")
        st.stop()

    with st.spinner("🔄 Сбор отзывов..."):
        df = fetch_reviews(APP_ID, tuple(REGIONS))

    if df.empty:
        st.warning("⚠️ Отзывы не найдены")
        st.stop()

    df.drop_duplicates(subset=["review_id"], inplace=True)

    # ================= DASHBOARD =================
    st.success(f"✅ Собрано отзывов: {len(df)}")

    st.divider()
    st.header("📊 Дашборд")

    # безопасные типы
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")

    c1, c2, c3 = st.columns(3)
    c1.metric("Всего отзывов", len(df))
    c2.metric("Средний рейтинг", round(df["rating"].mean(), 2))
    c3.metric("Регионов", df["region"].nunique())

    st.subheader("⭐ Распределение рейтингов")
    st.bar_chart(df["rating"].value_counts().sort_index())

    st.subheader("💬 Тональность")
    st.bar_chart(df["sentiment"].value_counts())

    st.subheader("🌍 Отзывы по регионам")
    st.bar_chart(df["region"].value_counts())

    st.subheader("📈 Динамика отзывов")
    daily = df.dropna(subset=["review_date"]).groupby(
        df["review_date"].dt.date
    ).size()
    st.line_chart(daily)

    st.subheader("🌎 Средний рейтинг по регионам")
    avg_region = (
        df.dropna(subset=["rating"])
        .groupby("region")["rating"]
        .mean()
        .sort_values()
    )
    st.bar_chart(avg_region)

    # ================= EXPORT =================
    df_export = prepare_for_export(df)

    csv = df_export.to_csv(index=False, encoding="utf-8-sig")

    xlsx = BytesIO()
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False)
    xlsx.seek(0)

    st.divider()
    c1, c2 = st.columns(2)

    c1.download_button(
        "⬇️ Скачать CSV",
        csv,
        "appstore_reviews.csv",
        "text/csv",
        use_container_width=True
    )

    c2.download_button(
        "⬇️ Скачать XLSX",
        xlsx,
        "appstore_reviews.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    st.subheader("📄 Пример данных")
    st.dataframe(df.head(100), use_container_width=True)
