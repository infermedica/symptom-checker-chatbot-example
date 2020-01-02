import requests


infermedica_url = 'https://api.infermedica.com/v2/{}'


def _remote_headers(auth_string, case_id, model=None):
    app_id, app_key = auth_string.split(':')
    headers = {
        'Content-Type': 'application/json',
        'Dev-Mode': 'true',  # please turn this off when your app goes live
        'Interview-Id': case_id,
        'App-Id': app_id,
        'App-Key': app_key}
    if model:
        headers['Model'] = model
    return headers


def call_diagnosis(evidence, age, sex, case_id, auth_string, no_groups=True, model=None):
    """Call the /diagnosis endpoint.
    Input: evidence and patient basic data (age and sex).
    Output:
    1. next question to be answered by the patient (differential diagnosis);
    2. current outlook (list of diagnoses with probability estimates);
    3. "stop now" flag -- if the diagnostic engine recommends to stop asking questions now and present
    the current outlook as final results.

    Use no_groups to turn off group questions (they may be both single-choice questions and multiple questions
    gathered together under one subtitle; it's hard to handle such questions in voice-only chatbot).
    """
    request_spec = {
        'age': age,
        'sex': sex,
        'evidence': evidence,
        'extras': {
            # this is to avoid very improbable diagnoses at output and ensure there are no more than 8 results
            'enable_adaptive_ranking': True,
            # voice/chat apps usually can't handle group questions well
            'disable_groups': no_groups
        }
    }
    return call_endpoint('diagnosis', auth_string, request_spec, case_id, model)


def call_triage(evidence, age, sex, case_id, auth_string, no_groups=True, model=None):
    """Call the /triage endpoint.
    Input: evidence and patient basic data (age and sex).
    Output:
    1. next question to be answered by the patient (differential diagnosis);
    2. current outlook (list of diagnoses with probability estimates);
    3. "stop now" flag -- if the diagnostic engine recommends to stop asking questions now and present
    the current outlook as final results.

    Use no_groups to turn off group questions (they may be both single-choice questions and multiple questions
    gathered together under one subtitle; it's hard to handle such questions in voice-only chatbot).
    """
    request_spec = {
        'age': age,
        'sex': sex,
        'evidence': evidence,
        'extras': {
            # this is to turn on the 5-level triage (recommended in the API docs)
            'enable_triage_5': True,
        }
    }
    return call_endpoint('triage', auth_string, request_spec, case_id, model)


def ask_nlp(text, auth_string, case_id, context=(), conc_types=('symptom', 'risk_factor',), model=None):
    """Call Infermedica NLP API to have the user message (text) analysed and obtain a list of dicts, each
    representing one observation mention understood. Each of the mention refers to one concept (e.g. abdominal pain),
    its status/modality (present/absent/unknown) and some less important details.
    Context should be a list of strings, each string corresponding to a present observation reported so far,
    in the order of reporting. See https://developer.infermedica.com/docs/nlp (contextual clues)."""
    request_spec = {'text': text, 'context': list(context), 'include_tokens': True, 'concept_types': conc_types}
    return call_endpoint('parse', auth_string, request_spec, case_id, model=model)


def call_endpoint(endpoint, auth_string, request_spec, case_id, model=None):
    if auth_string and ':' in auth_string:
        url = infermedica_url.format(endpoint)
        headers = _remote_headers(auth_string, case_id, model)
    else:
        raise IOError('need App-Id:App-Key auth string')
    if model:
        # name of a model for a language other than the default English
        # e.g. infermedica-es
        # extract the language code in such cases
        if '-' in model:
            model = model.split('-')[-1]
        headers['Language'] = model
    if request_spec:
        resp = requests.post(
            url,
            json=request_spec,
            headers=headers)
    else:
        resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

