from playwright.sync_api import sync_playwright

URL = "https://docs.google.com/forms/d/e/1FAIpQLScjXo_bRidflpYW238gKWwQwu-TZzCyo90KSucwSjSkprip6g/viewform"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL)
    page.wait_for_timeout(2000)

    blocks = page.query_selector_all('xpath=//div[@role="listitem"][not(ancestor::div[@role="listitem"])]')
    checkbox_block = blocks[1]  # index [1] = "Bagaimana Anda mengetahui restoran kami?"

    checkboxes = checkbox_block.query_selector_all('[role="checkbox"]')
    for i, cb in enumerate(checkboxes):
        print(f"--- checkbox [{i}] ---")
        print("aria-label:", cb.get_attribute("aria-label"))
        print("data-value:", cb.get_attribute("data-value"))
        print("data-answer-value:", cb.get_attribute("data-answer-value"))
        print("inner_text:", repr(cb.inner_text()))
        print("outerHTML:", cb.evaluate("el => el.outerHTML"))
        print()

    browser.close()