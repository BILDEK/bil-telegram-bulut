# Bulut Telegram Asistanı

Normal sohbet GitHub Actions + ücretsiz Gemini ile devam eder; PC kapalıyken de çalışabilir. GitHub cron gecikmesi sınırlanamaz; anlık iletişim/finansal kontrol için kullanılmaz.

## PC komutları KAPALI (2026-11-09)

Gecikme kabul edilmediği için `/pc` artık sadece kapatma bilgisini gösterir; yeni iş kuyruklanmaz. Workflow `PC_QUEUE_ENABLED=false` kullanır ve queue anahtarını almaz. PC TelegramKopru süreci worker başlatmaz; yalnız giden raporlar korunmuştur. Eski kuyruk boşaltıldı; protokol testleri tarihsel güvenlik kontrolleridir, etkin servis değildir.

Doğrudan ajan erişimi: PC'de `KAYNAK/remote/telefon-baglan.cmd` çalıştır. Eşleştikten sonra GitHub kuyruğuna girmez; OpenCode/OpenTunnel kullanılır. PC açık/internette olmalı. Tam Windows ekran/fare erişimi değildir. Telefon uçtan uca bağlantısı ayrıca kullanıcı tarafında doğrulanmalıdır.

`/rapor` Gemini yanıtıdır, gerçek zamanlı piyasa raporu değildir. Token ve API anahtarları Actions Secrets içinde; sohbete/repo/loglara yazılmaz.
