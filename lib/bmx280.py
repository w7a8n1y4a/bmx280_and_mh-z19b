import struct


class BMx280:
    """BMP280/BME280 I2C driver. Auto-detects chip type via ID register."""

    def __init__(self, i2c, addr=0x76):
        self.i2c = i2c
        self.addr = addr

        chip_id = i2c.readfrom_mem(addr, 0xD0, 1)[0]
        self.is_bme = chip_id == 0x60

        cal = i2c.readfrom_mem(addr, 0x88, 24)
        (self.T1, self.T2, self.T3,
         self.P1, self.P2, self.P3, self.P4, self.P5,
         self.P6, self.P7, self.P8, self.P9) = struct.unpack('<HhhHhhhhhhhh', cal)

        if self.is_bme:
            self.H1 = i2c.readfrom_mem(addr, 0xA1, 1)[0]
            h = i2c.readfrom_mem(addr, 0xE1, 7)
            self.H2 = struct.unpack_from('<h', h, 0)[0]
            self.H3 = h[2]
            self.H4 = (h[3] << 4) | (h[4] & 0x0F)
            if self.H4 > 2047:
                self.H4 -= 4096
            self.H5 = (h[5] << 4) | ((h[4] >> 4) & 0x0F)
            if self.H5 > 2047:
                self.H5 -= 4096
            self.H6 = struct.unpack_from('<b', h, 6)[0]
            i2c.writeto_mem(addr, 0xF2, b'\x01')

        i2c.writeto_mem(addr, 0xF5, b'\x00')
        i2c.writeto_mem(addr, 0xF4, b'\x27')

    def read(self):
        n = 8 if self.is_bme else 6
        d = self.i2c.readfrom_mem(self.addr, 0xF7, n)

        raw_t = (d[3] << 12) | (d[4] << 4) | (d[5] >> 4)
        v1 = (raw_t / 16384.0 - self.T1 / 1024.0) * self.T2
        v2 = ((raw_t / 131072.0 - self.T1 / 8192.0) ** 2) * self.T3
        tf = v1 + v2
        temp = tf / 5120.0

        raw_p = (d[0] << 12) | (d[1] << 4) | (d[2] >> 4)
        v1 = tf / 2.0 - 64000.0
        v2 = v1 * v1 * self.P6 / 32768.0
        v2 = v2 + v1 * self.P5 * 2.0
        v2 = v2 / 4.0 + self.P4 * 65536.0
        v1 = (self.P3 * v1 * v1 / 524288.0 + self.P2 * v1) / 524288.0
        v1 = (1.0 + v1 / 32768.0) * self.P1
        if v1 == 0:
            press = 0.0
        else:
            press = 1048576.0 - raw_p
            press = (press - v2 / 4096.0) * 6250.0 / v1
            v1 = self.P9 * press * press / 2147483648.0
            v2 = press * self.P8 / 32768.0
            press = (press + (v1 + v2 + self.P7) / 16.0) / 100.0

        hum = None
        if self.is_bme:
            raw_h = (d[6] << 8) | d[7]
            h = tf - 76800.0
            if h != 0:
                h = (raw_h - (self.H4 * 64.0 + self.H5 / 16384.0 * h)) * \
                    (self.H2 / 65536.0 * (1.0 + self.H6 / 67108864.0 * h *
                     (1.0 + self.H3 / 67108864.0 * h)))
                hum = h * (1.0 - self.H1 * h / 524288.0)
                hum = max(0.0, min(100.0, hum))
            else:
                hum = 0.0

        return (
            round(temp, 2),
            round(press, 2),
            round(hum, 2) if hum is not None else None
        )
