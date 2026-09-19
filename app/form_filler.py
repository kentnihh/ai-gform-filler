import time
import random
from typing import List, Dict, Union
from playwright.sync_api import Page
from app.models import Question, QuestionType
from app.logger import logger
from tenacity import retry, stop_after_attempt, wait_fixed

def human_delay(min_ms=100, max_ms=500):
    time.sleep(random.uniform(min_ms/1000.0, max_ms/1000.0))

class FormFiller:
    """Fills and submits a Google Form using Playwright automation."""
    
    def __init__(self, page: Page) -> None:
        """Initializes the FormFiller.
        
        Args:
            page (Page): An active Playwright Page instance pointing to the loaded form.
        """
        self.page = page

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def fill_and_submit(self, questions: List[Question], answers: Dict[str, Union[str, List[str]]]) -> bool:
        """Fills the form with the provided answers and simulates a human submission.
        
        Maps the generated answers to the corresponding DOM elements based on the QuestionType.
        Uses human-like delays for typing and clicking to avoid bot detection.
        
        Args:
            questions (List[Question]): The list of parsed questions representing the form structure.
            answers (Dict[str, Union[str, List[str]]]): A mapping of Question IDs to their corresponding answer(s).
            
        Returns:
            bool: True if the submission was successful and the confirmation page was reached, False otherwise.
        """
        try:
            question_blocks = self.page.query_selector_all(
                'xpath=//div[@role="listitem"][not(ancestor::div[@role="listitem"])]'
            )
            unmatched = []

            for idx, q in enumerate(questions):
                ans = answers.get(q.id)
                if ans is None:
                    continue

                block = question_blocks[idx]

                if q.type == QuestionType.SHORT_ANSWER:
                    input_elem = block.query_selector('input[type="text"]')
                    if input_elem:
                        input_elem.fill("")
                        input_elem.type(str(ans), delay=random.randint(20, 80))
                        human_delay(50, 200)

                elif q.type == QuestionType.PARAGRAPH:
                    textarea_elem = block.query_selector('textarea')
                    if textarea_elem:
                        textarea_elem.fill("")
                        textarea_elem.type(str(ans), delay=random.randint(15, 60))
                        human_delay(50, 200)

                elif q.type == QuestionType.MULTIPLE_CHOICE:
                    radios = block.query_selector_all('[role="radio"]')
                    matched = False
                    for radio in radios:
                        val = (radio.get_attribute("data-answer-value")
                               or radio.get_attribute("aria-label")
                               or radio.inner_text()).strip()
                        if val.lower() == str(ans).strip().lower():
                            radio.click(delay=random.randint(30, 100))
                            human_delay(100, 300)
                            matched = True
                            break
                    if not matched:
                        unmatched.append((q.id, ans, [
                            (r.get_attribute("data-value") or r.inner_text()).strip() for r in radios
                        ]))

                elif q.type == QuestionType.CHECKBOXES:
                    ans_list = ans if isinstance(ans, list) else [ans]
                    ans_list_norm = [str(a).strip().lower() for a in ans_list]
                    checkboxes = block.query_selector_all('[role="checkbox"]')
                    any_checked = False
                    for cb in checkboxes:
                        val = (cb.get_attribute("data-answer-value")
                               or cb.get_attribute("aria-label")
                               or cb.inner_text()).strip()
                        if val.lower() in ans_list_norm:
                            if cb.get_attribute("aria-checked") != "true":
                                cb.click(delay=random.randint(30, 100))
                                human_delay(150, 400)
                            any_checked = True
                    if not any_checked:
                        unmatched.append((q.id, ans, [
                            (c.get_attribute("data-answer-value")
                             or c.get_attribute("aria-label")
                             or c.inner_text()).strip() for c in checkboxes
                        ]))

                elif q.type == QuestionType.DROPDOWN:
                    dropdown = block.query_selector('div[role="listbox"]')
                    if dropdown:
                        dropdown.click(delay=random.randint(30, 100))
                        human_delay(300, 600)
                        option_elems = self.page.query_selector_all('div[role="option"]')
                        matched = False
                        for opt in option_elems:
                            if opt.inner_text().strip().lower() == str(ans).strip().lower():
                                opt.click(delay=random.randint(30, 100))
                                human_delay(100, 300)
                                matched = True
                                break
                        if not matched:
                            unmatched.append((q.id, ans, [o.inner_text().strip() for o in option_elems]))

                
                elif q.type == QuestionType.LINEAR_SCALE:
                    scale_items = block.query_selector_all('[role="radio"]')
                    matched = False
                    for item in scale_items:
                        val = (item.get_attribute("data-value")
                               or item.get_attribute("aria-label")
                               or item.inner_text()).strip()
                        if val == str(ans).strip():
                            item.click(delay=random.randint(30, 100))
                            human_delay(100, 300)
                            matched = True
                            break
                    if not matched:
                        unmatched.append((q.id, ans, [
                            (i.get_attribute("data-value") or i.get_attribute("aria-label") or i.inner_text()).strip()
                            for i in scale_items
                        ]))

            if unmatched:
                for qid, ans, options in unmatched:
                    logger.warning(f"Jawaban '{ans}' untuk {qid} tidak cocok dengan opsi manapun: {options}")

            # Tombol Submit
            submit_btn = self.page.query_selector(
                'div[role="button"]:has-text("Submit"), div[role="button"]:has-text("Kirim")'
            )
            if not submit_btn:
                logger.error("Tombol Submit tidak ditemukan.")
                return False

            human_delay(500, 1000)
            submit_btn.click(delay=random.randint(30, 100))

            # VERIFIKASI SUNGGUHAN: tunggu halaman konfirmasi, bukan cuma sleep
            try:
                self.page.wait_for_selector(
                    'text=/telah (disimpan|tersimpan|dicatat|direkam)|tanggapan anda|response has been recorded|your response/i',
                    timeout=8000
                )
                logger.info("Form berhasil di-submit (terkonfirmasi).")
                return True
            except Exception:
                # Cek apakah ada pesan error "Wajib diisi" yang menahan submit
                error_texts = self.page.query_selector_all('text=/wajib diisi|required/i')
                if error_texts:
                    logger.error(f"Submit GAGAL: ada {len(error_texts)} field required belum terisi valid.")
                else:
                    logger.error("Submit GAGAL: halaman konfirmasi tidak muncul (kemungkinan validasi lain).")
                self.page.screenshot(path=f"results/debug_fail_{int(time.time())}.png")
                return False

        except Exception as e:
            logger.error(f"Error saat mengisi form: {str(e)}")
            raise e