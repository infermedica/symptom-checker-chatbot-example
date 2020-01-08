#!/usr/bin/env python3
import argparse
import uuid

import conversation


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
    parser.add_argument('--model', help='set given model')
    parser.add_argument('--age', help='set given patient age')
    parser.add_argument('--sex', help='set given patient sex')
    parser.add_argument('--story', help='read given patient symptom description and don\'t ask')
    parser.add_argument(
        '-v', '--verbose', dest='verbose', action='store_true', default=False, help='dump internal state')

    args = parser.parse_args()

    auth_string = get_auth_string(args.auth)
    case_id = new_case_id()
    age, sex = conversation.read_age_sex(args.age, args.sex)
    print('Ok, {} year old {}.'.format(age, sex))
    mentions = conversation.read_complaints(auth_string, case_id, args.story, args.model)
    evidence = conversation.from_complaints(mentions)
    evidence, diagnoses, triage = conversation.conduct_interview(evidence, age, sex, case_id, auth_string, args.model)
    conversation.name_evidence(evidence, auth_string, case_id, args.model)
    print()
    conversation.summarise_all_evidence(evidence)
    conversation.summarise_diagnoses(diagnoses)
    conversation.summarise_triage(triage)


if __name__ == '__main__':
    run()
