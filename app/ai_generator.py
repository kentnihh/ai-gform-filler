import json
import time
import random
from typing import List
from openai import OpenAI
from app.models import Question, Persona, RespondentData, QuestionType
from config import Config
from app.logger import logger

PHONE_PREFIXES = ["811", "812", "813", "821", "822", "823", "852", "853", "857", "858", "877", "878", "881", "882", "883", "895", "896", "897", "898", "899"]
EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "icloud.com", "protonmail.com"]

def generate_phone_number() -> str:
    prefix = random.choice(PHONE_PREFIXES)
    suffix = "".join(str(random.randint(0, 9)) for _ in range(7))
    return f"0{prefix}{suffix}"

def generate_email(name: str) -> str:
    slug = "".join(c for c in name.lower().replace(" ", ".") if c.isalnum() or c == ".")
    slug = slug.strip(".") or "user"
    domain = random.choice(EMAIL_DOMAINS)
    return f"{slug}{random.randint(1, 999)}@{domain}"

class AIAnswerGenerator:
    def __init__(self):
        # Jika menggunakan Groq API
        if Config.OPENAI_API_KEY.startswith("gsk_"):
            self.client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=Config.OPENAI_API_KEY
            )
        else:
            self.client = OpenAI(api_key=Config.OPENAI_API_KEY)

    def generate_answers(self, respondent_id: int, persona: Persona, questions: List[Question]) -> RespondentData:
        prompt_data = {
            "persona": persona.model_dump(),
            "questions": [
                {
                    "id": q.id,
                    "title": q.title,
                    "description": q.description,
                    "type": q.type.value,
                    "options": q.options,
                    "required": q.required
                }
                for q in questions
            ]
        }

        system_prompt = (
            "Anda adalah sistem generator responden survei yang realistis.\n"
            "Tugas Anda adalah membuat jawaban yang konsisten dan natural berdasarkan profil persona yang diberikan.\n"
            "Aturan ketat:\n"
            "1. Jika pertanyaan memiliki pilihan terbatas (multiple_choice, dropdown, checkboxes, linear_scale), JAWABAN HARUS PERSIS SAMA dengan salah satu (atau beberapa untuk checkboxes) string dari array 'options' yang disediakan.\n"
            "2. Jangan mengarang pilihan yang tidak ada dalam daftar 'options'.\n"
            "3. Untuk tipe 'checkboxes', jawaban harus berupa list/array dari string opsi.\n"
            "4. Jaga konsistensi logika antar-jawaban.\n"
            "5. Kembalikan HANYA JSON valid dengan format: {\"answers\": {\"q_1\": \"jawaban1\", \"q_2\": \"jawaban2\"}}\n"
            "6. WAJIB: baca ulang setiap 'options' pada tiap pertanyaan SEBELUM menjawab. Jangan gunakan jawaban generik seperti 'Cukup baik' untuk pertanyaan yang memiliki daftar 'options' (multiple_choice, checkboxes, dropdown) — jawaban tersebut HARUS berupa salah satu string persis dari 'options' pertanyaan itu, bukan dari pertanyaan lain."
        )

        user_prompt = f"Hasilkan jawaban untuk formulir ini dalam format JSON:\n{json.dumps(prompt_data, ensure_ascii=False, indent=2)}"

        for attempt in range(Config.MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=Config.MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7
                )
                content = response.choices[0].message.content

                parsed_json = json.loads(content)
                answers = parsed_json.get("answers", parsed_json)

                cleaned_answers = {}
                for q in questions:
                    val = answers.get(q.id) or answers.get(q.title)

                    if q.options:
                        if q.type == QuestionType.CHECKBOXES:
                            val_list = val if isinstance(val, list) else ([val] if val else [])
                            val = [v for v in val_list if v in q.options] or None
                        else:
                            if val not in q.options:
                                val = None

                    if val is None and q.required:
                        if q.options:
                            val = q.options[0] if q.type != QuestionType.CHECKBOXES else [q.options[0]]
                        else:
                            val = "Cukup baik"
                    cleaned_answers[q.id] = val

                # Override nama-nama field kontak dengan generator lokal (lebih realistis & variatif)
                name_value = None
                for q in questions:
                    if "nama" in q.title.lower():
                        name_value = cleaned_answers.get(q.id)
                        break
                name_value = name_value or "User"

                for q in questions:
                    title_lower = q.title.lower()
                    if any(k in title_lower for k in ["telepon", "no. hp", "nomor hp", "whatsapp", "wa "]):
                        cleaned_answers[q.id] = generate_phone_number()
                    elif "email" in title_lower:
                        cleaned_answers[q.id] = generate_email(name_value)

                return RespondentData(
                    respondent_id=respondent_id,
                    persona=persona,
                    answers=cleaned_answers
                )

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} gagal memanggil AI API: {str(e)}")
                time.sleep(2 ** attempt)

        raise RuntimeError(f"Gagal menghasilkan jawaban AI setelah {Config.MAX_RETRIES} percobaan.")