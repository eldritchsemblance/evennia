"""
Gendersub

Griatch 2015

This is a simple gender-aware Character class for allowing users to
insert custom markers in their text to indicate gender-aware
messaging. It relies on a modified msg() and is meant as an
inspiration and starting point to how to do stuff like this.

When in use, all messages being sent to the character will make use of
the character's gender, for example the echo

```
char.msg("%s falls on {p face with a thud." % char.key)
```

will result in "Tom falls on his|her|its face with a thud" depending
on the gender of the object being messaged. Default gender is
"neutral".

To use, have DefaultCharacter inherit from this, or change
setting.DEFAULT_CHARACTER to point to this class.

The `@gender` command needs to be added to the default cmdset
before it becomes available.

"""

import re

from django.conf import settings

from evennia import DefaultCharacter
from evennia import Command

# gender maps
from evennia.utils import object_from_module

GENDER_PRONOUN_MAP = {"male": {"s": "he",
                                "o": "him",
                                "p": "his",
                                "a": "his"},
                       "female": {"s": "she",
                                   "o": "her",
                                   "p": "her",
                                   "a": "hers"},
                       "neutral": {"s": "it",
                                    "o": "it",
                                    "p": "its",
                                    "a": "its"}}
RE_GENDER_PRONOUN = re.compile(r'(\{s|\{S|\{o|\{O|\{p|\{P|\{a|\{A)')


# in-game command for setting the gender
class SetGender(Command):
    """
    Sets gender on yourself

    Usage:
      @gender male|female|herm|neutral

    """
    key = "@gender"
    alias = "@sex"
    locks = "call:all()"

    def func(self):
        """
        Implements the command.
        """
        caller = self.caller
        arg = self.args.strip().lower()
        if not arg in ("male", "female", "neutral"):
            caller.msg("Usage: @gender male|female|neutral")
            return
        caller.db.gender = arg
        caller.msg("Your  gender was set to %s." % arg)


def gender_map_generator(target):
    """
    This function can be overwritten if you store gender on a different prop
    or need to customize genders in some manner.
    """
    gender = target.usrattributes.get("gender", default="neutral").lower()
    gender = gender if gender in GENDER_PRONOUN_MAP else "neutral"
    return gender, GENDER_PRONOUN_MAP


def _get_pronoun(target):
    def wrapped(regex_match):
        """
        Get pronoun from the pronoun marker in the text. This is used as
        the callable for the re.sub function.

        Args:
            target (Character): A character to find the gender for.
            regex_match (MatchObject): the regular expression match.

        Notes:
            - `{s`, `{S`: Subjective form: he, she, it, He, She, It
            - `{o`, `{O`: Objective form: him, her, it, Him, Her, It
            - `{p`, `{P`: Possessive form: his, her, its, His, Her, Its
            - `{a`, `{A`: Absolute Possessive form: his, hers, its, His, Hers, Its

        """
        typ = regex_match.group()[1]  # "s", "O" etc
        if hasattr(settings, 'GENDER_MAP_GENERATOR'):
            gender, gender_map = object_from_module(settings.GENDER_MAP_GENERATOR)(target)
        else:
            gender, gender_map = gender_map_generator(target)
        pronoun = gender_map[gender][typ.lower()]
        return pronoun.capitalize() if typ.isupper() else pronoun
    return wrapped


def gender_sub(target, text):
    return RE_GENDER_PRONOUN.sub(_get_pronoun(target), text)


# Gender-aware character class
class GenderCharacter(DefaultCharacter):
    """
    This is a Character class aware of gender.

    """

    def at_object_creation(self):
        """
        Called once when the object is created.
        """
        super(GenderCharacter, self).at_object_creation()
        self.db.gender = "neutral"

    def msg(self, text, from_obj=None, session=None, **kwargs):
        """
        Emits something to a session attached to the object.
        Overloads the default msg() implementation to include
        gender-aware markers in output.

        Args:
            text (str, optional): The message to send
            from_obj (obj, optional): object that is sending. If
                given, at_msg_send will be called
            session (Session or list, optional): session or list of
                sessions to relay to, if any. If set, will
                force send regardless of MULTISESSION_MODE.
        Notes:
            `at_msg_receive` will be called on this Object.
            All extra kwargs will be passed on to the protocol.

        """
        # pre-process the text before continuing
        text = gender_sub(self, text)
        super(GenderCharacter, self).msg(text, from_obj=from_obj, session=session, **kwargs)
