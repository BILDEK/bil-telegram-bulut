#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bulut-telegram bot.py — PC'den bağımsız Telegram botu.
GitHub Actions cron ile çalışır; mesajları Gemini ücretsiz API ile yanıtlar.
Secrets env'den gelir (TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, GEMINI_API_KEY).
Offset offset.json'da tutulur ve workflow tarafından commit'lenir.
Anahtar DEĞERLERİ hiçbir yere yazdırılmaz.
"""
import json, os, sys, urllib.request, urllib.error

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = str(os.environ.get("TELEGRAM_CHAT_ID", ""))
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
GEMINI_FALLBACKS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-lite-latest"]
OFFSET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offset.json")

SYS = (
    "Sen Bil'in (Tayyip Bilal T.) kişisel asistanısın. Türkçe, kısa ve pratik yanıt ver. "
    "Bil bir trader ve kişisel yapay-zekâ sistemi geliştiricisi; ücretsiz kaynaklara önem verir, "
    "parasız kısıtlı. OKX futures scalp trading, likidasyon avı, koşullu strateji backtest'i ile ilgilenir. "
    "Bilgisayar kapalıyken bulutta çalışıyorsun; sohbet, analiz, piyasa yorumu ve genel yardım yapabilirsin "
    "ama yerel PC araçlarını/ajan ordusunu çalıştıramazsın. Ahlak dersi verme, nedeni söyle kararı ona bırak. "
    "Para harcama önerme. Emoji kullanma."
)

def api_call(url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def tg(method, **params):
    return api_call(f"https://api.telegram.org/bot{TOKEN}/{method}", params)

def gemini(text):
    payload = {
        "systemInstruction": {"parts": [{"text": SYS}]},
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
    }
    seen = set()
    for model in [GEMINI_MODEL] + GEMINI_FALLBACKS:
        if model in seen:
            continue
        seen.add(model)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
        try:
            d = api_call(url, payload)
            parts = d.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            out = "".join(p.get("text", "") for p in parts).strip()
            if out:
                return out
        except urllib.error.HTTPError as e:
            if e.code in (404, 503, 429):
                continue
            return f"(Gemini hatası {e.code}; sonra tekrar dene)"
        except Exception:
            continue
    return "(şu an yanıt veremiyorum, sonra tekrar dene)"

def load_offset():
    try:
        with open(OFFSET_FILE, encoding="utf-8") as f:
            return int(json.load(f).get("offset", 0))
    except (OSError, ValueError, TypeError):
        return 0

def save_offset(off):
    with open(OFFSET_FILE, "w", encoding="utf-8") as f:
        json.dump({"offset": off}, f)

def main():
    if not TOKEN or not GEMINI_KEY:
        print("Eksik secret (token/gemini); çıkılıyor.")
        return
    off = load_offset()
    try:
        updates = tg("getUpdates", offset=off, timeout=0, allowed_updates=["message"]).get("result", [])
    except Exception as e:
        print("getUpdates hatası:", str(e)[:120])
        return
    new_off = off
    handled = 0
    for u in updates:
        new_off = max(new_off, u["update_id"] + 1)
        msg = u.get("message") or {}
        chat = str((msg.get("chat") or {}).get("id", ""))
        text = (msg.get("text") or "").strip()
        if not text or chat != CHAT_ID:
            continue
        if text in ("/start", "/durum"):
            reply = "Bulut asistan aktif (PC kapalıyken de çalışır). Yazdığın her şeyi Gemini ile yanıtlarım. /rapor = piyasa."
        else:
            reply = gemini(text)
        try:
            tg("sendMessage", chat_id=CHAT_ID, text=reply[:4000])
            handled += 1
        except Exception as e:
            print("sendMessage hatası:", str(e)[:120])
    if new_off != off:
        save_offset(new_off)
    print(f"updates={len(updates)} handled={handled} offset={new_off}")

if __name__ == "__main__":
    main()