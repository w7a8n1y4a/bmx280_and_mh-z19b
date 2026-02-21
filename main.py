import gc
import ujson as json
import uasyncio as asyncio

import machine

from pepeunit_micropython_client.client import PepeunitClient
from pepeunit_micropython_client.enums import SearchTopicType, SearchScope

from lib.bmx280 import BMx280
from lib.mhz19b import MHZ19B

STATUS_MEASURING = "measuring"
STATUS_ERROR = "error"

last_output_send_time = 0
device_status = STATUS_MEASURING
bmx_sensor = None
mhz_sensor = None


def init_sensors(client):
    global bmx_sensor, mhz_sensor

    if client.settings.FF_WEATHER_SENSOR_ENABLE:
        i2c = machine.SoftI2C(
            scl=machine.Pin(int(client.settings.PIN_BMX_SCL)),
            sda=machine.Pin(int(client.settings.PIN_BMX_SDA))
        )
        bmx_sensor = BMx280(i2c)
        detected = "BME280" if bmx_sensor.is_bme else "BMP280"
        expected = str(client.settings.FF_TYPE_WEATHER_SENSOR).upper()
        if (expected == "BME" and not bmx_sensor.is_bme) or (expected == "BMP" and bmx_sensor.is_bme):
            client.logger.warning(f'Expected {expected}280, detected {detected}')
        client.logger.info(f'Weather sensor: {detected}')

    if client.settings.FF_CO2_SENSOR_ENABLE:
        uart = machine.UART(
            1, baudrate=9600,
            tx=int(client.settings.PIN_MH_Z19B_RX),
            rx=int(client.settings.PIN_MH_Z19B_TX),
            timeout=300
        )
        mhz_sensor = MHZ19B(uart)
        desired_abc = 1 if client.settings.FF_CO2_AUTOCORRECTION else 0
        for attempt in range(5):
            mhz_sensor.set_abc(client.settings.FF_CO2_AUTOCORRECTION)
            abc = mhz_sensor.get_abc_status()
            if abc == desired_abc:
                break
            client.logger.warning(f'ABC set attempt {attempt + 1}: expected {desired_abc}, got {abc}')
        fw = mhz_sensor.get_firmware_version()
        rng = mhz_sensor.get_range()
        client.logger.info(f'MH-Z19B fw={fw} abc={abc} range={rng}')


async def input_handler(client: PepeunitClient, msg):
    global device_status

    parts = msg.topic.split('/')
    if len(parts) != 3:
        return

    topic_name = await client.schema.find_topic_by_unit_node(
        parts[1], SearchTopicType.UNIT_NODE_UUID, SearchScope.INPUT
    )

    if topic_name != 'co2_command/pepeunit':
        return

    if mhz_sensor is None:
        client.logger.warning('CO2 sensor disabled, ignoring command')
        return

    try:
        cmd_data = json.loads(msg.payload)
        command = cmd_data.get('command', '')

        if command == 'zero_calibration':
            mhz_sensor.zero_calibration()
            client.logger.info('Zero point calibration sent (400 ppm)')

        else:
            client.logger.warning(f'Unknown command: {command}')

    except Exception as e:
        client.logger.error(f'Command error: {str(e)}')


async def output_handler(client: PepeunitClient):
    global last_output_send_time, device_status

    current_time = client.time_manager.get_epoch_ms()

    if (current_time - last_output_send_time) < client.settings.PUBLISH_SEND_INTERVAL:
        return

    gc.collect()
    device_status = STATUS_MEASURING

    if bmx_sensor is not None:
        try:
            temp, press, hum = bmx_sensor.read()
            await client.publish_to_topics('temperature/pepeunit', str(temp))
            await client.publish_to_topics('pressure/pepeunit', str(press))
            if hum is not None:
                await client.publish_to_topics('humidity/pepeunit', str(hum))
            client.logger.debug(f'BMx: T={temp} P={press} H={hum}')
        except Exception as e:
            device_status = STATUS_ERROR
            client.logger.error(f'BMx280 error: {str(e)}')

    if mhz_sensor is not None:
        try:
            result = mhz_sensor.read_co2()
            if result is not None:
                co2 = result[0]
                await client.publish_to_topics('co2/pepeunit', str(co2))
                client.logger.debug(f'CO2={co2}')
            else:
                device_status = STATUS_ERROR
                client.logger.warning('MH-Z19B: no valid response')
        except Exception as e:
            device_status = STATUS_ERROR
            client.logger.error(f'MH-Z19B error: {str(e)}')

    await client.publish_to_topics(
        'device_status/pepeunit', json.dumps({"status": device_status})
    )

    last_output_send_time = current_time


async def main_async(client: PepeunitClient):
    client.set_mqtt_input_handler(input_handler)
    client.set_output_handler(output_handler)
    client.subscribe_all_schema_topics()

    init_sensors(client)

    await client.run_main_cycle()


if __name__ == '__main__':
    try:
        asyncio.run(main_async(client))
    except KeyboardInterrupt:
        raise
    except Exception as e:
        client.logger.critical(f"Error with reset: {str(e)}", file_only=True)
        client.restart_device()
