#!/usr/bin/python3
"""날씨 데이터 (wttr.in, IP 기반 위치). 15분 캐시.

  weather.py --waybar   → waybar custom 모듈용 JSON 한 줄
"""
import datetime
import json
import os
import sys
import time
import urllib.request

CACHE = os.path.expanduser("~/.cache/kyulio-weather.json")
MAX_AGE = 15 * 60

# WWO 날씨 코드 → Nerd Font 아이콘
_ICONS = [
    ({113}, "\U000F0599", "\U000F0594"),                     # 맑음 (낮/밤)
    ({116}, "\U000F0595", "\U000F0F31"),                     # 구름 조금
    ({119, 122}, "\U000F0590", "\U000F0590"),                # 흐림
    ({143, 248, 260}, "\U000F0591", "\U000F0591"),           # 안개
    ({200, 386, 389, 392, 395}, "\U000F0593", "\U000F0593"),  # 뇌우
    ({179, 182, 185, 227, 230, 317, 320, 323, 326, 329, 332, 335, 338,
      350, 362, 365, 368, 371, 374, 377}, "\U000F0598", "\U000F0598"),  # 눈/진눈깨비
    ({299, 302, 305, 308, 356, 359}, "\U000F0596", "\U000F0596"),        # 비(강)
]
ICON_RAIN = "\U000F0597"  # 비(약) — 나머지
ICON_HUMID = "\U000F058E"

DESC_KO = {
    113: "맑음", 116: "구름 조금", 119: "흐림", 122: "흐림", 143: "옅은 안개", 248: "안개", 260: "안개",
    176: "곳에 따라 비", 263: "이슬비", 266: "이슬비", 293: "약한 비", 296: "약한 비", 353: "약한 소나기",
    299: "비", 302: "비", 305: "강한 비", 308: "강한 비", 356: "소나기", 359: "폭우",
    200: "뇌우", 386: "뇌우", 389: "뇌우", 392: "뇌우와 눈", 395: "뇌우와 눈",
    179: "곳에 따라 눈", 227: "날림 눈", 230: "눈보라", 323: "약한 눈", 326: "약한 눈", 329: "눈",
    332: "눈", 335: "많은 눈", 338: "폭설", 368: "약한 눈", 371: "눈", 182: "진눈깨비", 185: "진눈깨비",
    317: "진눈깨비", 320: "진눈깨비", 350: "우박", 362: "진눈깨비", 365: "진눈깨비", 374: "우박", 377: "우박",
}


def icon_for(code, night=False):
    code = int(code)
    for codes, day, nite in _ICONS:
        if code in codes:
            return nite if night else day
    return ICON_RAIN


def _fetch():
    req = urllib.request.Request("https://wttr.in/?format=j1", headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = json.load(r)
    c = raw["current_condition"][0]
    area = raw["nearest_area"][0]
    hour = datetime.datetime.now().hour
    code = int(c["weatherCode"])
    data = {
        "temp": int(c["temp_C"]),
        "feels": int(c["FeelsLikeC"]),
        "humidity": int(c["humidity"]),
        "wind": int(c["windspeedKmph"]),
        "code": code,
        "icon": icon_for(code, night=hour < 6 or hour >= 19),
        "desc": DESC_KO.get(code, c["weatherDesc"][0]["value"]),
        "place": area["areaName"][0]["value"],
        "uv": int(c.get("uvIndex", 0) or 0),
        "pressure": int(c.get("pressure", 0) or 0),
        "visibility": int(c.get("visibility", 0) or 0),
        "precip": float(c.get("precipMM", 0) or 0),
        "sunrise": raw["weather"][0]["astronomy"][0]["sunrise"],
        "sunset": raw["weather"][0]["astronomy"][0]["sunset"],
        "days": [],
        "fetched": time.time(),
    }
    for w in raw["weather"]:
        noon = int(w["hourly"][4]["weatherCode"])
        rain = max(int(h.get("chanceofrain", 0) or 0) for h in w["hourly"])
        data["days"].append({"date": w["date"], "max": int(w["maxtempC"]), "min": int(w["mintempC"]),
                             "code": noon, "icon": icon_for(noon),
                             "desc": DESC_KO.get(noon, w["hourly"][4]["weatherDesc"][0]["value"]),
                             "rain": rain})
    return data


def cached():
    """네트워크 없이 캐시만 즉시 읽기."""
    try:
        with open(CACHE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def is_stale(d):
    return not d or time.time() - d.get("fetched", 0) >= MAX_AGE


def get(force=False):
    cached = None
    try:
        with open(CACHE) as f:
            cached = json.load(f)
    except (OSError, ValueError):
        pass
    if not force and cached and time.time() - cached.get("fetched", 0) < MAX_AGE:
        return cached
    try:
        data = _fetch()
    except Exception:  # noqa: BLE001  네트워크 오류 → 캐시 사용
        return cached
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    tmp = CACHE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, CACHE)
    return data


def waybar():
    d = get()
    if not d:
        print(json.dumps({"text": "", "class": "unavailable", "tooltip": "날씨 정보를 가져올 수 없어요"}))
        return
    text = f"{d['icon']}  {d['temp']}°  {ICON_HUMID} {d['humidity']}%"
    tip = f"{d['place']} · {d['desc']}\n체감 {d['feels']}° · 바람 {d['wind']} km/h"
    print(json.dumps({"text": text, "tooltip": tip, "class": "ok"}, ensure_ascii=False))


if __name__ == "__main__":
    if "--waybar" in sys.argv:
        waybar()
    else:
        print(json.dumps(get(force="--force" in sys.argv), ensure_ascii=False, indent=2))
