import json
import random
import numpy as np
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import OpenAI
from app.models import Question, Persona, RespondentData, QuestionType
from config import Config
from app.logger import logger
from faker import Faker

fake = Faker('id_ID')

# Jawaban fallback beragam dan natural khas responden Indonesia (Anti-AI Slop, tanpa em-dash)
HUMAN_FALLBACK_ANSWERS = [
    "Pelayanan ramah dan tempatnya bersih.",
    "Rasa makanan oke, tapi waktu tunggu pesanan agak lama pas jam sibuk.",
    "Porsi pas dan harga terjangkau di kantong.",
    "Kebersihan meja tolong lebih dijaga setelah tamu selesai makan.",
    "Enak bgt, sambelnya mantap. Pertahankan rasanya.",
    "Tempatnya nyaman buat santai, cuma parkir mobil agak susah.",
    "Semua sudah baik, belum ada komplain.",
    "Kasirnya tolong ditambah atau dipercepat antriannya pas lagi rame.",
    "Rasa lumayan enak, cuma AC di ruangan kurang dingin.",
    "Pilihan menu cukup variatif dan rasa konsisten.",
    "Pelayanannya cepat dan stafnya responsif.",
    "Ayamnya empuk bumbunya meresap, recommended.",
    "Toilet dan wastafel tolong lebih rutin dibersihkan.",
    "Oke ga ada kendala, pengalaman makan memuaskan.",
    "Porsinya ngenyangin, staf ramah.",
    "Makanannya enak, tempat ber-AC nyaman buat kumpul keluarga.",
]

def sanitize_human_text(text: str) -> str:
    """Membersihkan teks agar bebas dari AI-slop (em dash, markdown bold, quotes)."""
    if not isinstance(text, str):
        return text
    # R-02: Ganti em-dash dan double-dash dengan koma
    clean = text.replace("—", ", ").replace("--", ", ").replace("**", "").strip()
    if (clean.startswith('"') and clean.endswith('"')) or (clean.startswith("'") and clean.endswith("'")):
        clean = clean[1:-1].strip()
    return clean

class AIAnswerGenerator:
    """Handles the batch generation of answers via OpenAI-compatible API (Ollama/9Router)."""

    def __init__(self) -> None:
        """Initializes the OpenAI-compatible client based on config."""
        self.client = OpenAI(base_url=Config.LLM_BASE_URL, api_key=Config.LLM_API_KEY or "not-needed")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Calls the LLM with a system and user prompt."""
        try:
            response = self.client.chat.completions.create(
                model=Config.MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.85,
                timeout=300.0
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM API Error during _call_llm: {e}")
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
            "Anda adalah mesin simulasi responden manusia untuk survei Google Form di Indonesia.\n"
            "Tugas Anda: Menghasilkan jawaban (answers) untuk masing-masing responden (persona) secara realistis, hidup, dan natural.\n\n"
            "=== ATURAN FORMAT DATA ===\n"
            "1. Pilihan Terbatas: Jika pertanyaan memiliki 'options', JAWABAN HARUS PERSIS SAMA dengan salah satu string di array 'options'.\n"
            "2. Checkboxes: WAJIB pilih HANYA 1 atau 2 item secara acak realistis. JANGAN PERNAH memilih semua opsi.\n"
            "3. Output HARUS JSON Object valid dengan root key 'batch_answers' berisi array of object:\n"
            "   [{\"idx\": 0, \"answers\": {\"q_1\": \"...\", \"q_2\": \"...\"}}]\n"
            f"4. SANGAT PENTING: Setiap objek 'answers' WAJIB menyertakan SEMUA {len(llm_questions)} key pertanyaan berikut: {[q.id for q in llm_questions]}.\n\n"
            "=== ATURAN ANTI-AI SLOP (WAJIB DITERAPKAN) ===\n"
            "Jawaban teks bebas/paragraf TIDAK BOLEH terbaca seperti buatan AI. Terapkan prinsip berikut:\n"
            "- DILARANG KERAS menggunakan tanda em dash (— atau --). Gunakan tanda koma, titik, atau tanda kurung biasa.\n"
            "- DILARANG menggunakan kata-kata klise AI / PR korporat: 'menghadirkan pengalaman luar biasa', 'sinergi', 'revolusioner', 'harmonis', 'ekosistem', 'patut diapresiasi', 'menjadi bukti nyata', 'tak tertandingi', 'secara keseluruhan sangat memuaskan'.\n"
            "- DILARANG memakai salam pembuka klise ('Sejujurnya menurut saya...', 'Jujur saja...') dan DILARANG memakai salam penutup chatbot ('Semoga masukan ini bermanfaat', 'Terima kasih atas pelayanannya', 'Semoga makin sukses!'). Manusia asli langsung to the point menulis isi ulasan.\n"
            "- DILARANG formula 'Rule of Three' (memaksakan 3 pujian/keluhan klise seperti 'cepat, bersih, dan ramah'). Fokus pada 1 atau 2 aspek konkret saja.\n"
            "- HINDARI jawaban seragam. Variasikan panjang dan gaya bahasa sesuai persona:\n"
            "  * Usia muda / Mahasiswa: santai, wajar memakai kata sehari-hari (tp, bgt, ga, udah, nunggu) atau kalimat ringkas ('enak bgt porsi pas', 'tempat cozy tp wifi agak lemot').\n"
            "  * Usia dewasa / Pekerja / ASN: kalimat lebih tertata rapi, sopan, to-the-point ('Kualitas makanan baik, mohon kebersihan wastafel ditingkatkan.').\n"
            "  * Trait 'Kritis & Detail': berikan komplain atau masukan pada hal fisik spesifik (antrean kasir, pendingin ruangan/AC, parkiran sempit, rasa bumbu, kebersihan meja).\n"
            "  * Trait 'Cepat Puas' / 'Netral': komentar singkat, padat, tidak bertele-tele ('Sudah cukup baik', 'Makanannya enak, ga ada kendala').\n"
            "- DILARANG memakai format markdown seperti **teks tebal**, bullet points, atau tanda kutip di jawaban teks bebas.\n"
            "- KONSISTENSI: Rating kuantitatif dan isi ulasan teks harus sejalan secara logis."
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
                                if q.type == QuestionType.CHECKBOXES:
                                    # ponytail: uniform random; weight by real distribution when known
                                    val = random.sample(q.options, min(len(q.options), random.randint(1, 2)))
                                else:
                                    val = random.choice(q.options)
                            else:
                                val = random.choice(HUMAN_FALLBACK_ANSWERS)
                        elif isinstance(val, str) and not q.options:
                            val = sanitize_human_text(val)
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

            # Fallback untuk soal non-stat saat batch LLM gagal total (P0: jawaban hilang)
            # ponytail: uniform random; weight by real distribution when known
            for q in llm_questions:
                if answers.get(q.id) is not None:
                    continue
                if q.options:
                    if q.type == QuestionType.CHECKBOXES:
                        answers[q.id] = random.sample(q.options, min(len(q.options), random.randint(1, 2)))
                    else:
                        answers[q.id] = random.choice(q.options)
                elif q.required:
                    answers[q.id] = random.choice(HUMAN_FALLBACK_ANSWERS)
                if isinstance(answers.get(q.id), str) and not q.options:
                    answers[q.id] = sanitize_human_text(answers[q.id])

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