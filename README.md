# Health Check-up Chatbot Example

This here is a simple example of how a symptom-checking chatbot may be built using Infermedica API and 300 lines
of Python code.

The project is merely a tutorial. It's not intended to be a production-ready solution.
The entire interaction takes place in console. No intent recognition is performed and the bot is pretty ignorant
when it comes to understanding user's actions other than blindly following the instructions.

## How to run the example

You'll need an Infermedica account. If you don't have one, please register at https://developer.infermedica.com.

The code is written in Python 3. First, install the requirements (preferably within a dedicated virtualenv):

```
pip install -r requirements.txt
```

To run the demo:

```
python chat.py APP_ID:APP_KEY
```

Please use the `APP_ID` and `APP_KEY` values from your Infermedica account.

The demo starts by asking for patient's age and sex. Then you're expected to provide complaints.
You can provide complaints in one or multiple messages. You need to reply with an empty string to let the bot know
you're finished with the complaints. A real-life bot should understand replies such as _I don't know_, _that's it_, etc.

The complaints are analysed by using the `/parse` endpoint of the Infermedica API.

The bot will start asking diagnostic questions obtained from the `/diagnosis` endpoint of the Infermedica API.
At this stage, answers of `yes` (or `y`), `no` (`n`) or `dont know` (or `skip`) are expected.
The interview will finish when the diagnostic API responds with a `should_stop` flag.
This flag is raised when the engine reaches conclusion that enough is known or there have already been too many
questions to bother the user further.

This toy bot also allows you to finish earlier and see what the current outlook was. To do so, reply to a question
with an empty string (just press enter). You'll see what the current hypotheses were, although these will have been
based on incomplete knowledge and may well be unreliable.

Below is an example session.

```
$ ./chat.py APP_ID:APP_KEY

Patient age and sex (e.g., 30 male): 40 male
Ok, 40 year old male.
Describe you complaints: it hurts when I pee, also, stomach ache
Noting: +Pain while urinating, +Abdominal pain
Describe you complaints:
Have you had urinary tract infections before, e.g. infections of bladder, urethra, kidney or ureter? no
Is your stomach pain severe? no
Is your stomach pain in the right lower part of your abdomen? dont know
Has your stomach pain lasted less than two days? yes
Did you have genital trauma recently? no
Have you recently had any trauma or physical injury? no
Do you have to urinate more often than usual? yes
Can you describe your sexual behavior as risky (e.g. sex without condom use, having a high-risk partner, anal sex, mouth-to-genital contact, having multiple sex partners)? no
Do you have a fever? yes
Is your body temperature between 100.4°F (38°C) and 104°F (40°C)? no
Do you have pain around your anus? no
Do you sometimes have a sudden and urgent need to pass urine such that it is difficult for you to hold it? yes
Do you urinate in small amounts such as a drop at a time? yes
Are you passing more urine than you usually do over all day? dont know

Patient complaints:
 1. +Pain while urinating
 2. +Abdominal pain

Patient answers:
 1. -History of urinary tract infections
 2. -Abdominal pain, severe
 3. ?Abdominal pain, right lower quadrant
 4. +Abdominal pain, lasting less than two days
 5. -Genital injury
 6. -Recent physical injury
 7. +Frequent urination
 8. -Risky sexual behavior
 9. +Fever
10. -Fever between 100.4 and 104 °F (38 and 40 °C)
11. -Anorectal pain
12. +Urinary urgency
13. +Urination in small amounts
14. ?Frequent urination, large quantities

Diagnoses:
 1. 0.86 Acute cystitis

Triage level: consultation_24
Teleconsultation applicable: False
```

## What is not covered here

A real chatbot needs to handle multiple users. You need to have a database where you'd keep state of conversation
with each user and have it updated each time an interaction takes place. Also, a real chatbot will need to handle
events coming from external components (e.g. chatbot frontend or third-party platform such as Google Assistant),
so the bot backend should probably be a REST app (e.g. made with Flask or UWSGI).
In such a setting, this would be an event-driven program. The application would expose a _handle message_ endpoint
that would be called with user id, user message text and possibly some settings.
The endpoint would be responsible for retrieving the state of conversation with the requesting user,
handling the user's message, altering the state, storing the altered state back in the database and returning response
messages.

Also, some basic intent recognition is needed to know when the user wants to proceed to next stage, to quit the
conversation, perhaps restart or request for help. In the most crude form this could be handled by a list of most likely
answers or regular expressions; but in the long run you should consider using open-source tools
such as _Snips NLU_ or _RASA NLU_.

Please note that you must know the user's age and sex before calling `/diagnosis`.
You're free to choose if you want to read complaints first or age and sex.
Any case of age below 12 years old should be rejected as the Infermedica's engine does not cover paediatrics yet
(at the moment of writing).
For legal reasons you may need to use higher age threshold, though. 


If you're developing a voice app or simple text-based chat, you cannot handle medical questions other than
the simple ones (yes, no, don't-know). For such scenarios the `disable_groups` mode is intented (see `apiaccess.py`).
If your chatbot is more of a rich conversational UI, then you may as well support all of the question types and not
need this mode.
