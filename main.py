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
    "periodo": 5,
    "rele": None,
}

param_no_vol = ("setpoint", "modo", "rele", "periodo")
led = machine.Pin("LED", machine.Pin.OUT)
output_pin = machine.Pin(22, machine.Pin.OUT, value=1) # Activo en bajo

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
            try:
                assert topic.decode() == id + "/" + key
            except AssertionError:
                print("Topic no coincide con key")
                continue

            if key in param_no_vol:

                if key == "rele":
                    try: 
                        assert datos["modo"] == "manual"
                        try:
                            assert value in (0, 1)
                            datos[key] = value # type: ignore
                            output_pin.value(not value) # Activo en bajo
                        except AssertionError:
                            print("Valor de relé incorrecto")
                    except AssertionError:
                        print("Rele no está en modo manual")
                else:
                    datos[key] = value
                    

                if key == "rele":
                    try: 
                        assert datos["modo"] == "manual"
                        try:
                            assert value in (0, 1)
                            datos[key] = value # type: ignore
                            output_pin.value(not value) # Activo en bajo
                        except AssertionError:
                            print("Valor de relé incorrecto")
                    except AssertionError:
                        print("Rele no está en modo manual")
                else:
                    datos[key] = value # type: ignore
                    
                try:
                    with open('savedata.json', 'w') as f:
                        json.dump({k: datos[k] for k in param_no_vol}, f)
                except:
                    print("Error! No se pudo guardar")


            elif key == "destello":
                asyncio.create_task(destello())

async def medir():
    sensor.measure()
    datos["temperatura"] = sensor.temperature()
    datos["humedad"] = sensor.humidity()

async def destello():
    led.on()
    await asyncio.sleep(2)
    led.off()

async def up(client):  # Respond to connectivity being (re)established
    while True:
        await client.up.wait()  # Wait on an Event
        client.up.clear()
        # await client.subscribe(f"{id}/setpoint", 1)  # renew subscriptions
        for parametro in param_no_vol + ("destello",):
            await client.subscribe(f"{id}/{parametro}", 1)  # renew subscriptions

async def main(client):
    await client.connect()
    for coroutine in (up, messages):
        asyncio.create_task(coroutine(client))
    n = 0
    while True:
        await asyncio.sleep(datos["periodo"])
        asyncio.create_task(medir())

        if datos["modo"] == "automatico":
            try:
                assert isinstance(datos["setpoint"], int)
                if datos["temperatura"] > datos["setpoint"]:
                    datos["rele"] = 1 # type: ignore
                else:
                    datos["rele"] = 0 # type: ignore
                output_pin.value(not datos["rele"]) # Activo en bajo
            except AssertionError:
                print("Relé en modo automatico pero setpoint no configurado")

        print('publish', n)
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