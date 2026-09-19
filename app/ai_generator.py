import json
import random
import numpy as np
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from ollama import Client
from app.models import Question, Persona, RespondentData, QuestionType
from config import Config
from app.logger import logger
from faker import Faker

fake = Faker('id_ID')

class AIAnswerGenerator:
    """Handles the batch generation of answers using Ollama API."""
    
    def __init__(self) -> None:
        """Initializes the Ollama client based on config."""
        self.client = Client(host=Config.OLLAMA_BASE_URL, timeout=60.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Calls the Ollama LLM with a system and user prompt."""
        try:
            response = self.client.chat(
                model=Config.MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                format="json",
                options={"temperature": 0.85}
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"Ollama API Error during _call_llm: {e}")
            raise e

    def generate_batch_answers(self, personas: List[Persona], questions: List[Question]) -> List[RespondentData]:
        """Generates answers for a batch of personas."""
        llm_questions = [q for q in questions if q.type != QuestionType.LINEAR_SCALE]
        stat_questions = [q for q in questions if q.type == QuestionType.LINEAR_SCALE]

        # 1. Ask LLM for non-Likert questions in a batch
        prompt_data = {
            "questions": [
                {
                    "id": q.id,
                    "title": q.title,
                    "description": q.description,
                    "type": q.type.value,
                    "options": q.options,
                    "required": q.required
                }
                for q in llm_questions
            ],
            "personas": [
                {"idx": idx, "profile": p.model_dump()} for idx, p in enumerate(personas)
            ]
        }

        system_prompt = (
            "Anda adalah asisten AI yang mensimulasikan respons untuk sekelompok responden survei.\n"
            "Tugas Anda adalah menghasilkan list jawaban (answers) untuk masing-masing responden (persona) yang diberikan.\n"
            "Aturan ketat:\n"
            "1. Jika pertanyaan memiliki pilihan terbatas, JAWABAN HARUS PERSIS SAMA dengan salah satu string dari array 'options'.\n"
            "2. Untuk tipe 'checkboxes' (array/list), Anda WAJIB memilih HANYA 1 atau 2 item secara acak. JANGAN PERNAH memilih semua opsi yang tersedia.\n"
            "3. Untuk tipe pertanyaan teks bebas/paragraf, Anda WAJIB menghasilkan jawaban yang SANGAT unik, realistis, dan beragam berdasarkan persona. JANGAN PERNAH mengulang jawaban standar seperti 'Cukup baik'. Sebagian responden harus mengeluh detail (misal: parkir susah, pelayanan lambat, harga mahal, meja kotor), sebagian memberi pujian spesifik, dan sebagian memberi saran konstruktif. Buat senyata mungkin seperti ulasan pelanggan Indonesia.\n"
            "4. Output HARUS BERUPA JSON Object dengan key 'batch_answers' yang berisi array of object.\n"
            "5. Setiap object di dalam array 'batch_answers' harus memiliki key 'idx' yang sesuai dengan idx persona, dan key 'answers' berisi jawaban dari form.\n"
            f"6. SANGAT PENTING: Setiap 'answers' object WAJIB memiliki SEMUA {len(llm_questions)} key pertanyaan berikut: {[q.id for q in llm_questions]}. JANGAN PERNAH melewatkan atau menghilangkan key manapun.\n"
            "7. DILARANG KERAS menghasilkan jawaban yang terpotong, tidak lengkap, atau kosong.\n"
            "Format Output yang Diharapkan:\n"
            "{\n"
            "  \"batch_answers\": [\n"
            "    {\n"
            "      \"idx\": 0,\n"
            "      \"answers\": {\n"
            "        \"q_1\": \"Sangat Setuju\",\n"
            "        \"q_2\": \"Harga terjangkau, tapi Wi-Fi sering putus saat saya nugas.\"\n"
            "      }\n"
            "    },\n"
            "    {\n"
            "      \"idx\": 1,\n"
            "      \"answers\": {\n"
            "        \"q_1\": \"Tidak Setuju\",\n"
            "        \"q_2\": \"Pelayanan staf sangat lambat dan area parkir mobil terlalu sempit untuk tamu bisnis.\"\n"
            "      }\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "PASTIKAN: Rating kuantitatif (q_1) SEJALAN dengan teks ulasan (q_2). Jika rating buruk, teks harus berisi komplain. Sesuaikan gaya bahasa dengan persona (misal: mahasiswa lebih santai, profesional lebih formal)."
        )

        user_prompt = f"Hasilkan batch jawaban untuk form ini:\n{json.dumps(prompt_data, ensure_ascii=False)}"

        batch_responses = {}
        if llm_questions:
            try:
                content = self._call_llm(system_prompt, user_prompt)
                
                # Sanitize the output to remove markdown code blocks
                clean_content = content.strip()
                if clean_content.startswith("```"):
                    clean_content = clean_content.split("\n", 1)[-1]
                if clean_content.endswith("```"):
                    clean_content = clean_content.rsplit("\n", 1)[0]
                clean_content = clean_content.strip()

                parsed_json = json.loads(clean_content)
                batch_array = parsed_json.get("batch_answers", [])
                
                for item in batch_array:
                    idx = item.get("idx")
                    answers = item.get("answers", {})
                    
                    cleaned_answers = {}
                    for q in llm_questions:
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
                        
                    batch_responses[idx] = cleaned_answers
                    
            except Exception as e:
                logger.error(f"Gagal generate LLM batch answers: {e}")
                # Fallback: empty answers if LLM totally fails on this batch
                pass

        # 2. Process all personas and create RespondentData objects
        results = []
        for idx, persona in enumerate(personas):
            answers = batch_responses.get(idx, {})
            
            # Programmatically generate Likert scale for this persona
            for q in stat_questions:
                if not q.options:
                    continue
                try:
                    num_options = [int(opt) for opt in q.options if opt.isdigit()]
                    if num_options:
                        min_val, max_val = min(num_options), max(num_options)
                        scale_range = max_val - min_val
                        mapped_score = min_val + ((persona.latent_score - 1) / 4.0) * scale_range
                        
                        generated_val = int(round(np.random.normal(loc=mapped_score, scale=0.6)))
                        generated_val = max(min_val, min(max_val, generated_val))
                        answers[q.id] = str(generated_val)
                    else:
                        answers[q.id] = random.choice(q.options)
                except Exception as e:
                    answers[q.id] = random.choice(q.options)

            # Override personal fields
            for q in questions:
                title_lower = q.title.lower()
                if any(k in title_lower for k in ["nama", "name", "lengkap"]):
                    answers[q.id] = persona.name
                elif "email" in title_lower:
                    answers[q.id] = persona.email
                elif any(k in title_lower for k in ["telepon", "no. hp", "nomor hp", "whatsapp", "wa "]):
                    answers[q.id] = "08" + "".join([str(random.randint(0, 9)) for _ in range(random.randint(8, 12))])

            # The respondent_id inside the batch will be updated outside by the main loop
            results.append(RespondentData(
                respondent_id=0,
                persona=persona,
                answers=answers
            ))
            
        return results