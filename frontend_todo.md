# Frontend TODO (Basit ve Hatasız Akış)

## ✅ Tamamlananlar

- [x] `StatusDashboard` polling tabanlı yapıdan SSE + basit FSM yapısına geçirildi.
- [x] HITL onay sonrası yanlış `interrupted` tekrar görünmesi için `awaiting_resume` aşaması eklendi.
- [x] SSE normal kapanışında gereksiz "Canlı bağlantı kesildi" uyarısı kaldırıldı.
- [x] Backend `start` endpointi: aynı şirket için aktif (`running/interrupted`) thread varsa yeni thread açmak yerine mevcut thread döndürüyor.
- [x] Frontend başlangıç formunda backend mesajı gösteriliyor (yeni başlatıldı / mevcut thread devam ediyor).
- [x] Sayfa yenileme sonrası `activeThreadId` localStorage ile geri yükleniyor.

## 🔄 Sıradaki Basit İyileştirmeler

- [ ] Sol panelde "Son Aktif Thread" kartı (thread id + hızlı devam et).
- [ ] Basit "Geçmiş Analizler" listesi (son 10 thread): company, status, updated_at.
- [ ] `history` endpointi ile şirket bazlı son karar bilgisini StartForm altında göstermek.
- [ ] `StatusDashboard` içinde kullanıcı dostu özet kart: Karar, pending node, loop_step.

## 🧩 Backend Destek Gerekenler (Minimal)

- [ ] `GET /api/v1/analysis/recent` endpointi (tamamlanan + devam eden son thread listesi).
- [ ] `GET /api/v1/analysis/{thread_id}/summary` (UI için hafif özet payload).
- [ ] (Opsiyonel) `status` yanıtına `updated_at` / `last_event_at` eklemek.

## 🚫 Şimdilik Kapsam Dışı

- [ ] PDF yükleme akışı (bilinçli olarak beklemede).
- [ ] Gelişmiş grafik/analitik dashboard (MVP sonrası).
