#------------------------------------Imports Used-----------------------------------
from dash import Dash, dcc, html, Input, Output
from dash.dependencies import Input, Output, State
import os
import dash
import dash_daq as daq
import RPi.GPIO as GPIO
import adafruit_dht
from board import *
import smtplib
from paho.mqtt import client as mqtt_client
import random
import datetime
import dash_dangerously_set_inner_html
import time
import sys
import pymysql

#------------------------------------Database Setup---------------------------------
# Connect to MariaDB Platform
try:
    conn = pymysql.connect(
        user="root",
        password="root",
        host="127.0.0.1",
        port=3306,
        database="SmartHome"
    )
except pymysql.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)

# Get Cursor
cur = conn.cursor()

query = "SELECT tag FROM users"
# To execute the SQL query
cur.execute(query)
rows = cur.fetchall()

# query = (f"SELECT * FROM users WHERE tag = `{tagid}`")
# cur.execute(query)
# conn.close()

tagArr=[];

for row in rows :
    print(row)
    tagArr.append(row[0])
#-----------------------------------------------------------------------------------

#-------------------------------------MQTT Setup------------------------------------
# Setting the MQTT Broker Address
broker = '192.168.2.155' #Home
# broker = '192.168.0.148' #School 

# Assigning the subscribe topics for the phase 3 (Photo Resistor)
# and the phase 4 (RFID) + Assigning port number and client_id for MQTT
topic = "light"
topic2 = "tagnumber"
port = 1883
client_id = f'python-mqtt-{random.randint(0, 100)}'
#-----------------------------------------------------------------------------------

#---------------------------------Components Setup----------------------------------
# Implementing GPIO code for the phase 1 (LED) and the phase 2 (DHT11)
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# Implementing GPIO code for the phase 1 (LED)
GPIO.setup(4,GPIO.OUT) #LED Diode

# Implementing GPIO code for the phase 2 (DHT11)
SENSOR_PIN = D17 #DHT11
dht11 = adafruit_dht.DHT11(SENSOR_PIN, use_pulseio=False) #DHT11
GPIO.setup(19,GPIO.OUT) #LED Diode 2
#-----------------------------------------------------------------------------------

# Phase 2 variable to avoid email spamming
emailSent=False

#----------------------------------Dash Page Setup----------------------------------
app = Dash(__name__)

# Page Name
app.title = "IoT Dashboard"
#-----------------------------------------------------------------------------------

#----------------------------------Dashboard Layout---------------------------------
app.layout = html.Div([
# Phase 1 Layout
html.Div([
html.H1('Phase 1'),
html.H3('Toggle the switch to turn on/off the led diode!'),
html.A(html.Img(id="led", height=100, width=100,
src=app.get_asset_url("../assets/images/lightbulb-off.png")),
style = {'position':'absolute', 'top':'120px', 'left':'150px'}),
daq.ToggleSwitch(id='ledswitch', color='green', value=False,
style = {'position':'absolute', 'top':'150px', 'left':'250px'})],
style = {'width': '48.75%', 'height':'250px', 'background-color':'#ADD8E6',
'position':'absolute', 'top':'10px', 'left':'10px', 'box-sizing':'border-box',
'padding-left':'20px'}),
# Phase 2 Layout    
html.Div([
html.H1('Phase 2'),
html.H3('Temperature and Humidity'),
daq.Thermometer(id='thermometer', value= 0, min=0, max=100,
style = {'margin-bottom':'5%', 'position':'absolute', 'top':'120px',
'left':'1300px'}),
daq.Gauge(id='humidity', value= 0, min=0, max=100,
style = {'margin-bottom':'5%', 'position':'absolute', 'top':'120px',
'left':'1400px'}),
html.Div(id='latest-timestamp', style={"padding": "20px"}), 
dcc.Interval(id='interval-component', interval=1*5000, n_intervals=0)],
style = {'width':'48.75%', 'height':'350px', 'background-color':'#FFCCCB',
'float':'right', 'box-sizing':'border-box', 'padding-left':'20px'}),
# Phase 3 Layout     
html.Div([
html.H1('Phase 3'),
html.H3('Photoresistor and LED'),
html.A(html.Img(id="led2", height=100, width=100,
src=app.get_asset_url("../assets/images/lightbulb-off.png")),
style = {'position':'absolute', 'top':'120px', 'left':'150px'}),
html.Div(id='latest-timestamp2', style={"padding":"20px"}),
dcc.Interval(id='interval-component2', interval=1*5000, n_intervals=0),
daq.ToggleSwitch(id='prswitch', color='green', value=False,
style = {'position':'absolute', 'top':'150px', 'left':'250px'})],
style = {'width':'48.75%', 'height':'250px', 'background-color':'#90EE90',
'position':'absolute', 'top':'270px', 'left':'10px', 'box-sizing':'border-box',
'padding-left':'20px'}),
# Phase 4 Layout     
html.Div([
html.H1('Phase 4'),
html.H3('RFID & Database'),
html.Div(id='latest-timestamp3', style={"padding":"20px"}),
dcc.Interval(id='interval-component3', interval=1*5000, n_intervals=0),
daq.ToggleSwitch(id='rfidswitch', color='green', value=False,
style = {'position':'absolute', 'top':'150px', 'left':'250px'})],
style = {'width':'48.75%', 'height':'350px', 'background-color':'#FFA500',
'position':'absolute', 'top':'370px', 'left':'970px','float':'right',
'box-sizing':'border-box', 'padding-left':'10px'})],
style = {'width':'100%', 'height':'100%', 'background-color':'#0B0B45',
'position':'absolute', 'top':'0px', 'left':'0px', 'box-sizing':'border-box',
'padding-right':'10px', 'padding-top':'10px'})
#-----------------------------------------------------------------------------------

                             # Callbacks and Functions

#---------------------------------Start of Phase 1----------------------------------
@app.callback(Output('led', 'src'), Input('ledswitch', 'value'))
def update_led(value):
    if value == True:
        GPIO.output(4, GPIO.HIGH)
        return "../assets/images/lightbulb-on.png"
    elif (value == False):
        GPIO.output(4, GPIO.LOW)
        return "../assets/images/lightbulb-off.png"
    return "../assets/images/lightbulb-off.png"
#----------------------------------End of Phase 1-----------------------------------

#---------------------------------Start of Phase 2----------------------------------
# @app.callback([Output('thermometer', 'value'), Output('humidity', 'value'),
# Output(component_id='latest-timestamp', component_property='children')],
# [Input('interval-component', 'n_intervals')])
def update_thermo(interval):
    temp = dht11.temperature
    humi = dht11.humidity
    if temp > 20:
        if (emailSent == false):
            sender = ['1945421@iotvanier.com']
            receivers = ['1945421@iotvanier.com']

            message = """From: From You <1945421@iotvanier.com>
            To: To Person <to1945421@iotvanier.com>
            Subject: Temperature Sensor

            The temperature is currently warmer than the specified temperature
            threshold, would you like to turn on the fan?
            """

            try:
                smtpObj = smtplib.SMTP('192.168.0.11')
                smtpObj.sendmail(sender, receivers, message)         
                print ("Successfully sent email")
                emailSent = True
            except smtplib.SMTPException:
                print ("Error: unable to send email")
    
            #ADD CODE FOR READING MAIL + COMPARE BY PAYLOAD + RUN MOTOR
    return [temp, humi, html.Span(f"Last updated: {datetime.datetime.now()}")]
#----------------------------------End of Phase 2-----------------------------------

#---------------------------------Start of Phase 3----------------------------------
# @app.callback([Output('led2', 'src'),
# Output(component_id='latest-timestamp2', component_property='children')],
# [Input('interval-component2', 'n_intervals')])
def update_lightint(interval):
    if (lightint < 2500):
        return ["../assets/images/lightbulb-on.png",
        html.Span(f"Light Intensity: {lightint}, Email Sent!")]
    elif (lightint > 2500):
        return ["../assets/images/lightbulb-off.png",
        html.Span(f"Light Intensity: {lightint}")]
#     return [html.Span(f"Light Intensity: {lightint}")]


def connect_mqtt() -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(client_id)
#     client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client

def subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        global lightint
        lightint = int(msg.payload.decode())
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        if (int(msg.payload.decode()) < 2500):
            GPIO.output(19, GPIO.HIGH)
            #Send notification email
            sender = ['1945421@iotvanier.com']
            receivers = ['1945421@iotvanier.com']

#             message = 'Subject: {}\n\n{}'.format(SUBJECT, TEXT)
            SUBJECT = "Light Sensor"
            TEXT = """From: From You <1945421@iotvanier.com>
            To: To Person <to1945421@iotvanier.com>

            The light intensity is currently lower than the specified light
            intensity threshold, turning on the light.
            """
            message = 'Subject: {}\n\n{}'.format(SUBJECT, TEXT)
            try:
                smtpObj = smtplib.SMTP('192.168.0.11')
                smtpObj.sendmail(sender, receivers, message)         
                print ("Successfully sent email")
            except smtplib.SMTPException:
                print ("Error: unable to send email")
            
        elif (int(msg.payload.decode()) > 2500):
            GPIO.output(19, GPIO.LOW)
    client.subscribe(topic)
    client.on_message = on_message
    
def run():
    client = connect_mqtt()
    subscribe(client)
    client.loop_forever()

# Phase 3
@app.callback(Output('latest-timestamp2', 'style'), Input('prswitch', 'value'))
def update_led(value):
    if value == True:
        run()

#----------------------------------End of Phase 3-----------------------------------

#---------------------------------Start of Phase 4----------------------------------
@app.callback([
Output(component_id='latest-timestamp3', component_property='children')],
[Input('interval-component3', 'n_intervals')])
def update_tagint(interval):
        return [html.Span(f"Tag Id: {tagid} | User: {name} | Temperature Threshold: {tempthresh} | Light Threshold: {lightthresh}")]

def subscribe2(client: mqtt_client):
    def on_message(client, userdata, msg):
        global tagid
        global name
        global tempthresh
        global lightthresh
        
        tagid = int(msg.payload.decode())
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        for tag in tagArr:
            if(tag == tagid):
                print("matching tags found")
                query = """SELECT * FROM users WHERE tag = %s"""
                cur.execute(query, tagid)
                rows2 = cur.fetchall()
                for row in rows2 :
                    print(row[1])
                    print(row[2])
                    name = row[2]
                    print(row[3])
                    tempthresh = row[3]
                    print(row[4])
                    lightthresh = row[4]
                #DISPLAY ALL VALUES FROM THAT SPECIFIC USER
                app.layout = html.Div([html.Div('Example Div',
                 style={'background-color':'yellow','width':'100px', 'height':'100px','position':'absolute', 'left':'10px', 'top':'1800px',
                'marginBottom': 50, 'marginTop': 25})])
                
                # SEND NOTIFICATION EMAIL MAILCOW
                t = time.localtime()
                time = time.strftime("%H:%M:%S", t)
                sender = ['1945421@iotvanier.com']
                receivers = ['1945421@iotvanier.com']

                SUBJECT = "RFID Reader"
                TEXT = """From: From You <1945421@iotvanier.com>
                To: To Person <to1945421@iotvanier.com>

                User {name} has accessed the reader at {time}.
                """
                message = 'Subject: {}\n\n{}'.format(SUBJECT, TEXT)
                try:
                    smtpObj = smtplib.SMTP('192.168.0.11')
                    smtpObj.sendmail(sender, receivers, message)         
                    print ("Successfully sent email")
                except smtplib.SMTPException:
                    print ("Error: unable to send email")

    client.subscribe(topic2)
    client.on_message = on_message
    
def run2():
    client = connect_mqtt()
    subscribe2(client)
    client.loop_forever()
    
# Phase 4
@app.callback(Output('latest-timestamp3', 'style'), Input('rfidswitch', 'value'))
def update_rfid(value):
    if value == True:
        run2()    

#----------------------------------End of Phase 4-----------------------------------      

if __name__ == '__main__':
    app.run_server(debug=True)