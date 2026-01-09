import time
import requests
from text_utils import is_russian

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

            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                break

            feed = r.json().get("feed", {})
            entries = feed.get("entry", [])

            if not entries:
                break

            if page == 1:
                entries = entries[1:]

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

    return all_reviews
