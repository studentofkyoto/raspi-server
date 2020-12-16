"""
ir recording and playbacking tool
"""
import time
from typing import List, Dict, Union, Any

import pigpio


class Irrp:
    """
    record and playback class
    """
    GLITCH = 100  # ignore edges shorter than glitch microseconds, default 100 us
    PRE_MS = 200  # expect post milliseconds of silence after code, default 15 ms
    POST_MS = 15  # expect pre milliseconds of silence before code, default 200 ms
    FREQ = 38.0  # IR carrier frequency, default 38 kHz
    SHORT = 10  # reject codes with less than short pulses, default 10
    GAP_MS = 100  # gap in milliseconds between transmitted codes, default 100 ms
    TOLERANCE = 15  # consider pulses the same if within tolerance percent, default 15

    POST_US = POST_MS * 1000
    PRE_US = PRE_MS * 1000
    GAP_S = GAP_MS / 1000.0
    TOLER_MIN = (100 - TOLERANCE) / 100.0
    TOLER_MAX = (100 + TOLERANCE) / 100.0

    RECORD_PIN = 18
    PLAYBACK_PIN = 17

    def __init__(self) -> None:
        self._last_tick = 0
        self._in_code = False
        self._press1: List[float] = []
        self._press2: List[float] = []
        self._code: List[float] = []
        self._fetching_code = False

    @staticmethod
    def _carrier(
            gpio: int,
            frequency: float,
            micros: float) -> List[float]:
        """
        Generate carrier square wave.
        """
        waveform = []
        cycle = 1000.0 / frequency
        cycles = int(round(micros / cycle))
        on_pulse = int(round(cycle / 2.0))
        sofar = 0
        for cycle in range(cycles):
            target = int(round((cycle + 1) * cycle))
            sofar += on_pulse
            off_pulse = target - sofar
            sofar += off_pulse
            waveform.append(pigpio.pulse(1 << gpio, 0, on_pulse))
            waveform.append(pigpio.pulse(0, 1 << gpio, off_pulse))
        return waveform

    def _normalise(self) -> None:
        """
        Typically a code will be made up of two or three distinct
        marks (carrier) and spaces (no carrier) of different lengths.

        Because of transmission and reception errors those pulses
        which should all be x micros long will have a variance around x.

        This function identifies the distinct pulses and takes the
        average of the lengths making up each distinct pulse.  Marks
        and spaces are processed separately.

        This makes the eventual generation of waves much more efficient.

        Input

            M    S   M   S   M   S   M    S   M    S   M
        9000 4500 600 540 620 560 590 1660 620 1690 615

        Distinct marks

        9000                average 9000
        600 620 590 620 615 average  609

        Distinct spaces

        4500                average 4500
        540 560             average  550
        1660 1690           average 1675

        Output

            M    S   M   S   M   S   M    S   M    S   M
        9000 4500 609 550 609 550 609 1675 609 1675 609
        """
        entries = len(self._code)
        pulse = [0] * entries
        for index, value in enumerate(self._code):
            if not pulse[index]:  # Not processed?
                tot = value
                similar = 1.0

                # Find all pulses with similar lengths to the start pulse.
                for j in range(index + 2, entries, 2):
                    if not pulse[j]:  # Unprocessed.
                        if (self._code[j] *
                                self.TOLER_MIN) < value < (self._code[j] *
                                                           self.TOLER_MAX):  # Similar.
                            tot = tot + self._code[j]
                            similar += 1.0

                # Calculate the average pulse length.
                newv = round(tot / similar, 2)
                self._code[index] = newv

                # Set all similar pulses to the average value.
                for j in range(index + 2, entries, 2):
                    if not pulse[j]:  # Unprocessed.
                        if (self._code[j] *
                                self.TOLER_MIN) < value < (self._code[j] *
                                                           self.TOLER_MAX):  # Similar.
                            self._code[j] = newv
                            pulse[j] = 1

    def _compare(self, pulse1: List[float], pulse2: List[float]) -> bool:
        """
        Check that both recodings correspond in pulse length to within
        TOLERANCE%.  If they do average the two recordings pulse lengths.

        Input

                M    S   M   S   M   S   M    S   M    S   M
        1: 9000 4500 600 560 600 560 600 1700 600 1700 600
        2: 9020 4570 590 550 590 550 590 1640 590 1640 590

        Output

        A: 9010 4535 595 555 595 555 595 1670 595 1670 595
        """
        if len(pulse1) != len(pulse2):
            return False

        for value1, value2 in zip(pulse1, pulse2):
            value = value1 / value2
            if (value < self.TOLER_MIN) or (value > self.TOLER_MAX):
                return False

        for index, value in enumerate(pulse1):
            pulse1[index] = int(round((pulse1[index] + pulse2[index]) / 2.0))

        return True

    def _tidy_mark_space(self, recorded: List[float], base: int) -> None:

        millisec: Dict[Any, Any] = {}

        for i in range(base, len(recorded), 2):
            if recorded[i] in millisec:
                millisec[recorded[i]] += 1
            else:
                millisec[recorded[i]] = 1

        value = None

        for plen in sorted(millisec):
            if value is None:
                tmp = [plen]
                value = plen
                tot = plen * millisec[plen]
                similar = millisec[plen]

            elif plen < (value * self.TOLER_MAX):
                tmp.append(plen)
                tot += (plen * millisec[plen])
                similar += millisec[plen]

            else:
                value = int(round(tot / float(similar)))
                for i in tmp:
                    millisec[i] = value
                tmp = [plen]
                value = plen
                tot = plen * millisec[plen]
                similar = millisec[plen]

        value = int(round(tot / float(similar)))
        for i in tmp:
            millisec[i] = value

        for i in range(base, len(recorded), 2):
            recorded[i] = millisec[recorded[i]]

    def _tidy(self, recorded: List[float]) -> None:
        self._tidy_mark_space(recorded, 0)
        self._tidy_mark_space(recorded, 1)

    def _end_of_code(self) -> None:
        """
        finish fetching code if code is long enough
        """
        if len(self._code) > self.SHORT:
            self._normalise()
            self._fetching_code = False
        else:
            self._code = []
            print("Short code, probably a repeat, try again")

    def _record(self) -> List[float]:
        """
        record ir pulse
        """
        pigpio_pi = pigpio.pi()
        if not pigpio_pi.connected:
            raise Exception("cannot connect to pigpio")
        pigpio_pi.set_mode(self.RECORD_PIN, pigpio.INPUT)
        pigpio_pi.set_glitch_filter(self.RECORD_PIN, self.GLITCH)

        def cbf(gpio: int, level: int, tick: int) -> None:
            if level != pigpio.TIMEOUT:
                edge = pigpio.tickDiff(self._last_tick, tick)
                self._last_tick = tick

                if self._fetching_code:

                    if (edge > self.PRE_US) and (
                            not self._in_code):  # Start of a code.
                        self._in_code = True
                        # Start watchdog.
                        pigpio_pi.set_watchdog(gpio, self.POST_MS)

                    # End of a code.
                    elif (edge > self.POST_US) and self._in_code:
                        self._in_code = False
                        pigpio_pi.set_watchdog(gpio, 0)  # Cancel watchdog.
                        self._end_of_code()

                    elif self._in_code:
                        self._code.append(edge)
            else:
                pigpio_pi.set_watchdog(gpio, 0)  # Cancel watchdog.
                if self._in_code:
                    self._in_code = False
                    self._end_of_code()

        print("Recording")
        print("Press button")
        self._code = []
        self._fetching_code = True
        pigpio_pi.callback(self.RECORD_PIN, pigpio.EITHER_EDGE, cbf)
        while self._fetching_code:
            time.sleep(0.1)
        print("Okay")
        return self._code[:]

    def record(self) -> List[float]:
        """
        record with no comfirm
        """
        recorded = self._record()
        self._tidy(recorded)
        return recorded

    def record_first(self) -> List[float]:
        """
        record first press
        """
        self._press1 = self._record()
        return self._press1

    def record_confirm(self) -> Union[bool, List[float]]:
        """
        record second press and compare to the first press
        """
        if not self._press1:
            raise Exception("first press not recorded")

        recorded: List[float] = []
        for try_count in range(3):
            self._press2 = self._record()
            the_same = self._compare(self._press1, self._press2)
            if the_same:
                recorded = self._press1[:]
                print("Okay")
                break
            if try_count <= 3:
                print("No match")
            else:
                print("Giving up")
            time.sleep(0.5)

        self._press1 = []
        self._press2 = []
        if not recorded:
            return False
        self._tidy(recorded)
        return recorded

    def playback(self, code: List[int]) -> None:
        """
        play back the given code
        """
        pigpio_pi = pigpio.pi('soft', 8888)
        pigpio_pi.set_mode(self.PLAYBACK_PIN, pigpio.OUTPUT)
        pigpio_pi.wave_add_new()
        emit_time = time.time()

        marks_wid: Dict[int, float] = {}
        spaces_wid: Dict[int, float] = {}
        wave = [0.0] * len(code)

        for index, value in enumerate(code):
            if index & 1:  # Space
                if value not in spaces_wid:
                    pigpio_pi.wave_add_generic([pigpio.pulse(0, 0, value)])
                    spaces_wid[value] = pigpio_pi.wave_create()
                wave[index] = spaces_wid[value]
            else:  # Mark
                if value not in marks_wid:
                    waveform = self._carrier(
                        self.PLAYBACK_PIN, self.FREQ, value)
                    pigpio_pi.wave_add_generic(waveform)
                    marks_wid[value] = pigpio_pi.wave_create()
                wave[index] = marks_wid[value]

        delay = emit_time - time.time()

        if delay > 0.0:
            time.sleep(delay)

        pigpio_pi.wave_chain(wave)

        while pigpio_pi.wave_tx_busy():
            time.sleep(0.002)

        emit_time = time.time() + self.GAP_S

        for i in marks_wid:
            pigpio_pi.wave_delete(marks_wid[i])
        marks_wid = {}

        for i in spaces_wid:
            pigpio_pi.wave_delete(spaces_wid[i])
        spaces_wid = {}

        pigpio_pi.stop()
