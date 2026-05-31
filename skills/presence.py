import time


class PresenceManager:
    def __init__(self, greeting_cooldown_seconds=30, absence_reset_seconds=8):
        self.greeting_cooldown_seconds = greeting_cooldown_seconds
        self.absence_reset_seconds = absence_reset_seconds
        self.last_greeting_time = 0
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

    def force_person_left(self):
        self.person_was_present = False
        self.last_seen_time = 0
        return "person_left"
