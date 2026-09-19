import os
import time
import argparse
import random
from typing import List
import concurrent.futures

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel

from playwright.sync_api import sync_playwright

from config import Config
from app.logger import logger
from app.models import RespondentData, Question
from app.persona import PersonaGenerator
from app.form_parser import FormParser
from app.ai_generator import AIAnswerGenerator
from app.form_filler import FormFiller
from app import db

def parse_form(form_url: str) -> List[Question]:
    """Parses the Google Form and returns the questions."""
    with sync_playwright() as p:
        launch_args = {"headless": Config.HEADLESS}
        if getattr(Config, "PROXY_URL", None):
            launch_args["proxy"] = {"server": Config.PROXY_URL}
        
        browser = p.chromium.launch(**launch_args)
        page = browser.new_page()

        logger.info(f"Membuka URL Form: {form_url}")
        page.goto(form_url)
        
        parser_obj = FormParser(page)
        questions = parser_obj.parse()
        browser.close()
        return questions

def generate_phase(count: int, questions: List[Question], console: Console):
    """Generates respondents in batches and saves them to the DB."""
    db.initialize_db(questions)
    current_count = db.get_total_count()
    
    if current_count >= count:
        console.print(f"[bold yellow]Sudah {current_count} responden ter-generate. Melewati fase generate.[/bold yellow]")
        return
        
    remaining = count - current_count
    console.print(f"[bold cyan]Mulai generate {remaining} responden baru...[/bold cyan]")
    
    ai_gen = AIAnswerGenerator()
    batch_size = 3
    total_batches = (remaining + batch_size - 1) // batch_size
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Generating Respondents...", total=remaining, completed=0)
        
        for i in range(0, remaining, batch_size):
            chunk_size = min(batch_size, remaining - i)
            current_batch = (i // batch_size) + 1
            progress.update(task, description=f"[cyan]Generating batch {current_batch} of {total_batches} ({chunk_size} personas)...")
            
            personas = [PersonaGenerator.generate() for _ in range(chunk_size)]
            
            progress.update(task, description=f"[cyan]Calling LLM for batch {current_batch}/{total_batches} ({chunk_size} responses)...")
            respondents = ai_gen.generate_batch_answers(personas, questions)
            
            # Update IDs
            for j, r in enumerate(respondents):
                r.respondent_id = current_count + i + j + 1
                
            # Save to DB
            db.insert_batch(respondents)
            
            progress.advance(task, chunk_size)
            
            # Rate limiting for API
            if i + chunk_size < remaining:
                delay = random.uniform(2.0, 5.0)
                progress.update(task, description=f"[cyan]API Cooldown {delay:.1f}s...")
                time.sleep(delay)

def _submit_worker(respondent, form_url, questions):
    """Worker function for a single concurrent submission."""
    with sync_playwright() as p:
        launch_args = {"headless": Config.HEADLESS}
        if getattr(Config, "PROXY_URL", None):
            launch_args["proxy"] = {"server": Config.PROXY_URL}
        
        browser = p.chromium.launch(**launch_args)
        page = browser.new_page()
        
        try:
            page.goto(form_url)
            filler = FormFiller(page)
            success = filler.fill_and_submit(questions, respondent.answers)
            
            if success:
                logger.info(f"Responden #{respondent.respondent_id} sukses di-submit.")
                db.mark_as_submitted(respondent.db_id)
                return True
            else:
                logger.error(f"Responden #{respondent.respondent_id} gagal di-submit.")
                return False
        except Exception as e:
            logger.error(f"Responden #{respondent.respondent_id} error saat submit: {e}")
            return False
        finally:
            browser.close()

def submit_phase(form_url: str, questions: List[Question], console: Console):
    """Reads pending respondents from the DB and submits them to the form."""
    pending = db.get_pending_respondents()
    if not pending:
        console.print("[bold yellow]Tidak ada responden pending untuk di-submit.[/bold yellow]")
        return
        
    console.print(f"[bold cyan]Mulai submit {len(pending)} responden ke form secara paralel (max_workers=3)...[/bold cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Submitting Form...", total=len(pending), completed=0)
        
        # CPU Cooldown mechanism handled natively by worker startup times, but limit workers.
        max_workers = 3
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_submit_worker, r, form_url, questions): r for r in pending}
            
            for future in concurrent.futures.as_completed(futures):
                respondent = futures[future]
                progress.update(task, description=f"[cyan]Finished #{respondent.respondent_id} ({respondent.persona.name})...")
                progress.advance(task)

def main() -> None:
    """Entrypoint for the CLI application."""
    parser = argparse.ArgumentParser(description="AI Automated Google Form Filler (Decoupled Batch Architecture)")
    parser.add_argument("--url", type=str, help="Google Form URL")
    parser.add_argument("--count", type=int, help="Jumlah total responden")
    parser.add_argument("--mode", type=str, choices=["generate", "submit", "full"], help="Mode eksekusi (generate/submit/full)")
    args = parser.parse_args()

    Config.validate()
    console = Console()
    
    # 1. Parse Arguments (Backups)
    form_url = args.url
    mode = args.mode
    count = args.count

    # 2. Interactive CLI Wizard if arguments are missing
    from rich.prompt import Prompt, IntPrompt, Confirm

    if not form_url or not mode:
        console.print(Panel.fit("[bold blue]AI Google Form Filler - Interactive Wizard[/bold blue]", border_style="cyan"))
        
        if not form_url:
            form_url = Prompt.ask("[bold green]➜[/bold green] Paste the [bold cyan]Google Form URL[/bold cyan]")
            
        if not mode:
            console.print("\n[bold yellow]Select Execution Mode:[/bold yellow]")
            console.print("  [1] Generate Only (Create DB rows)")
            console.print("  [2] Submit Only (Read DB and submit)")
            console.print("  [3] Full (Generate & Submit)")
            choice = Prompt.ask("[bold green]➜[/bold green] Choose an option", choices=["1", "2", "3"], default="3")
            mode_map = {"1": "generate", "2": "submit", "3": "full"}
            mode = mode_map[choice]

    # 3. Ask for count if needed
    if mode in ["generate", "full"]:
        if not count:
            count = IntPrompt.ask("\n[bold green]➜[/bold green] How many [bold cyan]responses[/bold cyan] do you want to generate?", default=50)

    # 1. Parsing (Required for all modes to know the structure)
    console.print("[bold cyan]Parsing form structure...[/bold cyan]")
    questions = parse_form(form_url)
    if not questions:
        logger.error("Gagal membaca pertanyaan dari Form.")
        return
    console.print(f"[bold green][+] Berhasil membaca {len(questions)} pertanyaan.[/bold green]\n")

    # 2. Execution based on mode
    if mode in ["generate", "full"]:
        generate_phase(count, questions, console)
        
    if mode in ["submit", "full"]:
        submit_phase(form_url, questions, console)

    console.print("\n[bold green][✓] Selesai![/bold green]")

if __name__ == "__main__":
    main()