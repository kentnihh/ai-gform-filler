import time
from typing import List, Dict, Union
from playwright.sync_api import Page
from app.models import Question, QuestionType
from app.logger import logger

class FormFiller:
    def __init__(self, page: Page):
        self.page = page

    def fill_and_submit(self, questions: List[Question], answers: Dict[str, Union[str, List[str]]]) -> bool:
        try:
            question_blocks = self.page.query_selector_all('div[role="listitem"]')

            for idx, q in enumerate(questions):
                ans = answers.get(q.id)
                if ans is None:
                    continue

                block = question_blocks[idx]

                if q.type == QuestionType.SHORT_ANSWER:
                    input_elem = block.query_selector('input[type="text"]')
                    if input_elem:
                        input_elem.fill(str(ans))

                elif q.type == QuestionType.PARAGRAPH:
                    textarea_elem = block.query_selector('textarea')
                    if textarea_elem:
                        textarea_elem.fill(str(ans))

                elif q.type == QuestionType.MULTIPLE_CHOICE:
                    radios = block.query_selector_all('div[role="radio"]')
                    for radio in radios:
                        val = radio.get_attribute("data-value") or radio.inner_text().strip()
                        if val == str(ans):
                            radio.click()
                            break

                elif q.type == QuestionType.CHECKBOXES:
                    ans_list = ans if isinstance(ans, list) else [ans]
                    checkboxes = block.query_selector_all('div[role="checkbox"]')
                    for cb in checkboxes:
                        val = cb.get_attribute("data-value") or cb.inner_text().strip()
                        if val in ans_list:
                            # Hanya klik jika belum tercentang
                            if cb.get_attribute("aria-checked") != "true":
                                cb.click()

                elif q.type == QuestionType.DROPDOWN:
                    dropdown = block.query_selector('div[role="listbox"]')
                    if dropdown:
                        dropdown.click()
                        time.sleep(0.3)
                        option_elems = self.page.query_selector_all('div[role="option"]')
                        for opt in option_elems:
                            if opt.inner_text().strip() == str(ans):
                                opt.click()
                                break

            # Tombol Submit
            submit_btn = self.page.query_selector('div[role="button"][jscontroller]:has-text("Submit"), div[role="button"]:has-text("Kirim")')
            if not submit_btn:
                submit_btn = self.page.query_selector('span:has-text("Submit"), span:has-text("Kirim")')

            if submit_btn:
                submit_btn.click()
                self.page.wait_for_timeout(2000)
                logger.info("Form berhasil di-submit.")
                return True
            else:
                logger.error("Tombol Submit tidak ditemukan.")
                return False

        except Exception as e:
            logger.error(f"Error saat mengisi form: {str(e)}")
            return False