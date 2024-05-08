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

from messages_handler import heartbet_handler
from auxiliar_functions.on_cp_connect_in_csms import on_connect


class CentralSystem(cp):

    interval = 10
    
    @on("BootNotification")
    def on_boot_notification(self, charging_station, reason, **kwargs):
        #TODO: Add rejection case
        #heartbet_handler.on_hearbeat_at_csms()
        return call_result.BootNotificationPayload(
            current_time=datetime.now().isoformat(), interval=self.interval, status="Accepted"
        )

    @on("Heartbeat")
    def on_heartbeat(self):
        print("Got a Heartbeat!")
        return call_result.HeartbeatPayload(
            current_time=datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        )


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
