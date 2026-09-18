import os
import csv
import json
import random
import time
import argparse
from typing import List
from tqdm import tqdm
from playwright.sync_api import sync_playwright

from config import Config
from app.logger import logger
from app.models import RespondentData, Question
from app.persona import PersonaGenerator
from app.form_parser import FormParser
from app.ai_generator import AIAnswerGenerator
from app.form_filler import FormFiller

def save_results(results: List[RespondentData], questions: List[Question]):
    os.makedirs("results", exist_ok=True)
    
    # Save JSON
    json_data = [r.model_dump() for r in results]
    with open("results/responses.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    # Save CSV
    fieldnames = ["respondent_id", "age", "gender", "occupation", "usage_frequency", "attitude_trait"] + [q.title for q in questions]
    
    with open("results/responses.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for r in results:
            row = [
                r.respondent_id,
                r.persona.age,
                r.persona.gender,
                r.persona.occupation,
                r.persona.usage_frequency,
                r.persona.attitude_trait
            ]
            for q in questions:
                val = r.answers.get(q.id, "")
                if isinstance(val, list):
                    val = ", ".join(val)
                row.append(val)
            writer.writerow(row)

def main():
    parser = argparse.ArgumentParser(description="AI Automated Google Form Filler")
    parser.add_argument("--url", type=str, help="Google Form URL")
    parser.add_argument("--count", type=int, help="Jumlah responden")
    parser.add_argument("--mode", type=str, choices=["preview", "submit"], help="Mode eksekusi")
    args = parser.parse_args()

    Config.validate()

    print("=====================================")
    print("       AI GOOGLE FORM FILLER         ")
    print("=====================================")

    form_url = args.url or input("Google Form URL:\n> ").strip()
    
    if not args.count:
        try:
            count = int(input("Jumlah responden:\n> "))
        except ValueError:
            print("Jumlah responden harus berupa angka!")
            return
    else:
        count = args.count

    if not args.mode:
        print("\nMode:")
        print("1. Preview (Hanya generate data tanpa submit)")
        print("2. Submit (Generate dan isi ke Google Form)")
        mode_choice = input("Pilih [1/2]:\n> ").strip()
        is_preview = mode_choice != "2"
    else:
        is_preview = args.mode == "preview"

    ai_gen = AIAnswerGenerator()
    results: List[RespondentData] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=Config.HEADLESS)
        page = browser.new_page()

        logger.info(f"Membuka URL Form: {form_url}")
        page.goto(form_url)
        
        # 1. Parsing Struktur Form
        parser_obj = FormParser(page)
        questions = parser_obj.parse()

        if not questions:
            logger.error("Gagal membaca pertanyaan dari Form.")
            browser.close()
            return

        print(f"\n[+] Berhasil membaca {len(questions)} pertanyaan dari form.\n")

        # 2. Loop Responden
        for i in tqdm(range(1, count + 1), desc="Processing Respondents"):
            persona = PersonaGenerator.generate()
            respondent_data = ai_gen.generate_answers(i, persona, questions)
            results.append(respondent_data)

            if is_preview:
                print(f"\n--- Respondent #{i} ---")
                print(f"Persona: {persona.occupation}, {persona.age}th, {persona.attitude_trait}")
                for q in questions:
                    ans = respondent_data.answers.get(q.id)
                    print(f"  {q.title}: {ans}")
                print("[Preview mode - No submission]")
            else:
                # Reload ke form kosong jika ini iterasi > 1
                if i > 1:
                    page.goto(form_url)

                filler = FormFiller(page)
                success = filler.fill_and_submit(questions, respondent_data.answers)
                
                if success:
                    logger.info(f"Responden #{i} sukses di-submit.")
                else:
                    logger.error(f"Responden #{i} gagal di-submit.")

                # Rate Limiting
                delay = random.uniform(Config.MIN_DELAY, Config.MAX_DELAY)
                time.sleep(delay)

        browser.close()

    save_results(results, questions)
    print(f"\n[✓] Selesai! Hasil tersimpan di folder 'results/'.")

if __name__ == "__main__":
    main()