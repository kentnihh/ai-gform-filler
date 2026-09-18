import random
from app.models import Persona

OCCUPATIONS = [
    "Mahasiswa", "Karyawan Swasta", "Guru/Dosen", "Pengusaha",
    "PNS", "Freelancer", "Ibu Rumah Tangga", "Siswa SMA"
]

FREQUENCIES = ["Pertama Kali", "Jarang", "Kadang-kadang", "Sering", "Sangat Sering"]
ATTITUDES = ["Sangat Puas & Kritis", "Netral", "Cenderung Positif", "Cepat Puas", "Kritis & Detail"]
GENDERS = ["Laki-laki", "Perempuan"]

class PersonaGenerator:
    @staticmethod
    def generate() -> Persona:
        occupation = random.choice(OCCUPATIONS)
        if occupation in ["Siswa SMA", "Mahasiswa"]:
            age = random.randint(16, 23)
        else:
            age = random.randint(24, 55)
            
        return Persona(
            age=age,
            gender=random.choice(GENDERS),
            occupation=occupation,
            usage_frequency=random.choice(FREQUENCIES),
            attitude_trait=random.choice(ATTITUDES)
        )