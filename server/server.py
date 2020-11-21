from flask import Flask, render_template
import sys
import serial
import datetime
from datetime import timedelta
from threading import Thread
from time import sleep
from car import Car
from crccheck.crc import Crc32, CrcXmodem
from crccheck.checksum import Checksum32
from math import sin, cos, sqrt, atan2, radians
from geographiclib.geodesic import Geodesic

app = Flask(__name__)

Mazda = None
rx_port = None

def get_distance_in_m(lat1,lng1,lat2,lng2):
    # approximate radius of earth in km
    R = 6373.0

    lat1 = radians(lat1)
    lng1 = radians(lng1)
    lat2 = radians(lat2)
    lng2 = radians(lng2)

    dlon = lng2 - lng1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c * 1000

def orientation(lat1,lng1,lat2,lng2): # each point is a tuple of (lon, lat)
    azi = (
        Geodesic.WGS84.Inverse(
            lat2, 
            lng2,
            lat1,
            lng1,
        )['azi1'] % 360
    )
    ranges = {
        (0, 11.25): 'N',
        (11.25, 33.75): 'NNE',
        (33.75, 56.25): 'NE',
        (56.25, 78.75): 'ENE',
        (78.75, 101.25): 'E',
        (101.25, 123.75): 'ESE',
        (123.75, 146.25): 'SE',
        (146.25, 168.75): 'SSE',
        (168.75, 191.25): 'S',
        (191.25, 213.75): 'SSW',
        (213.75, 236.25): 'SW',
        (236.25, 258.75): 'WSW',
        (258.75, 281.25): 'W',
        (281.25, 303.75): 'WNW',
        (303.75, 326.25): 'NW',
        (326.25, 348.75): 'NNW',
        (348.75, 360): 'N',
    }
    for i in ranges.keys():
        if i[0] < azi <= i[1]:
            return ranges[i]

@app.route('/')
def index():
    # calculate last seen time
    last_seen_message = "Last Message Received: "
    if Mazda.last_seen is not None:
        time_delta = datetime.datetime.now() - Mazda.last_seen
        if time_delta.days > 1:
            last_seen_message += "{} day(s) ago".format(int(time_delta.days))
        elif time_delta.seconds / 3600 > 1:
            last_seen_message += "{} hour(s) ago".format(int(time_delta.seconds / 3600))
        elif time_delta.seconds / 60 > 1:
            last_seen_message += "{} min(s) ago".format(int(time_delta.seconds / 60))
        else:
            last_seen_message += "{} second(s) ago".format(int(time_delta.seconds))
    else:
        last_seen_message += "Never"

    status_message = None
    if rx_port.isOpen():
        if Mazda.last_seen is not None and Mazda.speed is not None:
            if Mazda.speed < 10:
                distance=get_distance_in_m(Mazda.lat,Mazda.lng,49.229199,-122.692631)
                compass=orientation(Mazda.lat,Mazda.lng,49.229199,-122.692631)
                status_message = "Mazda is Parked {} meters {}".format(int(distance),compass)
            else:
                status_message = "Mazda is Gone"
        else:
            status_message = "Mazda Status is Unknown"
    else:
        status_message = "Receiver is Disconnected"

    return render_template('index.html', 
    lat=Mazda.lat,
    lng=Mazda.lng,
    last_seen_message = last_seen_message,
    status_message = status_message,
    error_message = Mazda.error_message
    )

def threaded_function(com_port, baud_rate):
    global rx_port
    while True:
        try:
            if rx_port.isOpen() is False:
                print("Opening port")
                rx_port = serial.Serial(com_port, baud_rate, timeout=None)
            raw_line = rx_port.readline().strip()
            print("Received message: {}".format(raw_line))
            Mazda.last_seen = datetime.datetime.now()
            data_array = raw_line.split()
            if len(data_array) == 4:
                checksum = data_array[3]
                data_line = raw_line[0:len(raw_line)-len(data_array[3])]
                crc = Crc32.calc(data_line)
                if hex(crc)[2:].upper() == checksum.decode("utf-8"):
                    Mazda.lat = float(data_array[0])
                    Mazda.lng = float(data_array[1])
                    Mazda.speed = float(data_array[2])
                    Mazda.error_message = None
                else:
                    Mazda.error_message = "Could not decode last message"
            else:
                Mazda.error_message = raw_line.decode("utf-8")
        except Exception as err:
            print("Closing port due to exception: {}".format(err))
            rx_port.close()
            sleep(5)
            pass

if __name__ == '__main__':
    Mazda = Car()
    rx_port = serial.Serial()
    com_port = "COM12"
    baud_rate = 9600
    if len(sys.argv) >= 3:
        com_port = sys.argv[1]
        baud_rate = sys.argv[2]
    print("Starting server on port {} with baud rate of {}".format(com_port, baud_rate))
    thread = Thread(target = threaded_function, args=(com_port, baud_rate,))
    thread.start()
    app.run(debug=False, host='0.0.0.0')