from typing import List
from playwright.sync_api import Page
from app.models import Question, QuestionType
from app.logger import logger

from typing import List, Tuple, Any

class FormParser:
    """Parses a Google Form DOM to extract question details and structure."""
    
    def __init__(self, page: Page) -> None:
        """Initializes the FormParser.
        
        Args:
            page (Page): An active Playwright Page instance pointing to the form.
        """
        self.page = page

    def parse(self) -> List[Question]:
        """Scans the DOM and extracts all questions.

        Returns:
            List[Question]: A list of parsed Question objects representing the form structure.
        """
        logger.info("Mulai melakukan parsing Google Form...")
        self.page.wait_for_selector('div[role="listitem"]', timeout=10000)

        # Top-level blocks only — must match FormFiller's selector or answers misalign (P0)
        question_blocks = self.page.query_selector_all(
            'xpath=//div[@role="listitem"][not(ancestor::div[@role="listitem"])]'
        )
        questions: List[Question] = []

        q_num = 0
        for block in question_blocks:
            # Ambil Judul
            title_elem = block.query_selector('div[role="heading"]')
            if not title_elem:
                continue
            q_num += 1
            # Judul asli ada di span.M7eMe; inner_text heading termasuk " *" penanda wajib
            title_span = title_elem.query_selector('.M7eMe')
            raw_title = (title_span.inner_text() if title_span else title_elem.inner_text()).strip()
            # Required via marker DOM, bukan "*" di teks (judul bisa mengandung * legitimate)
            required = (
                block.query_selector('[aria-required="true"]') is not None
                or block.query_selector('span[aria-label="Pertanyaan wajib"]') is not None
            )
            clean_title = raw_title.replace("*", "").strip()

            # Ambil Deskripsi (jika ada)
            desc_elem = block.query_selector('div[id*="desc"]')
            description = desc_elem.inner_text().strip() if desc_elem else None

            # Deteksi Tipe Pertanyaan & Opsi
            q_type, options = self._detect_type_and_options(block)

            q_id = f"q_{q_num}"
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

    def _detect_type_and_options(self, block: Any) -> Tuple[QuestionType, List[str]]:
        """Analyzes a DOM block to determine the question type and available options.
        
        Args:
            block (Locator/ElementHandle): The Playwright element for the question block.
            
        Returns:
            Tuple[QuestionType, List[str]]: The detected type and a list of valid option strings.
        """
        # Checkbox
        checkboxes = block.query_selector_all('[role="checkbox"]')
        if checkboxes:
            opts = [
                (cb.get_attribute("data-answer-value")
                 or cb.get_attribute("aria-label")
                 or cb.inner_text()).strip()
                for cb in checkboxes
            ]
            # buang opsi "Yang lain" internal Google (__other_option__) dari daftar options resmi
            return QuestionType.CHECKBOXES, [o for o in opts if o and o != "__other_option__"]

        # Radio (Multiple Choice or Linear Scale)
        radios = block.query_selector_all('[role="radio"]')
        if radios:
            opts = [
                (r.get_attribute("data-answer-value")
                 or r.get_attribute("data-value")
                 or r.get_attribute("aria-label")
                 or r.inner_text()).strip()
                for r in radios
            ]
            is_scale = all(o.isdigit() for o in opts if o)
            q_type = QuestionType.LINEAR_SCALE if is_scale else QuestionType.MULTIPLE_CHOICE
            return q_type, [o for o in opts if o and o != "__other_option__"]

        # Dropdown
        dropdown = block.query_selector('div[role="listbox"]')
        if dropdown:
            # Buka dropdown sebentar untuk baca opsi
            dropdown.click()
            try:
                self.page.wait_for_selector('div[role="option"]', timeout=3000)
            except Exception:
                pass
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