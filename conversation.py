import re
import sys

import apiaccess
import constants


def read_input(prompt):
    """Displays appropriate prompt and reads the input.

    Args:
        prompt (str): String to be displayed.

    Returns:
        str: Stripped users input.

    """
    if prompt.endswith('?'):
        prompt = prompt + ' '
    else:
        prompt = prompt + ': '
    print(prompt, end='', flush=True)
    return sys.stdin.readline().strip()


def read_age_sex():
    """Reads age and sex specification such as "30 male".

    This is very crude. This is because reading answers to simple questions is
    not the main scope of this example. In real chatbots, either use some real
    intent+slot recogniser such as snips_nlu, or at least write a number of
    regular expressions to capture most typical patterns for a given language.
    Also, age below 12 should be rejected as our current knowledge doesn't
    support paediatrics (it's being developed but not delivered yet).

    Returns:
        int, str: Age and sex.

    """
    agesex = read_input("Patient age and sex (e.g., 30 male)")
    try:
        age, sex = agesex.split()
        age = int(age)
        sex = constants.SEX_NORM[sex.lower()]
        if age < constants.MIN_AGE:
            print("Ages below 12 are not yet supported.", end=' ')
            raise ValueError
        if age > constants.MAX_AGE:
            print("Maximum possible age is 130.", end=' ')
            raise ValueError
    except (ValueError, KeyError):
        print("Invalid input, Please reenter.")
        age, sex = read_age_sex()
    return age, sex


def read_complaint_portion(auth_string, case_id, context, language_model=None):
    """Reads user input and calls the /parse endpoint of Infermedica API to
    extract conditions found in text.

    Args:
        auth_string (str): Authentication string.
        case_id (str): Case ID.
        context (list): List previous complaints.
        lanugage_model (str): Chosen language model.

    Returns:
        dict: Response from /parse endpoint.

    """
    text = read_input('Describe you complaints')
    if not text:
        return None
    resp = apiaccess.call_parse(text, auth_string, case_id, context,
                                language_model=language_model)
    return resp.get('mentions', [])


def mention_as_text(mention):
    """Represents the given mention structure as simple textual summary.

    Args:
        mention (dict): Response containing information about medical concept.

    Returns:
        str: Formatted name of the reported medical concept, e.g. +Dizziness,
            -Headache.

    """
    _modality_symbol = {"present": "+", "absent": "-", "unknown": "?"}
    name = mention["name"]
    symbol = _modality_symbol[mention["choice_id"]]
    return "{}{}".format(symbol, name)


def context_from_mentions(mentions):
    """Returns IDs of medical concepts that are present."""
    return [m['id'] for m in mentions if m['choice_id'] == 'present']


def summarise_mentions(mentions):
    """Prints noted mentions."""
    print("Noting: {}".format(", ".join(mention_as_text(m) for m in mentions)))


def read_complaints(auth_string, case_id, language_model=None):
    """Keeps reading complaint-describing messages from user until empty
    message is read (or just read the story if given). Will call the /parse
    endpoint and return mentions captured there.

    Args:
        auth_string (str): Authentication string.
        case_id (str): Case ID.
        lanugage_model (str): Chosen language model.

    Returns:
        list: Mentions extracted from user answers.

    """
    mentions = []
    context = []  # List of ids of present symptoms in the order of reporting.
    while True:
        portion = read_complaint_portion(auth_string, case_id, context,
                                         language_model=language_model)
        if portion:
            summarise_mentions(portion)
            mentions.extend(portion)
            # Remember the mentions understood as context for next /parse calls
            context.extend(context_from_mentions(portion))
        if mentions and portion is None:
            # User said there's nothing more but we've already got at least one
            # complaint.
            return mentions


def read_single_question_answer(question_text):
    """Primitive implementation of understanding user's answer to a
    single-choice question. Prompt the user with question text, read user's
    input and convert it to one of the expected evidence statuses: present,
    absent or unknown. Return None if no answer provided."""
    answer = read_input(question_text)
    if not answer:
        return None
    return constants.ANSWER_NORM[answer]


def conduct_interview(evidence, age, sex, case_id, auth, language_model=None):
    """Keep asking questions until API tells us to stop or the user gives an
    empty answer."""
    while True:
        resp = apiaccess.call_diagnosis(evidence, age, sex, case_id, auth,
                                        language_model=language_model)
        question_struct = resp['question']
        diagnoses = resp['conditions']
        should_stop_now = resp['should_stop']
        if should_stop_now:
            # Triage recommendation must be obtained from a separate endpoint,
            # call it now and return all the information together.
            triage_resp = apiaccess.call_triage(evidence, age, sex, case_id,
                                                auth,
                                                language_model=language_model)
            return evidence, diagnoses, triage_resp
        new_evidence = []
        if question_struct['type'] == 'single':
            # If you're calling /diagnosis in "disable_groups" mode, you'll
            # only get "single" questions. These are simple questions that
            # require a simple answer -- whether the observation being asked
            # for is present, absent or unknown.
            question_items = question_struct['items']
            assert len(question_items) == 1  # this is a single question
            question_item = question_items[0]
            observation_value = read_single_question_answer(
                question_text=question_struct['text'])
            if observation_value is not None:
                new_evidence.append(apiaccess.question_answer_to_evidence(
                    question_item, observation_value))
        else:
            # You'd need a rich UI to handle group questions gracefully.
            # There are two types of group questions: "group_single" (radio
            # buttons) and "group_multiple" (a bunch of single questions
            # gathered under one caption). Actually you can try asking
            # sequentially for each question item from "group_multiple"
            # question and then adding the evidence coming from all these
            # answers. For "group_single" there should be only one present
            # answer. It's recommended to include only this chosen answer as
            # present symptom in the new evidence. For more details, please
            # consult:
            # https://developer.infermedica.com/docs/diagnosis#group_single
            raise NotImplementedError("Group questions not handled in this"
                                      "example")
        # Important: always update the evidence gathered so far with the new
        # answers
        evidence.extend(new_evidence)


def summarise_some_evidence(evidence, header):
    print(header + ':')
    for idx, piece in enumerate(evidence):
        print('{:2}. {}'.format(idx + 1, mention_as_text(piece)))
    print()


def summarise_all_evidence(evidence):
    reported = []
    answered = []
    for piece in evidence:
        (reported if piece.get('initial') else answered).append(piece)
    summarise_some_evidence(reported, 'Patient complaints')
    summarise_some_evidence(answered, 'Patient answers')


def summarise_diagnoses(diagnoses):
    print('Diagnoses:')
    for idx, diag in enumerate(diagnoses):
        print('{:2}. {:.2f} {}'.format(idx + 1, diag['probability'],
                                       diag['name']))
    print()


def summarise_triage(triage_resp):
    print('Triage level: {}'.format(triage_resp['triage_level']))
    teleconsultation_applicable = triage_resp.get(
        'teleconsultation_applicable')
    if teleconsultation_applicable is not None:
        print('Teleconsultation applicable: {}'
              .format(teleconsultation_applicable))
    print()


def extract_intentions(text, mapping=constants.ANSWER_NORM):
    """Extracts intent from given text.

    This is a slightly more advanced intent recognition (but still basic),
    which matches regular expression for each word in dictionary and then
    projects them onto possible intents.

    Note:
        The match is case insensitive.

    Args:
        text (str): Text to analyzed.
        mapping (dict, optional): Mapping from keyword to intent. Defaults to
            constants.ANSWER_NORM.

    Returns:
        list: Found intents. One for each found keyword.

    """
    # Construct an alternative regex pattern for each keyword (speeds up the
    # search). Note that keywords must me escaped as they could potentialy
    # contain regex-specific symbols, e.g. ?, *.
    pattern = r"|".join(r"\b{}\b".format(re.escape(keyword))
                        for keyword in mapping.keys())
    mentions_regex = re.compile(pattern, flags=re.I)
    found_keywords = mentions_regex.findall(text)
    return [mapping[found.lower()] for found in found_keywords]
