import time


class MHZ19B:
    """MH-Z19B NDIR CO2 sensor driver over UART (9600 baud, 9-byte binary protocol).
    Includes documented + reverse-engineered commands (RevSpace)."""

    def __init__(self, uart):
        self.uart = uart

    @staticmethod
    def _checksum(data):
        return (0xFF - (sum(data[1:8]) & 0xFF) + 1) & 0xFF

    def _make_cmd(self, cmd_byte, b3=0, b4=0, b5=0, b6=0, b7=0):
        cmd = [0xFF, 0x01, cmd_byte, b3, b4, b5, b6, b7, 0x00]
        cmd[8] = self._checksum(cmd)
        return cmd

    def _send_cmd(self, cmd):
        while self.uart.any():
            self.uart.read()
        self.uart.write(bytes(cmd))
        time.sleep_ms(150)
        resp = self.uart.read(9)
        if resp and len(resp) == 9 and self._checksum(resp) == resp[8]:
            return resp
        return None

    def _send_no_response(self, cmd):
        while self.uart.any():
            self.uart.read()
        self.uart.write(bytes(cmd))

    def read_co2(self):
        """0x86: Returns (co2_ppm, temp_celsius, abc_ticks, abc_cycles) or None.
        temp = byte[4] - 40; abc info in bytes[6..7] (valid when ABC is on)."""
        resp = self._send_cmd(self._make_cmd(0x86))
        if resp and resp[1] == 0x86:
            co2 = resp[2] * 256 + resp[3]
            temp = resp[4] - 40
            return co2, temp, resp[6], resp[7]
        return None

    def read_raw(self):
        """0x84: Raw light sensor data. Returns (raw_light_half, const_32000, extra) or None."""
        resp = self._send_cmd(self._make_cmd(0x84))
        if resp and resp[1] == 0x84:
            raw_light = resp[2] * 256 + resp[3]
            const = resp[4] * 256 + resp[5]
            extra = resp[6] * 256 + resp[7]
            return raw_light, const, extra
        return None

    def read_unclamped(self):
        """0x85: Returns (temp_adc, co2_unclamped, min_light_adc) or None.
        CO2 value before range clamping — useful for diagnostics."""
        resp = self._send_cmd(self._make_cmd(0x85))
        if resp and resp[1] == 0x85:
            temp_adc = resp[2] * 256 + resp[3]
            co2_unclamped = resp[4] * 256 + resp[5]
            min_light = resp[6] * 256 + resp[7]
            return temp_adc, co2_unclamped, min_light
        return None

    def zero_calibration(self):
        """0x87: Zero point calibration. Sensor must be at ~400ppm for 20+ min."""
        self._send_no_response(self._make_cmd(0x87))

    def span_calibration(self, span_ppm):
        """0x88: Span point calibration at known concentration."""
        self._send_no_response(self._make_cmd(0x88, b3=(span_ppm >> 8) & 0xFF, b4=span_ppm & 0xFF))

    def set_abc(self, on):
        """0x79: ABC logic on (0xA0) / off (0x00)."""
        self._send_cmd(self._make_cmd(0x79, b3=0xA0 if on else 0x00))

    def get_abc_status(self):
        """0x7D: Returns ABC status (1=enabled, 0=disabled) or None."""
        resp = self._send_cmd(self._make_cmd(0x7D))
        if resp and resp[1] == 0x7D:
            return resp[7]
        return None

    def set_range(self, range_ppm):
        """0x99: Set detection range (2000/5000/10000 ppm). Note: params in b[4..7]."""
        self._send_cmd(self._make_cmd(0x99, b5=(range_ppm >> 24) & 0xFF,
                                      b6=(range_ppm >> 8) & 0xFF, b7=range_ppm & 0xFF))

    def get_range(self):
        """0x9B: Returns current detection range in ppm or None."""
        resp = self._send_cmd(self._make_cmd(0x9B))
        if resp and resp[1] == 0x9B:
            return (resp[2] << 24) | (resp[3] << 16) | (resp[4] << 8) | resp[5]
        return None

    def get_firmware_version(self):
        """0xA0: Returns firmware version string (e.g. '0430') or None."""
        resp = self._send_cmd(self._make_cmd(0xA0))
        if resp and resp[1] == 0xA0:
            try:
                return bytes(resp[2:6]).decode('ascii')
            except Exception:
                return '{:02X}{:02X}{:02X}{:02X}'.format(resp[2], resp[3], resp[4], resp[5])
        return None

    def set_cycle_length(self, seconds):
        """0x7E: Set measurement cycle length in seconds (default 5). b[3]=2 to write."""
        resp = self._send_cmd(self._make_cmd(0x7E, b3=2, b4=(seconds >> 8) & 0xFF, b5=seconds & 0xFF))
        if resp and resp[1] == 0x7E:
            return resp[2] * 256 + resp[3]
        return None

    def get_cycle_length(self):
        """0x7E: Read current measurement cycle length in seconds."""
        resp = self._send_cmd(self._make_cmd(0x7E, b3=0))
        if resp and resp[1] == 0x7E:
            return resp[2] * 256 + resp[3]
        return None

    def reset(self):
        """0x8D: MCU reset."""
        self._send_no_response(self._make_cmd(0x8D))

    def set_dac_bounds(self, low_mv, high_mv):
        """0xA4: Set DAC analog output bounds in mV. Returns True on success."""
        resp = self._send_cmd(self._make_cmd(0xA4, b3=(low_mv >> 8) & 0xFF, b4=low_mv & 0xFF,
                                             b5=(high_mv >> 8) & 0xFF, b6=high_mv & 0xFF))
        if resp and resp[1] == 0xA4:
            return resp[2] == 1
        return False

    def get_dac_bounds(self):
        """0xA5: Returns (low_mv, high_mv) DAC output bounds or None."""
        resp = self._send_cmd(self._make_cmd(0xA5))
        if resp and resp[1] == 0xA5:
            low = resp[2] * 256 + resp[3]
            high = resp[4] * 256 + resp[5]
            return low, high
        return None
