from machine import Pin, PWM
import time

# Hardware Setup
servo = PWM(Pin(13), freq=50)
ir_sensor = Pin(12, Pin.IN) 

def move_servo(angle):
    duty = int(26 + (angle / 180) * (128 - 26))
    servo.duty(duty)

print("Task 3: IR Control Active...")

while True:
    if ir_sensor.value() == 0: # Object detected
        print("Object Detected! Opening...")
        move_servo(90)
        time.sleep(2)
        print("Closing...")
        move_servo(0)
        time.sleep(1) # Cool-down to prevent double-trigger
    time.sleep(0.1)