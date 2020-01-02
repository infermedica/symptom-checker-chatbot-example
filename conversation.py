import sys

import apiaccess


sex_norm = {
    'male': 'male',
    'm': 'male',
    'man': 'male',
    'female': 'female',
    'f': 'female',
    'woman': 'female',
    'hombre': 'male',
    'mujer': 'female',
    'varón': 'male',
    'varon': 'male',
    'señor': 'male',
    'senhor': 'male',
    'senor': 'male',
    'señora': 'female',
    'senora': 'female',
    'senhora': 'female',
}


answer_norm = {
    'yes': 'present',
    'y': 'present',
    'present': 'present',
    'no': 'absent',
    'n': 'absent',
    'absent': 'absent',
    '?': 'unknown',
    'skip': 'unknown',
    'unknown': 'unknown',
    'dont know': 'unknown',
    'don\'t know': 'unknown',
    'sí': 'present',
    'si': 'present',
    'no lo sé': 'unknown',
    'no lo se': 'unknown',
    'omitir': 'unknown',
    'omita': 'unknown',
    'salta': 'unknown',
}


modality_symbol = {'present': '+', 'absent': '-', 'unknown': '?'}


def read_input(prompt):
    if prompt.endswith('?'):
        prompt = prompt + ' '
    else:
        prompt = prompt + ': '
    print(prompt, end='', flush=True)
    return sys.stdin.readline().strip()


def read_age_sex(given_age=None, given_sex=None):
    """Primitive routine for reading age and sex specification such as "30 male" unless age and sex already given.
    This is very crude and lame. This is because reading answers to simple questions is not the main scope of this
    example. In real chatbots, either use some real intent+slot recogniser such as snips_nlu,
    or at least write a number of regular expressions to capture most typical patterns for a given language.
    Also, age below 12 should be rejected as our current model doesn't support paediatrics
    (it's being developed but not delivered yet)."""
    if given_age and given_sex:
        return int(given_age), sex_norm[given_sex.lower()]

    agesex = read_input('Patient age and sex (e.g., 30 male)')
    age, sex = agesex.split()
    return int(age), sex_norm[sex.lower()]


def read_complaint_portion(auth_string, case_id, context, given_story=None, model=None):
    """Call the /parse endpoint of Infermedica API for the given message or have the user input the message beforehand.
    """
    if given_story:
        text = given_story
    else:
        text = read_input('Describe you complaints')
    if not text:
        return None
    resp = apiaccess.ask_nlp(text, auth_string, case_id, context, model=model)
    return resp.get('mentions', [])


def mention_as_text(mention):
    """Represent the given mention structure as simple textual summary."""
    name = mention['name']
    symbol = modality_symbol[mention['choice_id']]
    return '{}{}'.format(symbol, name)


def context_from_mentions(mentions):
    return [m['id'] for m in mentions if m['choice_id'] == 'present']


def summarise_mentions(mentions):
    print('Noting: {}'.format(', '.join(mention_as_text(m) for m in mentions)))


def read_complaints(auth_string, case_id, given_story=None, model=None):
    """Keep reading complaint-describing messages from user until empty message read (or just read the story if given).
    Will call the /parse endpoint and return mentions captured there."""
    mentions = []
    context = []
    while True:
        portion = read_complaint_portion(auth_string, case_id, context, given_story, model=model)
        if portion:
            summarise_mentions(portion)
            mentions.extend(portion)
            # remember the mentions understood as context for next /parse calls
            context.extend(context_from_mentions(portion))
            if mentions and given_story:
                # assume it's all as it was given
                return mentions
        if mentions and portion is None:
            return mentions


def from_complaints(mentions):
    """Convert mentions into the evidence structure expected by the /diagnosis endpoint."""
    return [{'id': m['id'], 'choice_id': m['choice_id'], 'initial': True} for m in mentions]


def read_single_question_answer(qtext, qitem):
    """Primitive implementation of understanding user's answer to a single-choice question."""
    answer = read_input(qtext)
    if not answer:
        return None
    val = answer_norm[answer]
    return {'id': qitem['id'], 'choice_id': val, 'initial': False}


def read_question_answer_iter(question_struct):
    qtext = question_struct.get('text', 'id')
    qtype = question_struct['type']
    qitems = question_struct['items']
    stop = False
    if qtype == 'single':
        assert len(qitems) == 1
        here = read_single_question_answer(qtext, qitems[0])
        if here:
            yield here
    else:
        for qitem in qitems:
            if not stop:
                here = read_single_question_answer(qitem['name'], qitem)
                if here:
                    yield here
                    if qtype == 'group_single' and here['choice_id'] == 'present':
                        stop = True
                else:
                    stop = True


def conduct_interview(evidence, age, sex, case_id, auth, model=None):
    """Keep asking questions until API tells us to stop or the user gives an empty answer."""
    while True:
        resp = apiaccess.call_diagnosis(evidence, age, sex, case_id, auth, model=model)
        question_struct = resp['question']
        diagnoses = resp['conditions']
        if resp['should_stop']:
            triage_resp = apiaccess.call_triage(evidence, age, sex, case_id, auth, model=model)
            return evidence, diagnoses, triage_resp
        answers = list(read_question_answer_iter(question_struct))
        if not answers:
            triage_resp = apiaccess.call_triage(evidence, age, sex, case_id, auth, model=model)
            return evidence, diagnoses, triage_resp
        else:
            # this is a very important step: always update the evidence gathered so far with the new answers
            evidence.extend(answers)


def name_evidence(evidence, auth_string, case_id, model=None):
    # TODO: extract obtaining naming dict from API to a different method to be cached for some time
    # instead of asking /symptoms/ID, you can call /symptoms once and get metadata for all of them
    # this is what could be cached; remember to set some time-out to get updated metadata once in a while
    obs_structs = []
    obs_structs.extend(apiaccess.call_endpoint('risk_factors', auth_string, None, case_id=case_id, model=model))
    obs_structs.extend(apiaccess.call_endpoint('symptoms', auth_string, None, case_id=case_id, model=model))
    naming = {struct['id']: struct['name'] for struct in obs_structs}
    for piece in evidence:
        piece['name'] = naming[piece['id']]


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
        print('{:2}. {:.2f} {}'.format(idx + 1, diag['probability'], diag['name']))
    print()


def summarise_triage(triage_resp):
    print('Triage level: {}'.format(triage_resp['triage_level']))
    teleconsultation_applicable = triage_resp.get('teleconsultation_applicable')
    if teleconsultation_applicable is not None:
        print('Teleconsultation applicable: {}'.format(teleconsultation_applicable))
    print()
