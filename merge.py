import json
import os

# ===== FILE PATHS =====
json1_path = "articles_detailed.json"  # file with full article metadata
json2_path = "topics.json"  # file with topics
output_path = "merged_articles.json"

# ===== LOAD JSON FILES =====
with open(json1_path, "r", encoding="utf-8") as f1:
    articles1 = json.load(f1)

with open(json2_path, "r", encoding="utf-8") as f2:
    data2 = json.load(f2)
    articles2 = data2.get("articles", [])

# ===== BUILD LOOKUP FROM JSON2 =====
topic_lookup = {
    art["title"].strip().lower(): {"topic": art["topic"], "topic_id": art["topic_id"]}
    for art in articles2
}

# ===== MERGE & REMOVE DUPLICATES =====
merged_articles = []
seen_titles = set()

for article in articles1:
    title_key = article["title"].strip().lower()

    # Skip duplicates
    if title_key in seen_titles:
        continue
    seen_titles.add(title_key)

    # Add topic info if available
    if title_key in topic_lookup:
        article["topic"] = topic_lookup[title_key]["topic"]
        article["topic_id"] = topic_lookup[title_key]["topic_id"]
    else:
        article["topic"] = None
        article["topic_id"] = None

    merged_articles.append(article)

# ===== SAVE MERGED JSON =====
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(merged_articles, f, indent=2, ensure_ascii=False)

print(f"✅ Merged {len(merged_articles)} articles saved to '{output_path}'")
