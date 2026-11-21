import json

from django.conf import settings


def get_file(subject_name, test_number):
    root = settings.ANSWERS_DIR.resolve()
    path = (root / subject_name / f"{test_number}.json").resolve()
    if not path.is_relative_to(root):
        raise ValueError("Invalid answer key path.")
    with path.open(encoding="utf-8") as answer_file:
        answers = json.load(answer_file)["answers"]
    if (not isinstance(answers, list) or len(answers) != 105
            or any(not isinstance(answer, str) or not answer.replace(".", "").strip() for answer in answers)):
        raise ValueError("The answer key must contain 105 answers.")
    return answers


def getPoint(person_lang, query_data, random_num, user_answers):
    answers = get_file(query_data, random_num)
    earned_tenths = 0
    results = []
    for index, (expected, submitted) in enumerate(zip(answers, user_answers, strict=True)):
        correct = expected.replace(".", "").strip()[-1].upper() == submitted.upper()
        if correct:
            earned_tenths += 21 if index < 45 else 31
        results.append([submitted, correct])
    return earned_tenths / 10, results
