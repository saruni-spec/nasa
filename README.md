# Navigate into the project

cd nasa

# Create venv

python3 -m venv nasa

# Activate venv

source nasa/bin/activate # Mac/Linux

nasa\Scripts\activate

# Install deps

pip install -r requirements.txt

# Run

uvicorn main:app --reload
