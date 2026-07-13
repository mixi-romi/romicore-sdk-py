from enum import StrEnum


class Emotion(StrEnum):
    """
    Romi発話の感情の種類
    """

    NORMAL = "normal"
    ANGRY = "angry"
    CRY = "cry"
    FEARFUL = "fearful"
    HEART = "heart"
    JOY = "joy"
    KISS = "kiss"
    LAUGHING = "laughing"
    RELAXED = "relaxed"
    SCREAM = "scream"
    SOB = "sob"
    SURPRISED = "surprised"
    SWEAT_SMILE = "sweat_smile"
    THINKING = "thinking"
    TIRED = "tired"


class Language(StrEnum):
    """
    Romi発話の言語の種類
    """

    JPN = "JPN"
    ENG = "ENG"
