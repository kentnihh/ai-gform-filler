import pytest
from app.models import Question, QuestionType, Persona
from app.ai_generator import AIAnswerGenerator

def test_persona_generation():
    from app.persona import PersonaGenerator
    p = PersonaGenerator.generate()
    assert p.age > 0
    assert len(p.occupation) > 0

def test_ai_answer_format(mocker):
    questions = [
        Question(
            id="q_1",
            title="Seberapa puas Anda?",
            type=QuestionType.MULTIPLE_CHOICE,
            required=True,
            options=["Sangat Puas", "Puas", "Tidak Puas"]
        )
    ]
    persona = Persona(
        age=25, gender="Laki-laki", occupation="Developer",
        usage_frequency="Sering", attitude_trait="Netral"
    )

    # Mock response OpenAI
    mock_resp = {
        "answers": {
            "q_1": "Puas"
        }
    }
    
    generator = AIAnswerGenerator()
    mocker.patch.object(generator.client.chat.completions, 'create', return_value=mocker.MagicMock(
        choices=[mocker.MagicMock(message=mocker.MagicMock(content=str(mock_resp).replace("'", '"')))]
    ))

    result = generator.generate_answers(1, persona, questions)
    assert result.answers["q_1"] in questions[0].options