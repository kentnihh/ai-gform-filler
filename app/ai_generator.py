import json
import time
from typing import List, Dict, Any
from openai import OpenAI
from app.models import Question, Persona, RespondentData, QuestionType
from config import Config
from app.logger import logger

class AIAnswerGenerator:
    def __init__(self):
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
            "4. Jaga konsistensi logika antar-jawaban (misal: persona kritis memberikan rating rendah dan alasan evaluatif).\n"
            "5. Kembalikan JSON valid sesuai format schema."
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
                    temperature=0.8
                )

                content = response.choices[0].message.content
                parsed_json = json.loads(content)
                answers = parsed_json.get("answers", {})

                # Format ulang jika key dari AI tidak sesuai ID
                cleaned_answers = {}
                for q in questions:
                    val = answers.get(q.id) or answers.get(q.title)
                    if val is None and q.required:
                        if q.options:
                            val = q.options[0] if q.type != QuestionType.CHECKBOXES else [q.options[0]]
                        else:
                            val = "Cukup baik"
                    cleaned_answers[q.id] = val

                return RespondentData(
                    respondent_id=respondent_id,
                    persona=persona,
                    answers=cleaned_answers
                )

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} gagal memanggil AI API: {str(e)}")
                time.sleep(2 ** attempt)

        raise RuntimeError(f"Gagal menghasilkan jawaban AI setelah {Config.MAX_RETRIES} percobaan.")