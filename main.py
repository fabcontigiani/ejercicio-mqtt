from settings import ssid, wifi_pw, server
from mqtt_as import MQTTClient, config
import asyncio
import machine
id = ""
for b in machine.unique_id():
  id += "{:02X}".format(b)
print(f"ID: {id}")
import ujson as json
import dht
sensor = dht.DHT11(machine.Pin(15))

datos = {
    "setpoint": None,
    "modo": None,
    "periodo": None,
    "rele": None,
}

parametros_no_volatiles = ("setpoint", "modo", "rele", "destello", "periodo")

# Local configuration
config['ssid'] = ssid  # Optional on ESP8266
config['wifi_pw'] = wifi_pw
config['server'] = server  # Change to suit e.g. 'iot.eclipse.org'

async def messages(client):  # Respond to incoming messages
    # If MQTT V5is used this would read
    # async for topic, msg, retained, properties in client.queue:
    async for topic, msg, retained in client.queue:
        # print(topic.decode(), msg.decode(), retained)
        mensaje = json.loads(msg.decode())
        for key, value in mensaje.items():
            if (key in parametros_no_volatiles) and (topic.decode() == key): # TODO: arreglar verificacion topic == key
                datos[key] = value

async def up(client):  # Respond to connectivity being (re)established
    while True:
        await client.up.wait()  # Wait on an Event
        client.up.clear()
        # await client.subscribe(f"{id}/setpoint", 1)  # renew subscriptions
        for parametro in parametros_no_volatiles:
            await client.subscribe(f"{id}/{parametro}", 1)  # renew subscriptions

async def main(client):
    await client.connect()
    for coroutine in (up, messages):
        asyncio.create_task(coroutine(client))
    n = 0
    while True:
        await asyncio.sleep(5)
        sensor.measure()
        print('publish', n)
        # If WiFi is down the following will pause for the duration.
        datos["temperatura"] = sensor.temperature()
        datos["humedad"] = sensor.humidity()
        cadena = f"{json.dumps(datos)}"
        print(cadena)
        await client.publish(id, cadena, qos = 1)
        n += 1

config["queue_len"] = 1  # Use event interface with default queue size
MQTTClient.DEBUG = True  # Optional: print diagnostic messages  # type: ignore 
client = MQTTClient(config)
try:
    asyncio.run(main(client))
finally:
    client.close()  # Prevent LmacRxBlk:1 errors