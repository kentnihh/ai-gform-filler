import random
from faker import Faker
from app.models import Persona

from config import Config
from data.names import FIRST_NAMES, LAST_NAMES

fake = Faker('id_ID')

class PersonaGenerator:
    """Utility class to generate realistic human personas for form filling."""
    
    @staticmethod
    def generate() -> Persona:
        """Generates a random, statistically valid Persona.
        
        Uses the Faker library (id_ID locale) to generate realistic names, emails, 
        and occupations. It also computes a 'latent_score' which acts as a 
        mathematical anchor for statistical generation of Likert scale answers.
        
        Returns:
            Persona: A fully populated Persona object.
        """
        genders = Config.DEMOGRAPHICS.get("genders", ["Laki-laki", "Perempuan"])
        frequencies = Config.DEMOGRAPHICS.get("frequencies", ["Pertama Kali", "Jarang", "Kadang-kadang", "Sering", "Sangat Sering"])
        attitudes = Config.DEMOGRAPHICS.get("attitudes", ["Sangat Puas & Kritis", "Netral", "Cenderung Positif", "Cepat Puas", "Kritis & Detail"])
        
        gender = random.choice(genders)
        
        # Name generation based on probabilities
        word_count = random.choices([1, 2, 3], weights=[15, 60, 25])[0]
        name_parts = [random.choice(FIRST_NAMES)]
        
        if word_count > 1:
            available_last_names = [n for n in LAST_NAMES if n not in name_parts]
            chosen_lasts = random.sample(available_last_names, word_count - 1)
            name_parts.extend(chosen_lasts)
            
        name = " ".join(name_parts)

        # Generate realistic email based on name
        clean_parts = ["".join(c for c in part.lower() if c.isalnum()) for part in name_parts]
        email_base = ".".join(clean_parts)
        
        # Optional random number
        if random.random() < 0.5:
            email_base += str(random.randint(1, 999))
            
        email = f"{email_base}@gmail.com"
        
        occupation = fake.job()
        age = random.randint(18, 55)
            
        # Generate a latent score (attitude anchor for statistical generation)
        latent_score = round(random.uniform(1.5, 4.5), 2)

        return Persona(
            name=name,
            email=email,
            age=age,
            gender=gender,
            occupation=occupation,
            usage_frequency=random.choice(frequencies),
            attitude_trait=random.choice(attitudes),
            latent_score=latent_score
        )