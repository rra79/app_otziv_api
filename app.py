import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from scraper import collect_reviews
from analysis_utils import extract_problems_and_pluses
from llm_analysis import llm_analyze

st.set_page_config("App Store Reviews", layout="wide")
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
        st.error("App ID должен содержать только цифры")
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

    st.subheader("📊 Общие метрики")
    st.metric("Средний рейтинг", round(df["rating"].mean(), 2))

    st.subheader("🌍 Рейтинг по регионам")
    st.bar_chart(df.groupby("region")["rating"].mean())

    st.subheader("⭐ Распределение оценок")
    st.bar_chart(df["rating"].value_counts().sort_index())

    problems, pluses = extract_problems_and_pluses(df["review_text"])

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("❌ Проблемы")
        for k, v in problems.most_common(5):
            st.write(f"{k}: {v}")

    with col2:
        st.subheader("✅ Плюсы")
        for k, v in pluses.most_common(5):
            st.write(f"{k}: {v}")

    st.subheader("🤖 LLM-анализ")
    if st.button("Запустить LLM-анализ"):
        sample = "\n".join(df["review_text"].sample(min(40, len(df))))
        st.markdown(llm_analyze(sample))

    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("⬇️ Скачать CSV", csv, "reviews.csv")

    st.dataframe(df.head(50))
