import re
import os
import json
import requests
import google.generativeai as genai
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ORS_API_KEY=""
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")



def strip_html(raw):
    return re.sub('<[^<]+?>', '', raw)

def normalize_place_name(place_name):
    # Check if contains Devanagari characters
    if any('\u0900' <= ch <= '\u097F' for ch in place_name):
        # Transliterate Hindi → English (IAST style)
        return transliterate(place_name, sanscript.DEVANAGARI, sanscript.ITRANS)
    return place_name

def geocode_place(place_name):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place_name, "format": "json", "limit": 1}
    headers = {"User-Agent": "ujjain-hackathon-nav-assistant/1.0 (contact: youremail@example.com)"}
    r = requests.get(url, params=params, headers=headers, timeout=10)

    if r.status_code != 200:
        print("Error:", r.status_code, r.text)
        return None

    data = r.json()
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"])

def parse_origin_destination_gemini_ai(user_text):
    system = (
        "You are a helper that extracts origin and destination locations from a short "
        "spoken user query. Return ONLY valid JSON like: "
        "{\"origin\":\"<origin text>\", \"destination\":\"<destination text>\"}. "
        "If you cannot find either, return it as an empty string.\n"
        "User query may be in Hindi or English and might be short and informal."
        "Always return origin and destination names in ENGLISH, even if the input is Hindi."
    )
    prompt = f"{system}\n\nUser utterance: '''{user_text}'''"

    try:
        response = model.generate_content(prompt)
        content = response.text.strip()

        # 🔧 Handle cases where Gemini wraps JSON in ```json ... ```
        if content.startswith("```"):
            content = content.strip("`").replace("json", "").strip()

        # Parse JSON
        json_start = content.find('{')
        json_text = content[json_start:] if json_start != -1 else content
        parsed = json.loads(json_text)

        origin = parsed.get("origin", "").strip()
        destination = parsed.get("destination", "").strip()

        return {"origin": origin, "destination": destination}

    except Exception as e:
        print("gemini_try_exceptblock", str(e))
        # fallback: simple heuristics (naive rule-based)
        txt = user_text.lower()
        if " se " in txt:
            parts = txt.split(" se ", 1)
            origin = parts[0].strip()
            if " to " in parts[1]:
                dest = parts[1].split(" to ", 1)[1]
            else:
                dest = parts[1]
            return {"origin": origin, "destination": dest}
        if " to " in txt:
            parts = txt.split(" to ", 1)
            return {"origin": parts[0].strip(), "destination": parts[1].strip()}
        return {"origin": "", "destination": ""}
    

# Build compact voice-friendly instruction from directions
def get_directions_ors(origin, destination, profile="driving-car"):
    """
    origin, destination = (lat, lon) tuples
    profile = 'foot-walking', 'driving-car', 'cycling-regular', etc.
    """
    url = f"https://api.openrouteservice.org/v2/directions/{profile}"
    headers = {"Authorization": ORS_API_KEY}
    params = {
        "start": f"{origin[1]},{origin[0]}",  # (lng,lat) order required
        "end": f"{destination[1]},{destination[0]}"
    }

    r = requests.get(url, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    if "features" not in data:
        return {"error": "No route found", "raw": data}

    route = data["features"][0]
    seg = route["properties"]["segments"][0]

    steps = []
    for step in seg["steps"]:
        steps.append({
            "instruction": step.get("instruction", ""),
            "distance": f"{step.get('distance', 0):.0f} m",
            "duration": f"{step.get('duration', 0):.0f} sec"
        })

    return {
        "summary": route["properties"].get("summary", {}),
        "total_distance": f"{seg['distance']:.0f} m",
        "total_duration": f"{seg['duration']:.0f} sec",
        "steps": steps
    }


def build_voice_text_ors(directions, max_steps=6):
    if directions.get("error"):
        return f"Maaf kijiye. Route prapt karne mein problem: {directions.get('error')}"

    parts = []
    # ✅ Intro line with summary
    total_distance = directions.get("total_distance", "")
    total_duration = directions.get("total_duration", "")
    parts.append(f"Rasta mil gaya. Kul doori {total_distance} aur samay lagbhag {total_duration}.")

    # ✅ Step-by-step instructions (limited for voice)
    steps = directions.get("steps", [])[:max_steps]
    for i, s in enumerate(steps, start=1):
        instr = s.get("instruction", "")
        dist = s.get("distance", "")
        dur = s.get("duration", "")
        # Make it short + voice-friendly
        parts.append(f"\nKadam {i}: {instr}. Doori {dist}, samay {dur}.")

    # ✅ If more steps exist, tell user they will get SMS
    if len(directions.get("steps", [])) > max_steps:
        parts.append("Aur details ke liye SMS bheja jayega.")

    return " ".join(parts)