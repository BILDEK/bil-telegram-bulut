# Bulut Telegram Asistanı

GitHub Actions ücretsiz bulut botudur. PC kapalıyken **normal mesajları Gemini** yanıtlar. `/rapor` da Gemini'ye gider; yerel rapor veya gerçek zamanlı piyasa verisi değildir.

## Telegram komutları
- `/pc` veya `/pc yardim`: yardım.
- `/pc durum`: PC durumu (`status`).
- `/pc rapor`: yerel rapor (`report`).
- `/pc baglan`: geçici bağlantı (`pair`).
- `/pc ajan <komut>`: kullanıcının verdiği komutu onayıyla yerel ajana iletir (`agent`). Proje `AGENTS.md` kuralları geçerlidir: para harcama, kişisel dosya silme, yeni açılış/oturum görevi, hesap/parola değişikliği ve credential taraması için gerekli açık onay atlanmaz.

**PC açık ve worker çalışıyorsa** kuyruktaki iş yürütülür, sonuç Telegram'a gelir. PC fiziksel kapalıysa yerel işlem yapılamaz. İş kuyruğa alındıktan **10 dakika sonra geçersiz olur**; süresi dolan iş çalışmaz. GitHub cron `*/5` kullanır; gecikme **5 dakika veya daha uzun** olabilir, anlık erişim garantisi yoktur.

## Mimari ve güvenlik
- `bot.py`: yalnızca yetkili `chat.id` ve `from.id` eşleşen özel sohbet, bot olmayan gönderici. Diğer mesajlar işlenmez.
- `pc_protocol.seal_job(job, key)` işleri Fernet ile doğrulanmış/şifreli zarfa dönüştürür. `pc_jobs.json` biçimi: `{"jobs":[{"id":"...","payload":"..."}]}`. Düzmetin PC komutu, bağlantı veya anahtar repo/log'a yazılmaz. Kuyruk atomik yazılır, aynı update ID yinelenmez, en fazla 50 iş tutulur (en eski budanır).
- `.github/workflows/telegram.yml`: yalnız schedule/manual; PR tetiklemesi yok. Tek eşzamanlı çalışma, `cancel-in-progress: false`. `cryptography` kurulur; `offset.json` ve şifreli kuyruk aynı commit'te saklanır.
- GitHub Secrets: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `GEMINI_API_KEY`, **`PC_QUEUE_KEY`**. PC worker ve bulut aynı kuyruk anahtarını kullanır; anahtar repo'ya konmaz.
- Telegram gelen mesajlarını yalnız bulut yoklar; PC köprüsü giden rapor/uyarı için kalır. Worker getUpdates kullanmaz.

Yerel worker ayrıca çalıştırılmalıdır. Bu değişiklik yeni boot/login görevi kurmaz. Kuyruk dosyası public olsa da komut içeriği şifrelidir; ID, kuyruk boyutu ve commit zamanları görülebilir.
