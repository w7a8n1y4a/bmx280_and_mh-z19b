# BME280 and MH-Z19B

Parameter | Implementation
-- | --
Description | Считывает температуру, давление и влажность с датчика `BME280`/`BMP280` по `I2C`, а также концентрацию `CO2` с датчика `MH-Z19B` по `UART`. Публикует показания в `MQTT` топики. Поддерживает команду калибровки нулевой точки `CO2` датчика
Lang | `Micropython`
Hardware | `esp32`, `esp32c3`, `esp32s3`, `BME280`, `BMP280`, `MH-Z19B`
Firmware | [ESP32_GENERIC-v1.27.0-PEPEUNIT-v1.1.1.bin](https://git.pepemoss.com/api/v4/projects/296/packages/generic/firmware/1.1.1/ESP32_GENERIC-v1.27.0-PEPEUNIT-v1.1.1.bin), [ESP32_GENERIC_S3-v1.27.0-PEPEUNIT-v1.1.1.bin](https://git.pepemoss.com/api/v4/projects/296/packages/generic/firmware/1.1.1/ESP32_GENERIC_S3-v1.27.0-PEPEUNIT-v1.1.1.bin), [ESP32_GENERIC_C3-v1.27.0-PEPEUNIT-v1.1.1.bin](https://git.pepemoss.com/api/v4/projects/296/packages/generic/firmware/1.1.1/ESP32_GENERIC_C3-v1.27.0-PEPEUNIT-v1.1.1.bin)
Stack | `pepeunit_micropython_client`
Version | 1.1.1
License | AGPL v3 License
Authors | Ivan Serebrennikov <admin@silberworks.com>

## Schema

<div align="center"><img align="center" src="https://minio.pepemoss.com/public-data/image/bmx280_and_mh-z19b.png"></div>

## Physical IO

- `client.settings.PIN_BMX_SCL` - Вывод `SCL` шины `I2C` для датчика `BME280`/`BMP280`
- `client.settings.PIN_BMX_SDA` - Вывод `SDA` шины `I2C` для датчика `BME280`/`BMP280`
- `client.settings.PIN_MH_Z19B_TX` - Вывод `TX` `UART` для датчика `MH-Z19B`
- `client.settings.PIN_MH_Z19B_RX` - Вывод `RX` `UART` для датчика `MH-Z19B`

## Env variable assignment

1. `FF_TYPE_WEATHER_SENSOR` - Тип датчика погоды: `bme` или `bmp`
2. `FF_CO2_SENSOR_ENABLE` - Включить датчик CO2: `true` или `false`
3. `FF_CO2_AUTOCORRECTION` - Включить автокалибровку (ABC) датчика CO2: `true` или `false`
4. `FF_WEATHER_SENSOR_ENABLE` - Включить датчик погоды: `true` или `false`
5. `PIN_BMX_SCL` - Номер пина `SCL` шины `I2C` для `BME280`/`BMP280`
6. `PIN_BMX_SDA` - Номер пина `SDA` шины `I2C` для `BME280`/`BMP280`
7. `PIN_MH_Z19B_TX` - Номер пина `TX` `UART` для `MH-Z19B`
8. `PIN_MH_Z19B_RX` - Номер пина `RX` `UART` для `MH-Z19B`
9. `PUBLISH_SEND_INTERVAL` - Интервал отправки показаний в миллисекундах
10. `PUC_WIFI_SSID` - Имя сети `WiFi`
11. `PUC_WIFI_PASS` - Пароль от сети `WiFi`

## Assignment of Device Topics

- `co2_command/pepeunit` - Принимает JSON-команду для датчика CO2 (входящий), например `{"command": "zero_calibration"}` для калибровки нулевой точки (400 ppm)
- `temperature/pepeunit` - Публикует значение температуры в °C (исходящий)
- `pressure/pepeunit` - Публикует значение атмосферного давления в Па (исходящий)
- `humidity/pepeunit` - Публикует значение влажности в % (исходящий, только для `BME280`)
- `co2/pepeunit` - Публикует концентрацию CO2 в ppm (исходящий)
- `device_status/pepeunit` - Публикует статус устройства в формате JSON: `{"status": "measuring"}` или `{"status": "error"}` (исходящий)

## Work algorithm

1. Подключение к `WiFi`
2. Подключение к `MQTT` Брокеру
3. Синхронизация времени по `NTP`
4. Инициализация датчика `BME280`/`BMP280` по `I2C` (если `FF_WEATHER_SENSOR_ENABLE` = `true`)
5. Инициализация датчика `MH-Z19B` по `UART` и настройка автокалибровки (если `FF_CO2_SENSOR_ENABLE` = `true`)
6. Подписка на входящие `MQTT` топики
7. Периодическое считывание показаний датчиков и публикация в соответствующие топики с интервалом `PUBLISH_SEND_INTERVAL`
8. При получении команды в `co2_command/pepeunit`: выполнение калибровки нулевой точки датчика `MH-Z19B`
9. Публикация статуса устройства (`measuring` или `error`) после каждого цикла измерений
10. Датчику `MH-Z19B` при работе в режиме автокалибровки, требуется хотябы 1 раз в день дышать свежим воздухом, они принимает минимальное значение за день как эталон 400 ppm

## Installation

1. Установите образ `Micropython` указанный в `firmware` на одну из платформ, например для `esp32` как это сделано в [руководстве](https://micropython.org/download/ESP32_GENERIC/)
2. Создайте `Unit` в `Pepeunit`
3. Установите переменные окружения в `Pepeunit`
4. Скачайте архив c программой из `Pepeunit`
5. Распакуйте архив в директорию
6. Загрузите файлы из директории на физическое устройство, например командой: `ampy -p /dev/ttyUSB0 -b 115200 put ./ .`
7. Запустить устройство нажатием кнопки `reset`
