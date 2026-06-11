import re

# Set of medical terms and common routing words to not treat as names
EXCLUDE_WORDS = {
    "Prior", "Auth", "Authorization", "Blue", "Cross", "Shield", "Aetna",
    "UnitedHealthcare", "United", "Healthcare", "Viet", "Nam", "Bao", "Hiem", "Y", "Te",
    "BHYT", "BCBS", "UHC", "Doctor", "Dr", "MD", "Patient", "Hospital", "Clinic", "Medical",
    "Center", "General", "Referral", "Request", "Status", "Code", "Codes", "Summary",
    "ICD-10", "ICD9", "ICD", "Radiculopathy", "Migraine", "Lumbar", "Chronic", "Acute",
    "Pain", "Therapy", "Treatment", "Prior Auth"
}


def anonymize_phi(text: str) -> str:
    """
    Anonymize Protected Health Information (PHI) in text using regex.
    This replaces names, emails, phone numbers, SSNs/IDs, and dates to preserve privacy.
    """
    if not text:
        return text

    # 1. Emails
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]", text)

    # 2. SSN / ID numbers (e.g. 123-45-6789 or 9-12 digit ID numbers)
    # Check these first so 10-12 digit numbers are treated as ID_NUMBER, not PHONE
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[ID_NUMBER]", text)
    text = re.sub(r"\b\d{9,12}\b", "[ID_NUMBER]", text)

    # 3. Phone numbers
    # We match standard phone numbers and parenthesized area codes
    text = re.sub(r"\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4}", "[PHONE]", text)
    text = re.sub(
        r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\d{3}[-.\s]?)?\d{3}[-.\s]?\d{4}\b", "[PHONE]", text)

    # 4. Dates of birth / dates (e.g. 12/12/1990, 1990-12-12)
    text = re.sub(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", "[DATE]", text)
    text = re.sub(r"\b\d{4}-\d{1,2}-\d{1,2}\b", "[DATE]", text)

    # 5. Names (Capitalized Word Sequences)
    # We match sequences of 2 or more capitalized words.
    def name_replacer(match):
        words = match.group(0).split()
        result_words = []
        person_active = False

        for w in words:
            # Strip trailing punctuation for exclusion check
            clean_w = re.sub(r'[^\w]', '', w)
            if clean_w in EXCLUDE_WORDS:
                if person_active:
                    result_words.append("[PERSON]")
                    person_active = False
                result_words.append(w)
            else:
                person_active = True

        if person_active:
            result_words.append("[PERSON]")

        return " ".join(result_words)

    text = re.sub(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", name_replacer, text)

    return text
