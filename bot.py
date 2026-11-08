#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bulut-telegram bot.py — PC'den bağımsız Telegram botu.
GitHub Actions cron ile çalışır; mesajları Gemini ücretsiz API ile yanıtlar.
Secrets env'den gelir; anahtar DEĞERLERİ hiçbir yere yazdırılmaz.
Offset ve şifreli PC kuyruğu workflow tarafından aynı commit'te saklanır.
"""
import json, os, tempfile, time, urllib.request, urllib.error

from pc_protocol import seal_job

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = str(os.environ.get("TELEGRAM_CHAT_ID", ""))
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
GEMINI_FALLBACKS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-lite-latest"]
OFFSET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offset.json")
PC_JOBS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pc_jobs.json")
PC_QUEUE_KEY = os.environ.get("PC_QUEUE_KEY", "")
PC_QUEUE_ENABLED = os.environ.get("PC_QUEUE_ENABLED", "false").lower() == "true"
PC_HELP = (
    "Gecikmeli PC komutları güvenlik için KAPATILDI; iş kuyruğa alınmaz ve çalıştırılmaz.\n"
    "Doğrudan ajan erişimi: PC'de KAYNAK/remote/telefon-baglan.cmd ile eşleştir; "
    "bağlandıktan sonra GitHub kuyruğu kullanılmaz. Tam Windows ekran/fare erişimi değildir.\n"
    "Normal bulut sohbeti devam eder, fakat GitHub zamanlaması nedeniyle gecikebilir. "
    "/rapor bulut Gemini yanıtıdır; canlı veri raporu değildir."
)

SYS = (
    "Sen Bil'in (Tayyip Bilal T.) kişisel asistanısın. Türkçe, kısa ve pratik yanıt ver. "
    "Bil bir trader ve kişisel yapay-zekâ sistemi geliştiricisi; ücretsiz kaynaklara önem verir, "
    "parasız kısıtlı. OKX futures scalp trading, likidasyon avı, koşullu strateji backtest'i ile ilgilenir. "
    "Bulutta çalışıyorsun; sohbet, analiz, piyasa yorumu ve genel yardım yapabilirsin ama kendin yerel "
    "PC araçlarını/ajan ordusunu çalıştıramazsın. Gecikmeli /pc komut kuyruğu tamamen kapatıldı; "
    "yerel iş başlatamazsın. /pc yalnız kapatma bilgisini ve doğrudan ajan bağlantısı yardımını verir. "
    "PC fiziksel kapalıysa yerel işlem yapılamaz. "
    "GitHub cron gecikmesi 5 dakika veya daha uzun olabilir. /rapor yalnız bulut Gemini yanıtıdır. "
    "Gerçek zamanlı veriye erişimin yoksa canlı fiyat, PC durumu veya gerçekleşmiş işlem uydurma; "
    "veri olmadığını açıkça söyle. Yerel komutu çalıştırmış gibi konuşma. "
    "Ahlak dersi verme, nedeni söyle kararı ona bırak. Para harcama önerme. Emoji kullanma."
)

def api_call(url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def tg(method, **params):
    result = api_call(f"https://api.telegram.org/bot{TOKEN}/{method}", params)
    if not result.get("ok"):
        raise RuntimeError("Telegram API isteği başarısız")
    return result


def log_error(operation, error):
    # URL/response/exception metni token veya özel içerik taşıyabilir.
    code = error.code if isinstance(error, urllib.error.HTTPError) else "-"
    print(f"{operation} hatası: {type(error).__name__} http={code}")


def enqueue_pc_job(job):
    try:
        with open(PC_JOBS_FILE, encoding="utf-8") as f:
            queue = json.load(f)
    except FileNotFoundError:
        queue = {"jobs": []}
    jobs = queue.get("jobs") if isinstance(queue, dict) else None
    if not isinstance(jobs, list) or any(
        not isinstance(item, dict) or set(item) != {"id", "payload"}
        or not isinstance(item["id"], str) or not isinstance(item["payload"], str)
        for item in jobs
    ):
        raise ValueError("Geçersiz PC kuyruk biçimi")
    if any(item["id"] == str(job["id"]) for item in jobs):
        return False
    envelope = seal_job(job, PC_QUEUE_KEY)
    jobs = (jobs + [envelope])[-50:]  # Ekleme sırasına göre en eskileri buda.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=os.path.dirname(PC_JOBS_FILE),
            prefix=".pc-jobs-", suffix=".tmp", delete=False,
        ) as f:
            temporary = f.name
            json.dump({"jobs": jobs}, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, PC_JOBS_FILE)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return True


def pc_reply(update, text):
    parts = text.split(None, 2)
    if not parts or parts[0].lower() != "/pc":
        return None
    if not PC_QUEUE_ENABLED:
        return PC_HELP
    command = parts[1].lower() if len(parts) > 1 else "yardim"
    if command in ("yardim", "yardım"):
        return PC_HELP
    actions = {"durum": "status", "rapor": "report", "baglan": "pair", "bağlan": "pair", "ajan": "agent"}
    action = actions.get(command)
    remainder = parts[2].strip() if len(parts) > 2 else ""
    if not action or (action == "agent" and not remainder):
        return PC_HELP
    if not PC_QUEUE_KEY:
        return "PC kuyruğu yapılandırılmamış (PC_QUEUE_KEY eksik); iş eklenmedi."
    created_at = int(time.time())
    message_time = (update.get("message") or {}).get("date", created_at)
    if not isinstance(message_time, int) or created_at - message_time > 600:
        return "Eski PC komutunun süresi dolmuş; çalıştırılmadı. Gerekiyorsa yeniden gönder."
    enqueue_pc_job({
        "id": str(update["update_id"]), "action": action, "text": remainder,
        "chat_id": CHAT_ID, "created_at": created_at, "expires_at": created_at + 600,
    })
    return (
        "PC işi kuyruğa alındı. PC açık ve worker çalışıyorsa sonuç Telegram'a gelir. "
        "PC kapalıysa yerel işlem yapılamaz; iş 10 dakika sonra geçersiz olur ve çalışmaz. "
        "GitHub cron gecikmesi 5 dakika veya daha uzun olabilir."
    )

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
    if not TOKEN or not CHAT_ID:
        print("Eksik secret (token/chat_id); çıkılıyor.")
        return
    off = load_offset()
    try:
        updates = tg("getUpdates", offset=off, timeout=0, allowed_updates=["message"]).get("result", [])
    except Exception as e:
        log_error("getUpdates", e)
        return
    new_off = off
    handled = 0
    for u in updates:
        next_off = max(new_off, u["update_id"] + 1)
        msg = u.get("message") or {}
        chat = msg.get("chat") or {}
        sender = msg.get("from") or {}
        text = (msg.get("text") or "").strip()
        if (not text or str(chat.get("id", "")) != CHAT_ID
                or str(sender.get("id", "")) != CHAT_ID
                or chat.get("type") != "private" or sender.get("is_bot") is not False):
            new_off = next_off
            continue
        try:
            reply = pc_reply(u, text)
        except Exception as e:
            log_error("PC kuyruğu", e)
            break  # İş saklanamadı: bu update'in offset'ini ilerletme, sonraki tur yeniden dene.
        if reply is None:
            if text in ("/start", "/durum"):
                reply = (
                    "Bulut asistan aktif (PC kapalıyken de çalışır). Normal mesajlar Gemini'ye gider. "
                    "Gecikmeli PC komutları kapalı; /pc = doğrudan bağlantı yardımı. /rapor canlı veri değil."
                )
            else:
                reply = gemini(text) if GEMINI_KEY else "Gemini yapılandırılmamış; /pc yardımını kullanabilirsin."
        new_off = next_off
        try:
            tg("sendMessage", chat_id=CHAT_ID, text=reply[:4000])
            handled += 1
        except Exception as e:
            log_error("sendMessage", e)
    if new_off != off:
        save_offset(new_off)
    print(f"updates={len(updates)} handled={handled} offset={new_off}")

if __name__ == "__main__":
    main()