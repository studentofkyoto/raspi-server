import time

import pigpio


class Irrp:
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

    def __init__(self):
        self._last_tick = 0
        self._in_code = False
        self._press1 = []
        self._press2 = []
        self._code = []
        self._fetching_code = False

    def _carrier(self, gpio, frequency, micros):
        wf = []
        cycle = 1000.0 / frequency
        cycles = int(round(micros / cycle))
        on = int(round(cycle / 2.0))
        sofar = 0
        for c in range(cycles):
            target = int(round((c + 1) * cycle))
            sofar += on
            off = target - sofar
            sofar += off
            wf.append(pigpio.pulse(1 << gpio, 0, on))
            wf.append(pigpio.pulse(0, 1 << gpio, off))
        return wf

    def _normalise(self, c):
        entries = len(c)
        p = [0] * entries  # Set all entries not processed.
        for i in range(entries):
            if not p[i]:  # Not processed?
                v = c[i]
                tot = v
                similar = 1.0

                # Find all pulses with similar lengths to the start pulse.
                for j in range(i + 2, entries, 2):
                    if not p[j]:  # Unprocessed.
                        if (c[j] *
                            self.TOLER_MIN) < v < (c[j] *
                                                   self.TOLER_MAX):  # Similar.
                            tot = tot + c[j]
                            similar += 1.0

                # Calculate the average pulse length.
                newv = round(tot / similar, 2)
                c[i] = newv

                # Set all similar pulses to the average value.
                for j in range(i + 2, entries, 2):
                    if not p[j]:  # Unprocessed.
                        if (c[j] *
                            self.TOLER_MIN) < v < (c[j] *
                                                   self.TOLER_MAX):  # Similar.
                            c[j] = newv
                            p[j] = 1

    def _compare(self, p1, p2):
        if len(p1) != len(p2):
            return False

        for i in range(len(p1)):
            v = p1[i] / p2[i]
            if (v < self.TOLER_MIN) or (v > self.TOLER_MAX):
                return False

        for i in range(len(p1)):
            p1[i] = int(round((p1[i] + p2[i]) / 2.0))

        return True

    def _tidy_mark_space(self, recorded, base):

        ms = {}

        rl = len(recorded)
        for i in range(base, rl, 2):
            if recorded[i] in ms:
                ms[recorded[i]] += 1
            else:
                ms[recorded[i]] = 1

        v = None

        for plen in sorted(ms):
            if v is None:
                e = [plen]
                v = plen
                tot = plen * ms[plen]
                similar = ms[plen]

            elif plen < (v * self.TOLER_MAX):
                e.append(plen)
                tot += (plen * ms[plen])
                similar += ms[plen]

            else:
                v = int(round(tot / float(similar)))
                for i in e:
                    ms[i] = v
                e = [plen]
                v = plen
                tot = plen * ms[plen]
                similar = ms[plen]

        v = int(round(tot / float(similar)))
        for i in e:
            ms[i] = v

        rl = len(recorded)
        for i in range(base, rl, 2):
            recorded[i] = ms[recorded[i]]

    def _tidy(self, recorded):
        self._tidy_mark_space(recorded, 0)
        self._tidy_mark_space(recorded, 1)

    def _end_of_code(self):
        if len(self._code) > self.SHORT:
            self._normalise(self._code)
            self._fetching_code = False
        else:
            self._code = []
            print("Short code, probably a repeat, try again")

    def _record(self):
        pi = pigpio.pi()
        if not pi.connected:
            raise Exception("cannot connect to pigpio")
        pi.set_mode(self.RECORD_PIN, pigpio.INPUT)
        pi.set_glitch_filter(self.RECORD_PIN, self.GLITCH)

        def cbf(gpio, level, tick):
            if level != pigpio.TIMEOUT:
                edge = pigpio.tickDiff(self._last_tick, tick)
                self._last_tick = tick

                if self._fetching_code:

                    if (edge > self.PRE_US) and (
                            not self._in_code):  # Start of a code.
                        self._in_code = True
                        # Start watchdog.
                        pi.set_watchdog(gpio, self.POST_MS)

                    # End of a code.
                    elif (edge > self.POST_US) and self._in_code:
                        self._in_code = False
                        pi.set_watchdog(gpio, 0)  # Cancel watchdog.
                        self._end_of_code()

                    elif self._in_code:
                        self._code.append(edge)
            else:
                pi.set_watchdog(gpio, 0)  # Cancel watchdog.
                if self._in_code:
                    self._in_code = False
                    self._end_of_code()

        print("Recording")
        print("Press button")
        self._code = []
        self._fetching_code = True
        pi.callback(self.RECORD_PIN, pigpio.EITHER_EDGE, cbf)
        while self._fetching_code:
            time.sleep(0.1)
        print("Okay")
        return self._code[:]

    def record(self):
        recorded = self._record()
        self._tidy(recorded)
        return recorded

    def record_first(self):
        self._press1 = self._record()
        return self._press1

    def record_confirm(self):
        if not self._press1:
            raise Exception("first press not recorded")

        recorded = []
        for try_count in range(3):
            self._press2 = self._record()
            the_same = self._compare(self._press1, self._press2)
            if the_same:
                recorded = self._press1[:]
                print("Okay")
                break
            else:
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

    def playback(self, code):
        pi = pigpio.pi()
        pi.set_mode(self.PLAYBACK_PIN, pigpio.OUTPUT)
        pi.wave_add_new()
        emit_time = time.time()

        marks_wid = {}
        spaces_wid = {}
        wave = [0] * len(code)

        for i in range(0, len(code)):
            ci = code[i]
            if i & 1:  # Space
                if ci not in spaces_wid:
                    pi.wave_add_generic([pigpio.pulse(0, 0, ci)])
                    spaces_wid[ci] = pi.wave_create()
                wave[i] = spaces_wid[ci]
            else:  # Mark
                if ci not in marks_wid:
                    wf = self._carrier(self.PLAYBACK_PIN, self.FREQ, ci)
                    pi.wave_add_generic(wf)
                    marks_wid[ci] = pi.wave_create()
                wave[i] = marks_wid[ci]

        delay = emit_time - time.time()

        if delay > 0.0:
            time.sleep(delay)

        pi.wave_chain(wave)

        while pi.wave_tx_busy():
            time.sleep(0.002)

        emit_time = time.time() + self.GAP_S

        for i in marks_wid:
            pi.wave_delete(marks_wid[i])
        marks_wid = {}

        for i in spaces_wid:
            pi.wave_delete(spaces_wid[i])
        spaces_wid = {}

        pi.stop()
