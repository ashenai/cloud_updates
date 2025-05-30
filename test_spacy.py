# test_spacy.py
import spacy
try:
    nlp = spacy.load("en_core_web_sm")
    print("spaCy and en_core_web_sm loaded successfully.")
except Exception as e:
    print(f"Error loading spaCy model: {e}")
    # Potentially exit with an error code if running in a script that checks this
