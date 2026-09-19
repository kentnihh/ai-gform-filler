import csv
import json
import os
import threading
from typing import List
from app.models import RespondentData, Persona
from app.logger import logger

CSV_PATH = "results/responses.csv"
db_lock = threading.Lock()

def initialize_db(questions):
    """Initializes the CSV with headers if it doesn't exist or is empty."""
    os.makedirs("results", exist_ok=True)
    with db_lock:
        file_exists = os.path.exists(CSV_PATH)
        is_empty = not file_exists or os.path.getsize(CSV_PATH) == 0
        if is_empty:
            fieldnames = ["db_id", "respondent_id", "name", "email", "age", "gender", "occupation", 
                          "usage_frequency", "attitude_trait", "latent_score", "answers_json", "status"]
            with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(fieldnames)

def _read_all_rows() -> List[List[str]]:
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        return list(reader)

def _write_all_rows(rows: List[List[str]]):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def insert_batch(respondents: List[RespondentData]):
    """Inserts a batch of respondents into the CSV."""
    with db_lock:
        rows = _read_all_rows()
        # db_id is the row index; if empty, initialize_db should have been called, 
        # but to be safe, treat start_db_id = 1 if rows is empty (0 is header)
        start_db_id = max(1, len(rows))
        
        new_rows = []
        for i, r in enumerate(respondents):
            db_id = start_db_id + i
            new_row = [
                db_id,
                r.respondent_id,
                r.persona.name,
                r.persona.email,
                r.persona.age,
                r.persona.gender,
                r.persona.occupation,
                r.persona.usage_frequency,
                r.persona.attitude_trait,
                r.persona.latent_score,
                json.dumps(r.answers),
                "Pending"
            ]
            new_rows.append(new_row)
            
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(new_rows)
            
    logger.info(f"Inserted {len(respondents)} respondents into the CSV.")

def get_pending_respondents() -> List[RespondentData]:
    """Retrieves all pending respondents from the CSV."""
    with db_lock:
        rows = _read_all_rows()
        if len(rows) <= 1: # only header or empty
            return []
            
        respondents = []
        for row in rows[1:]: # skip header
            if len(row) > 11 and row[11] == "Pending":
                persona = Persona(
                    name=row[2],
                    email=row[3],
                    age=int(row[4]),
                    gender=row[5],
                    occupation=row[6],
                    usage_frequency=row[7],
                    attitude_trait=row[8],
                    latent_score=float(row[9])
                )
                respondent = RespondentData(
                    respondent_id=int(row[1]),
                    persona=persona,
                    answers=json.loads(row[10])
                )
                # Parse db_id safely from the row
                try:
                    respondent.db_id = int(row[0])
                except ValueError:
                    respondent.db_id = 0
                respondent.status = row[11]
                respondents.append(respondent)
                
        return respondents

def mark_as_submitted(db_id: int):
    """Marks a respondent as submitted in the CSV."""
    with db_lock:
        rows = _read_all_rows()
        # db_id corresponds to the row index
        if 0 < db_id < len(rows):
            rows[db_id][11] = "Submitted"
            _write_all_rows(rows)

def get_total_count() -> int:
    """Returns the total number of respondents generated."""
    with db_lock:
        rows = _read_all_rows()
        return max(0, len(rows) - 1)
