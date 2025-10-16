import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "boer_war_personas_memory_expanded.json"

with open(DATA, "r", encoding="utf-8") as f:
    corpus = json.load(f)

keep_ids = {
    "british_soldier_arthur_jennings",
    "boer_commando_jan_du_preez",
    "afrikaner_woman_camp_anna_van_der_merwe",
    "black_man_with_boers_daniel_kgoathe",
}

corpus["personas"] = [p for p in corpus["personas"] if p["persona_id"] in keep_ids]
with open(DATA, "w", encoding="utf-8") as f:
    json.dump(corpus, f, ensure_ascii=False, indent=2)

print("Updated personas file:", DATA)
