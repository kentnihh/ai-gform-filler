# AI Context: Google Form Filler

## Project Architecture
This project is an automated Google Form filler that leverages Large Language Models (LLMs) and programmatic statistical generation to simulate highly realistic, statistically valid human responses.

It follows a modular, Single Responsibility Principle (SRP) design to ensure AI agents and human developers can easily maintain and modify individual components:
- `config.yaml`: The single source of truth for configurable demographics (e.g., genders, frequencies, attitudes).
- `config.py`: Environment configuration, validation, and YAML loader.
- `main.py`: Entrypoint for CLI execution, handles the main loop, orchestrates components, manages Checkpointing (resuming from CSV), and provides a Rich CLI progress UI.
- `app/logger.py`: Centralized `loguru` logging configuration.
- `app/models.py`: Pydantic data models for strict structured data validation (`Question`, `Persona`, `RespondentData`).
- `app/persona.py`: Generates human-like personas (demographics, names, emails) using the `Faker` library and assigns a foundational `latent_score`.
- `app/form_parser.py`: Uses `Playwright` to parse Google Form DOM structures into internal `Question` objects.
- `app/form_filler.py`: Uses `Playwright` to map generated answers back to the DOM and submit the form, utilizing human-like delays and retry mechanisms.
- `app/ai_generator.py`: Generates the answers for a persona. Uses a hybrid approach: an LLM for textual/categorical questions, and programmatic logic for statistical (Likert scale) questions.

## Environment & Ollama Setup
The project relies on a local instance of Ollama to avoid API costs, improve speed, and guarantee privacy.
- **Default Endpoint**: `http://localhost:11434`
- **Default Model**: `llama3.1` (configurable via `.env`)
- **Integration**: The official python `ollama` package is used for communication. No API keys are required for the local instance.

## Data Generation Rules (SPSS & PLS Validity)
A strict requirement of this project is that the generated data must be valid for advanced academic or professional statistical analysis, such as SPSS or Partial Least Squares Structural Equation Modeling (PLS-SEM). 

### The "Latent Score" Algorithm for Likert Scales (`LINEAR_SCALE`)
LLMs are notoriously bad at producing statistically valid Likert scale data; they often lack realistic variance or internal correlation, which destroys Cronbach's Alpha and Composite Reliability scores.

To solve this, a hybrid generation strategy is used:
1. **Latent Trait Anchoring**: In `app/persona.py`, every persona is given a `latent_score` (float between 1.5 and 4.5). This mathematically represents their unobserved, underlying attitude (e.g., 4.5 = highly satisfied).
2. **Normal Distribution**: In `app/ai_generator.py`, for every Likert scale question, the system *completely bypasses the LLM*. Instead, it generates the answer using a Gaussian/Normal Distribution algorithm: `numpy.random.normal(loc=latent_score, scale=0.6)`.
3. **Statistical Validity**: By anchoring the mean (`loc`) to the persona's latent score and adding a small variance (`scale=0.6`), the answers *within a single respondent* are highly correlated, simulating a realistic, internally consistent human respondent with expected human inconsistency.
