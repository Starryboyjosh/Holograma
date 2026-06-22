import os
import time


def _env_float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


class PresenceManager:
    def __init__(
        self,
        greeting_cooldown_seconds=None,
        absence_reset_seconds=None,
        group_cooldown_seconds=None,
    ):
        # Intervalos ajustables por entorno (segundos). El saludo no se repite
        # hasta pasado greeting_cooldown; sube el valor para un demo más calmado.
        self.greeting_cooldown_seconds = (
            greeting_cooldown_seconds
            if greeting_cooldown_seconds is not None
            else _env_float("PRESENCE_GREETING_COOLDOWN", 40)
        )
        self.absence_reset_seconds = (
            absence_reset_seconds
            if absence_reset_seconds is not None
            else _env_float("PRESENCE_ABSENCE_SECONDS", 5)
        )
        self.group_cooldown_seconds = (
            group_cooldown_seconds
            if group_cooldown_seconds is not None
            else _env_float("PRESENCE_GROUP_COOLDOWN", 180)
        )
        self.last_greeting_time = 0
        self.last_group_time = 0
        self.last_seen_time = 0
        self.person_was_present = False

    def update(self, person_detected):
        now = time.time()

        if person_detected:
            self.last_seen_time = now

            if not self.person_was_present:
                self.person_was_present = True
                return "person_entered"

            return "person_still_present"

        if (
            self.person_was_present
            and now - self.last_seen_time > self.absence_reset_seconds
        ):
            self.person_was_present = False
            return "person_left"

        return "no_person"

    def should_greet(self, person_detected):
        now = time.time()
        event = self.update(person_detected)

        if event != "person_entered":
            return False

        if now - self.last_greeting_time < self.greeting_cooldown_seconds:
            return False

        self.last_greeting_time = now
        return True

    def should_greet_group(self):
        now = time.time()
        if now - self.last_group_time < self.group_cooldown_seconds:
            return False

        self.last_group_time = now
        return True

    def force_person_left(self):
        self.person_was_present = False
        self.last_seen_time = 0
        return "person_left"

