class SoundGenerator:
    """Sound frequency generator class handling frequency calculations from sound string and producing sequences of sounds."""

    _OFFSETS = {
        "C": -9,
        "C#": -8,
        "D": -7,
        "D#": -6,
        "E": -5,
        "F": -4,
        "F#": -3,
        "G": -2,
        "G#": -1,
        "A": 0,
        "A#": 1,
        "B": 2,
    }
    _NOTES = list(_OFFSETS.keys())
    _A_FREQ = 440

    def _parse_sound(self, sound: str) -> tuple[str, int]:
        """
        Parse a pitch string into its note name and octave number.

        The input must be a note from the 12-tone chromatic scale
        (e.g. "C" or "G#") followed by a single-digit octave number,
        such as "C#2" or "A5".

        Returns a tuple containing the note name and the octave number.
        """

        return sound[:-1], int(sound[-1])

    def get_note_freq(self, note: str, octave: int | None = None) -> float:
        """Get frequency value based on provided pitch data."""

        if not octave:
            n, o = self._parse_sound(note)
        else:
            n, o = note, octave
        n_offseted = self._OFFSETS[n] + (o - 4) * 12
        return self._A_FREQ * (2 ** (n_offseted / 12))

    def get_arpeggio(self, note1: str, note2: str) -> list[float]:
        """Get a sequence of frequencies between two notes in form of a list."""

        start_note = self.get_note_index(note1)
        end_note = self.get_note_index(note2)

        step = 1 if end_note >= start_note else -1

        sequence = []
        for i in range(start_note, end_note + step, step):
            n = self._NOTES[i % 12]
            o = i // 12
            sequence.append(self.get_note_freq(n, o))
        return sequence

    def get_note_index(self, note: str) -> int:
        """Return the index of a note in the chromatic scale including its octave."""

        n, o = self._parse_sound(note)
        return self._NOTES.index(n) + o * 12
