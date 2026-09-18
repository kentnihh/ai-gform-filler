import time
from typing import List
from playwright.sync_api import Page
from app.models import Question, QuestionType
from app.logger import logger

class FormParser:
    def __init__(self, page: Page):
        self.page = page

    def parse(self) -> List[Question]:
        logger.info("Mulai melakukan parsing Google Form...")
        self.page.wait_for_selector('div[role="listitem"]', timeout=10000)
        
        question_blocks = self.page.query_selector_all('div[role="listitem"]')
        questions: List[Question] = []

        for idx, block in enumerate(question_blocks):
            # Ambil Judul
            title_elem = block.query_selector('div[role="heading"]')
            if not title_elem:
                continue
            title_text = title_elem.inner_text().strip()
            # Hilangkan asterisk (*) jika pertanyaan wajib
            required = "*" in title_text
            clean_title = title_text.replace("*", "").strip()

            # Ambil Deskripsi (jika ada)
            desc_elem = block.query_selector('div[id*="desc"]')
            description = desc_elem.inner_text().strip() if desc_elem else None

            # Deteksi Tipe Pertanyaan & Opsi
            q_type, options = self._detect_type_and_options(block)

            q_id = f"q_{idx + 1}"
            question = Question(
                id=q_id,
                title=clean_title,
                description=description,
                type=q_type,
                required=required,
                options=options
            )
            questions.append(question)

        logger.info(f"Berhasil mengidentifikasi {len(questions)} pertanyaan.")
        return questions

    def _detect_type_and_options(self, block) -> tuple[QuestionType, List[str]]:
        # Checkbox
        checkboxes = block.query_selector_all('div[role="checkbox"]')
        if checkboxes:
            opts = [cb.get_attribute("data-value") or cb.inner_text().strip() for cb in checkboxes]
            return QuestionType.CHECKBOXES, [o for o in opts if o]

        # Radio (Multiple Choice or Linear Scale)
        radios = block.query_selector_all('div[role="radio"]')
        if radios:
            opts = [r.get_attribute("data-value") or r.inner_text().strip() for r in radios]
            # Jika opsi berisi angka sequential, treat as linear scale / radio
            return QuestionType.MULTIPLE_CHOICE, [o for o in opts if o]

        # Dropdown
        dropdown = block.query_selector('div[role="listbox"]')
        if dropdown:
            # Buka dropdown sebentar untuk baca opsi
            dropdown.click()
            time.sleep(0.3)
            option_elems = self.page.query_selector_all('div[role="option"]')
            opts = [opt.inner_text().strip() for opt in option_elems if opt.inner_text().strip()]
            self.page.keyboard.press("Escape")  # Tutup kembali
            return QuestionType.DROPDOWN, opts

        # Text Area (Paragraph)
        textarea = block.query_selector('textarea')
        if textarea:
            return QuestionType.PARAGRAPH, []

        # Short Text
        text_input = block.query_selector('input[type="text"]')
        if text_input:
            return QuestionType.SHORT_ANSWER, []

        return QuestionType.SHORT_ANSWER, []