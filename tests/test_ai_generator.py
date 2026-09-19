import pytest
from app.models import Question, QuestionType, Persona
from app.ai_generator import AIAnswerGenerator

def test_persona_generation():
    from app.persona import PersonaGenerator
    p = PersonaGenerator.generate()
    assert p.age > 0
    assert len(p.occupation) > 0
    assert len(p.name) > 0
    assert "@" in p.email
    assert 1.0 <= p.latent_score <= 5.0

def test_ai_answer_format(mocker):
    questions = [
        Question(
            id="q_1",
            title="Seberapa puas Anda?",
            type=QuestionType.MULTIPLE_CHOICE,
            required=True,
            options=["Sangat Puas", "Puas", "Tidak Puas"]
        ),
        Question(
            id="q_2",
            title="Skala linear",
            type=QuestionType.LINEAR_SCALE,
            required=True,
            options=["1", "2", "3", "4", "5"]
        )
    ]
    persona = Persona(
        name="Budi", email="budi@gmail.com",
        age=25, gender="Laki-laki", occupation="Developer",
        usage_frequency="Sering", attitude_trait="Netral",
        latent_score=4.0
    )

    # Mock response LLM (we only ask LLM for non-Likert questions)
    mock_resp = {
        "answers": {
            "q_1": "Puas"
        }
    }
    
    generator = AIAnswerGenerator()
    # Mock the internal LLM call to bypass API completely in tests
    mocker.patch.object(generator, '_call_llm', return_value=str(mock_resp).replace("'", '"'))

    result = generator.generate_answers(1, persona, questions)
    
    # Assert LLM parsed answer
    assert result.answers["q_1"] == "Puas"
    
    # Assert programmatic statistical answer
    assert result.answers["q_2"] in ["1", "2", "3", "4", "5"]
    # With latent score 4.0, mean is ~4, so it should be highly likely to be 3, 4, or 5
    assert int(result.answers["q_2"]) >= 2