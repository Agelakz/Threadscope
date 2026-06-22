# 🚀 ThreadScope — Threads × Shopee Affiliate Automation Bot

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg) ![Playwright](https://img.shields.io/badge/Playwright-Browser%20Automation-orange.svg) ![Groq](https://img.shields.io/badge/Groq-llama--3.3--70b-purple.svg) ![Gemini](https://img.shields.io/badge/Gemini-AI%20Fallback-blue.svg)

---

## 👀 Apaan Nih?

**ThreadScope** itu bot otomasi super *smooth* yang tugasnya nyekrol timeline Threads, baca konteks postingan, dan **nge-reply layaknya manusia beneran** (bukan bot sales cringe). 

Kalo post-nya bahas barang yang ada hubungannya sama katalog Shopee (misal gadget atau *fashion*), bot ini bakal nyelipin link affiliate lu secara *smooth* parah. Kalo ga nyambung? Ya dia nimbrung asik aja biar akun lu tetep *engaging*.

**Flow-nya:** `Scroll Timeline ➡️ Pahami Konteks ➡️ Cek Intent ➡️ AI Generate Komen Gaul ➡️ Reply (+ Link kalo nyambung)`

---

## 🧠 Kenapa Dibikin Gini?

Awalnya bot ini nyoba login otomatis, tapi Meta galak banget bos, ada *trust-layer* yang nge-block semua usaha bot. Jadi, solusinya kita pake **Session-First**. Bot ini jalan pake *cookie* dari browser lu yang udah login. *No retry loop* ribet, *no* ke-block waktu login. Aman, cepet, dan stabil.

---

## ✨ Fitur-Fitur Kece

- **Session Injection:** Pake cookie browser biar ga perlu repot tembusin login Meta.
- **LLM Combo (Groq + Gemini):** Pake Groq (Llama 3) buat speed & hemat, kalo nyangkut langsung *fallback* ke Gemini. *Auto key rotation* jalan terus!
- **Anti-AI Writing Layer:** Udah di-prompt *engineering* habis-habisan biar gak kedengeran kayak robot (no "sangat menarik", "terima kasih infonya"). Bahasanya santai, kadang typo dikit biar *real* human.
- **Trend Affiliate Mode:** Bisa disetting buat nyari post yang lagi *viral* (30+ likes) buat maksimalkan cuan affiliate.
- **Auto Post:** Bisa bikin *organic post* tiap 48 jam biar akun lu keliatan aktif.

---

## 🛠️ Setup & Instalasi

Gampang kok, tinggal copas ini di terminal:

```bash
# 1. Clone & masuk folder
git clone <repo-url>
cd Threadscope

# 2. Bikin virtual env
python -m venv venv
# Aktifin env-nya (Windows: venv\Scripts\activate | Mac/Linux: source venv/bin/activate)

# 3. Install semua kebutuhan
pip install -r requirements.txt
pip install playwright
python -m playwright install chromium

# 4. Siapin config
cp .env.example .env
```

---

## 🛒 Ganti Link Shopee Punya Lu Sendiri

Biar cuannya masuk ke kantong lu (bukan ke kantong *developer*), lu **wajib** ganti data produk di file `shopee_affiliate_links.json`. 

Buka file-nya, terus ganti *link-link* yang ada di situ pake *custom link affiliate* Shopee lu sendiri. Formatnya JSON biasa, lu tinggal sesuaikan nama produk, *keyword*, sama URL-nya. Kalo ngga diganti, ntar yang dapet komisi orang lain dong! 💸

---

## ⚙️ Konfigurasi `.env`

Buka `.env` dan isi ini:

```env
# 🍪 Session Cookies (Ambil dari F12 > Application > Cookies di instagram.com/threads.net)
THREADS_SESSION_ID=
THREADS_CSRF_TOKEN=
THREADS_DS_USER_ID=
THREADS_MID=
THREADS_IG_DID=

# 🤖 API Keys (Bisa isi banyak biar ganti-gantian)
GEMINI_API_KEY_1=
GROQ_API_KEY_1=

# 🎛️ Mode Setting
APP_MODE=trend_affiliate      # Pilih: normal | affiliate | trend_affiliate
ENGAGEMENT_MODE=ADVANCED      # Pilih: ADVANCED (2x mikir) | FAST (1x sat set)
```

**Note:** Kalo session *expired*, lu tinggal login ulang di browser dan copas cookie yang baru.

---

## 🎮 Cara Main (Mode Bot)

Lu bisa atur kelakuan bot lewat `.env`:

### 1. `APP_MODE` (Strategi)
- `normal`: Cuma komen biasa buat *engagement* (cocok buat manasin akun baru).
- `affiliate`: Komen + 50% chance nyelipin link kalo nyambung sama produk Shopee.
- `trend_affiliate`: **Paling Agresif 🔥** Nyari post viral doang dan *wajib* nyelipin link.

### 2. `ENGAGEMENT_MODE` (Cara AI Mikir)
- `ADVANCED`: AI mikir 2x (Cek konteks dulu, baru nulis komen). Hasil lebih natural tapi boros token.
- `FAST`: AI mikir 1x langsung gas komen + link. Hemat kuota API.

---

## 🚀 Cara Jalanin

Kalo semua udah siap, pilih mode yang mau lu jalanin:

1. **Jalanin Bot Utama (Komen & Affiliate):**
   ```bash
   python auto_commenter.py
   ```
   *(Dia bakal nge-reply, lalu tidur belasan menit biar ga disangka bot)*

2. **Jalanin Bot Posting (Biar akun idup):**
   ```bash
   python threads_poster.py
   ```

3. **Risert Endpoint/Network:**
   ```bash
   python main.py
   ```

---

## 🏗️ Arsitektur Sistem (Behind the Scenes)

Biar lu tau gimana jeroan bot ini kerja:

```text
┌──────────────────────────────────────────────────────────────────┐
│                         Entry Points                             │
│           main.py  │  auto_commenter.py  │  threads_poster.py   │
└──────────────────────┬───────────────────────────────────────────┘
                       │
         ┌─────────────┼──────────────────────────┐
         ▼             ▼                          ▼
   ┌───────────┐  ┌──────────────┐        ┌─────────────────┐
   │  Session  │  │  LLM Router  │        │  Affiliate      │
   │  Manager  │  │              │        │  Strategy       │
   │           │  │ 1. Groq      │        │                 │
   │ load()    │  │    llama-70b │        │ find_product()  │
   │ validate()│  │ 2. Gemini    │        │ gen_comment()   │
   │ inject()  │  │    fallback  │        │ gen_thread()    │
   └───────────┘  └──────────────┘        └─────────────────┘
         │
         ▼
   ┌───────────────────────────────┐
   │  services/                    │
   │  ├── session_manager.py       │  ← Validasi + inject cookies
   │  ├── network_discovery.py     │  ← Playwright traffic capture
   │  ├── feed_explorer.py         │  ← HTML endpoint discovery
   │  ├── affiliate_strategy.py    │  ← Product matching + AI gen
   │  └── shopee_generator.py      │  ← Link affiliate generator
   └───────────────────────────────┘
```

**Kenapa harus "Session-First"?**  
Awalnya nyoba pake bot login otomatis biasa, eh gagal total kena *trust-layer* Meta yang super protektif. Kalo *legacy login* isinya *retry loop* yang muter-muter bikin pusing, sekarang pake *session-first* (ngambil *cookie* dari browser lu). Jauh lebih stabil, *error*-nya gampang di-*trace*, dan bisa *bypass* sistem *anti-bot* Meta dengan *smooth*.

---

## 📊 Status & Progress Fitur

Secara keseluruhan, sistem *core*-nya udah kelar semua 💯. 

- ✅ **Session Management:** Bypass mode + inject cookie jalan lancar.
- ✅ **Timeline Fetcher:** Narik feed lewat GraphQL mulus.
- ✅ **Auto Reply & Auto Post:** 100% fungsional, ada jeda waktu biar keliatan natural.
- ✅ **AI Engine (Groq + Gemini):** LLM Router jalan, ganti *key* otomatis kalo limit.
- ✅ **Anti-AI Writing:** Komentar ala netizen + anti bahasa *cringe*.
- ✅ **Trend Affiliate Mode:** Otomatis nargetin post viral.
- 🚧 **Multi-Session Support:** Belum dibikin (0%). Nanti rencananya bisa rotasi banyak akun.
- 🚧 **Web Dashboard:** Masih angan-angan (0%).

---

## 🧠 LLM Stack & Output

| Model | Peran | Alasan |
|-------|-------|--------|
| **Groq** (`llama-3.3-70b`) | Primary | Super ngebut dan gratisan boss! |
| **Google** (`gemini-3.5-flash`) | Fallback | Kalo Groq lagi ngambek atau limit. |

*Bot ini otomatis gonta-ganti API key kalo kena limit.*

**File-file penting hasil output bot:**
- `stats.json` ➡️ Rekap sukses/error bot lu.
- `network_capture.json` ➡️ Tangkepan request GraphQL.
- `gemini_cache.json` ➡️ Cache 24 jam biar ngga buang-buang token.

---

## 📖 Riwayat *Development* (Dari Nol ke Suhu)

- **Fase 0 (Ide Awal):** Pengen nyambungin obrolan di Threads sama *link affiliate* Shopee.
- **Fase 1-2 (Tragedi Login):** Coba login otomatis via HTTP, eh ketolak mentah-mentah sama Meta. Bikin `LoginRejectionClassifier` eh tetep diblokir.
- **Fase 3 (Arsitektur Session-First):** Pencerahan dateng! Pake session *cookie* lu dari browser, dan sukses nge-bypass Meta.
- **Fase 4 (Network Discovery):** Riset *endpoint* GraphQL Threads pake Playwright gara-gara Threads ngga punya public API.
- **Fase 5 (AI Engine):** Bikin LLM router (Groq -> Gemini) dan *prompt engineering* habis-habisan biar AI-nya nulis kayak *Gen-Z* Indo yang doyan *scrolling*.
- **Fase 6 (Affiliate Engine):** Nyocokin kata kunci postingan sama *database* produk Shopee tanpa *delay* panjang.
- **Fase 7 (Trend Mode - Current):** Bot jadi makin pinter, nargetin postingan viral doang biar peluang klik makin gede!
- **Fase 8 (To-Do):** *Next level*, pengen nambahin rotasi multi-akun, post pake gambar, dan UI *dashboard* cuan.

---

## ⚠️ Disclaimer PENTING

Bot ini murni buat **riset dan edukasi**. 
- Kalo lu pake buat barbar dan akun lu kena suspend, itu **tanggung jawab lu sendiri**. 
- Selalu patuhi ToS Meta & Shopee ya *guys*. *Use at your own risk!*

---

*Stay humble, keep grinding, and let the bot do the affiliate work! 💸*
