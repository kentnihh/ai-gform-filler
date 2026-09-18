# AI Google Form Filler

Aplikasi otomatisasi pengisian Google Form menggunakan Playwright dan AI (OpenAI API) untuk menghasilkan jawaban yang realistis, bervariasi, dan konsisten berdasarkan persona responden.

> **Catatan:** Gunakan aplikasi ini hanya pada Google Form milik sendiri atau yang telah memiliki izin pengujian.

## 🚀 Fitur

- **Form Parsing**: Otomatis mengekstrak struktur pertanyaan dan opsi pilihan jawaban.
- **Dynamic Persona Generator**: Menghasilkan profil responden yang unik (usia, pekerjaan, sifat).
- **Context-Aware AI Answers**: Menghasilkan jawaban yang sinkron antar-pertanyaan.
- **Preview & Submit Mode**: Pengujian tanpa melakukan submission langsung.
- **Rate Limiting & Safety**: Mencegah spamming berlebih dengan delay acak.
- **Export Data**: Menyimpan hasil respons ke CSV dan JSON.

## 🛠️ Persyaratan System

- Python 3.10+
- OpenAI API Key

## 📦 Instalasi

1. **Clone repository ini:**
   ```bash
   git clone [https://github.com/user/gform-ai-filler.git](https://github.com/user/gform-ai-filler.git)
   cd gform-ai-filler