import os

def llm_analyze(text: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "LLM-анализ отключён (нет OPENAI_API_KEY)"

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        prompt = f"""
Проанализируй отзывы о мобильном приложении.
Выдели:
1. Основные проблемы
2. Основные плюсы
3. Общую оценку
4. Рекомендации

Отзывы:
{text[:12000]}
"""

        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        return r.choices[0].message.content

    except Exception as e:
        return f"Ошибка LLM-анализа: {e}"
