import json
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


def test_ai_batch_format(mocker):
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
    personas = [Persona(
        name="Budi", email="budi@gmail.com",
        age=25, gender="Laki-laki", occupation="Developer",
        usage_frequency="Sering", attitude_trait="Netral",
        latent_score=4.0
    )]

    mock_resp = {"batch_answers": [{"idx": 0, "answers": {"q_1": "Puas"}}]}

    generator = AIAnswerGenerator()
    mocker.patch.object(generator, '_call_llm', return_value=json.dumps(mock_resp))

    results = generator.generate_batch_answers(personas, questions)

    assert results[0].answers["q_1"] == "Puas"
    assert results[0].answers["q_2"] in ["1", "2", "3", "4", "5"]
    assert int(results[0].answers["q_2"]) >= 2


def test_sanitize_human_text_anti_slop():
    from app.ai_generator import sanitize_human_text
    raw = '— "Tempatnya nyaman — pelayanan ramah banget! **rekomendasi**" —'
    clean = sanitize_human_text(raw)
    assert "—" not in clean
    assert "**" not in clean
    assert not clean.startswith('"')

