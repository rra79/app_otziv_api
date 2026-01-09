import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

from scraper import collect_reviews
from analysis_utils import extract_problems_and_pluses

st.set_page_config(page_title="App Store Reviews", layout="wide")
st.title("📱 Анализ отзывов App Store")

APP_ID = st.text_input("App ID (только цифры)")
REGIONS = st.multiselect(
    "Регионы",
    ["ru", "us", "kz", "ua", "by", "de", "fr"],
    default=["ru"]
)

if "stop" not in st.session_state:
    st.session_state.stop = False

col1, col2 = st.columns(2)
with col1:
    start = st.button("🚀 Начать сбор")
with col2:
    stop = st.button("🛑 Остановить")
    if stop:
        st.session_state.stop = True

def stop_flag():
    return st.session_state.stop

@st.cache_data(show_spinner=False)
def load_data(app_id, regions):
    return collect_reviews(app_id, regions, stop_flag)

if start:
    st.session_state.stop = False

    if not APP_ID.isdigit():
        st.error("❌ App ID должен содержать только цифры")
        st.stop()

    with st.spinner("Сбор отзывов..."):
        data = load_data(APP_ID, tuple(REGIONS))

    if not data:
        st.warning("Нет данных")
        st.stop()

    df = pd.DataFrame(data).drop_duplicates("review_id")
    df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

    st.success(f"Собрано отзывов: {len(df)}")

    # ===== Метрики =====
    st.subheader("📊 Общие метрики")
    st.metric("Средний рейтинг", round(df["rating"].mean(), 2))

    st.subheader("🌍 Средний рейтинг по регионам")
    st.bar_chart(df.groupby("region")["rating"].mean())

    st.subheader("⭐ Распределение оценок")
    st.bar_chart(df["rating"].value_counts().sort_index())

    # ===== Анализ =====
    problems, pluses = extract_problems_and_pluses(df["review_text"])

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("❌ Основные проблемы")
        for k, v in problems.most_common(5):
            st.write(f"{k}: {v}")

    with col2:
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

    st.subheader("🔎 Пример отзывов")
    st.dataframe(df.head(50))
