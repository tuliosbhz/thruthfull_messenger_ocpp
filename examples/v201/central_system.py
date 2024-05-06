import asyncio
import logging
from datetime import datetime

try:
    import websockets
except ModuleNotFoundError:
    print("This example relies on the 'websockets' package.")
    print("Please install it by running: ")
    print()
    print(" $ pip install websockets")
    import sys

    sys.exit(1)

from ocpp.routing import on
from ocpp.v201 import ChargePoint as cp
from ocpp.v201 import call_result
from ocpp.v201 import call

logging.basicConfig(level=logging.INFO)


class CentralSystem(cp):

    interval = 10
    
    @on("BootNotification")
    def on_boot_notification(self, charging_station, reason, **kwargs):
        #TODO: Add rejection case
        return call_result.BootNotificationPayload(
            current_time=datetime.now().isoformat(), interval=self.interval, status="Accepted"
        )

    @on("Heartbeat")
    def on_heartbeat(self):
        print("Got a Heartbeat!")
        return call_result.HeartbeatPayload(
            current_time=datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        )

async def on_connect(websocket, path):
    """For every new charge point that connects, create a ChargePoint
    instance and start listening for messages.
    """
    try:
        requested_protocols = websocket.request_headers["Sec-WebSocket-Protocol"]
    except KeyError:
        logging.error("Client hasn't requested any Subprotocol. Closing Connection")
        return await websocket.close()
    if websocket.subprotocol:
        logging.info("Protocols Matched: %s | %s", websocket.subprotocol, path)
    else:
        # In the websockets lib if no subprotocols are supported by the
        # client and the server, it proceeds without a subprotocol,
        # so we have to manually close the connection.
        logging.warning(
            "Protocols Mismatched | Expected Subprotocols: %s,"
            " but client supports %s | Closing connection",
            websocket.available_subprotocols,
            requested_protocols,
        )
        return await websocket.close()

    charge_point_id = path.strip("/")
    charge_point = CentralSystem(charge_point_id, websocket)
    logging.info(f"NEW CONNECTION: {charge_point_id}")

    await charge_point.start()


async def main():
    #  deepcode ignore BindToAllNetworkInterfaces: <Example Purposes>
    server = await websockets.serve(
        on_connect, "0.0.0.0", 9002, subprotocols=["ocpp2.0.1"],ping_interval=None
    )

    logging.info("Server Started listening to new connections...")
    await server.wait_closed()


if __name__ == "__main__":
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main())
