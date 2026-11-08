# Bulut Telegram Asistanı (PC'den bağımsız)

PC kapalıyken bile Telegram'dan mesaj atıp yanıt almanı sağlar. GitHub Actions (ücretsiz, public repo = sınırsız dakika) her 5 dakikada bir Telegram'u yoklar, mesajları **Gemini ücretsiz API** ile yanıtlar.

## Mimari
- `bot.py`: getUpdates → yetkili chat_id mesajlarını Gemini'ye gönder → sendMessage yanıt. Offset `offset.json`'da.
- `.github/workflows/telegram.yml`: cron `*/5 * * * *` + workflow_dispatch. Çalışma sonunda offset'i commit'ler (hem kalıcılık hem repo'yu aktif tutar → 60 gün inaktivite kilidi olmaz).
- Secrets (GitHub'da şifreli): `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `GEMINI_API_KEY`. Repo public olsa da secret'lar görünmez.

## Sınırlar / tradeoff
- GitHub cron en sık **5 dk** → yanıt 5 dk'ya kadar gecikebilir (anlık değil). Anlık gerekirse Cloudflare Worker webhook (ücretsiz, ayrı signup).
- PC kapalıyken bulut Gemini yanıtlar: sohbet/analiz/piyasa yorumu yapar ama **yerel PC araçlarını/ajan ordusunu çalıştıramaz**. PC açıkken tam güç yerel köprüde.
- Çift yanıtı önlemek için: bulut devreye girince PC köprüsünün **gelen mesaj yoklaması (getUpdates) kapatılır**, sadece giden rapor/uyarı kalır.

## Kurulum (bir kere)
1. `gh auth login` — PC tarayıcısında bir kere GitHub login (device flow). Telefondan değil.
2. `deploy.ps1` çalıştır: public repo oluşturur, 3 secret'ı yerel kaynaklardan okuyup stdin ile set eder (değerler ekrana yazılmaz), push'lar, offset'i backlog ötesine ayarlar.
3. PC köprüsünde getUpdates kapatılır (çakışma olmasın).

## Secret kaynakları (değerler hiçbir yere yazılmaz)
- Telegram token + chat_id: `C:\Users\Viole\.config\opencode\telegram.json`
- Gemini: User env `GEMINI_API_KEY`