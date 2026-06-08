import pytest
from app.domain.phi_filter import anonymize_phi

def test_anonymize_email():
    text = "Please send records to doctor.smith@hospital.com."
    expected = "Please send records to [EMAIL]."
    assert anonymize_phi(text) == expected

def test_anonymize_phone():
    text = "Call patient at 123-456-7890 or (987) 654-3210."
    expected = "Call patient at [PHONE] or [PHONE]."
    assert anonymize_phi(text) == expected

def test_anonymize_ssn_id():
    text = "SSN is 123-45-6789 and national ID is 123456789012."
    expected = "SSN is [ID_NUMBER] and national ID is [ID_NUMBER]."
    assert anonymize_phi(text) == expected

def test_anonymize_date():
    text = "Patient was born on 12/11/1985 and visited on 2026-06-08."
    expected = "Patient was born on [DATE] and visited on [DATE]."
    assert anonymize_phi(text) == expected

def test_anonymize_person_names():
    text = "Patient John Doe was diagnosed with migraine by Dr. Jack Smith. Prior Auth requested."
    # John Doe and Jack Smith should be anonymized.
    # Prior Auth, Dr., Patient, and medical terms should NOT be anonymized.
    anonymized = anonymize_phi(text)
    assert "[PERSON]" in anonymized
    assert "John Doe" not in anonymized
    assert "Jack Smith" not in anonymized
    assert "Prior Auth" in anonymized
    assert "Patient" in anonymized
