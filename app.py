from flask import Flask
import RPi.GPIO as GPIO

PIN = 15
GPIO.setmode(GPIO.BCM)                    
GPIO.setup(PIN,GPIO.OUT)                                

app = Flask(__name__)

@app.route('/on', methods=["GET"])
def gpio_on():
        GPIO.output(PIN, True)

@app.route('/off', methods=["GET"])
def gpio_off():
        GPIO.output(PIN, False)

if __name__ == "__main__":
    app.run(debug=True)