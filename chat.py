#!/usr/bin/env python3
import argparse
import uuid

import conversation
import apiaccess


def get_auth_string(auth_or_path):
    if ':' in auth_or_path:
        return auth_or_path
    try:
        with open(auth_or_path) as stream:
            content = stream.read()
            content = content.strip()
            if ':' in content:
                return content
    except FileNotFoundError:
        pass
    raise ValueError(auth_or_path)


def new_case_id():
    """Generate an identifier unique to a new session.
    This is not user id but an identifier that is generated anew with each started "visit" to the bot."""
    return uuid.uuid4().hex


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('auth', help='auth string for Infermedica API: app-id:app-key or filename with it')
    parser.add_argument('--model', help='use non-standard Infermedica model/language (e.g., infermedica-es)')
    parser.add_argument(
        '-v', '--verbose', dest='verbose', action='store_true', default=False, help='dump internal state')

    args = parser.parse_args()

    auth_string = get_auth_string(args.auth)
    case_id = new_case_id()

    # query for all observation names and store them
    # in a real chatbot, this could be done once at initialisation and used for handling all events by one worker
    # this will ba an id2name mapping
    naming = apiaccess.get_observation_names(auth_string, case_id, args.model)

    # read patient's age and sex; required by /diagnosis endpoint
    # alternatively, this could be done after learning patient's complaints
    age, sex = conversation.read_age_sex()
    print('Ok, {} year old {}.'.format(age, sex))

    # read patient's complaints by using /parse endpoint
    mentions = conversation.read_complaints(auth_string, case_id, args.model)

    # keep asking diagnostic questions until stop condition is met (all of this by calling /diagnosis endpoint)
    # and get the diagnostic ranking and triage (the latter from /triage endpoint)
    evidence = apiaccess.mentions_to_evidence(mentions)
    evidence, diagnoses, triage = conversation.conduct_interview(evidence, age, sex, case_id, auth_string, args.model)

    # add "name" field to each piece of evidence to get a human-readable summary
    apiaccess.name_evidence(evidence, naming)

    # print out all that we've learnt about the case and finish
    print()
    conversation.summarise_all_evidence(evidence)
    conversation.summarise_diagnoses(diagnoses)
    conversation.summarise_triage(triage)


if __name__ == '__main__':
    run()
