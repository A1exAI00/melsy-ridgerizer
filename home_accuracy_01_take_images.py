import time

from src.GCodeSender import GCodeSender, SomeGCodes, DEVICES
from src.Camera import Camera


initial_commands = [
    SomeGCodes.SET_STEPS_PER_UNIT_GCODE,
    SomeGCodes.SET_CURRENT_LIMIT_GCODE,
    SomeGCodes.SET_MAX_FEEDRATE_GCODE,
    SomeGCodes.SET_ACCELERATION_GCODE,
    SomeGCodes.SET_MICROSTEPPING_GCODE,
    SomeGCodes.HOME_X_GCODE,
]

sender = GCodeSender(DEVICES[0])
sender.connect()

camera = Camera()

for gcode in initial_commands:
    response = sender.send_command(gcode)
    print(f"Response: {response}")

for i in range(100):
    sender.send_command(SomeGCodes.HOME_X_GCODE)

    time.sleep(0.3)

    camera.save_image("images/home_accuracy", "image", "png")

sender.close()
camera.close()
