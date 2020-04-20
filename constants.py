"""Constants."""

MIN_AGE = 12
MAX_AGE = 130

SEX_NORM = {
    "male": "male",
    "m": "male",
    "man": "male",
    "female": "female",
    "f": "female",
    "woman": "female",
    "hombre": "male",
    "mujer": "female",
    "varón": "male",
    "varon": "male",
    "señor": "male",
    "senhor": "male",
    "senor": "male",
    "señora": "female",
    "senora": "female",
    "senhora": "female",
}

ANSWER_NORM = {
    "yes": "present",
    "y": "present",
    "present": "present",
    "no": "absent",
    "n": "absent",
    "absent": "absent",
    "?": "unknown",
    "skip": "unknown",
    "unknown": "unknown",
    "dont know": "unknown",
    "don't know": "unknown",
    "sí": "present",
    "si": "present",
    "no lo sé": "unknown",
    "no lo se": "unknown",
    "omitir": "unknown",
    "omita": "unknown",
    "salta": "unknown",
}
