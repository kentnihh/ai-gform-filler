python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium


kalau di pc sendiri download olama / qwen


how to run:
# PREVIEW
python main.py --url "https://docs.google.com/forms/d/e/1FAIpQLScjXo_bRidflpYW238gKWwQwu-TZzCyo90KSucwSjSkprip6g/viewform" --count 5 --mode preview

# SUBMIT 100
python main.py --url "https://docs.google.com/forms/d/e/1FAIpQLScjXo_bRidflpYW238gKWwQwu-TZzCyo90KSucwSjSkprip6g/viewform" --count 100 --mode submit