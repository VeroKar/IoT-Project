#------------------------------------Imports Used-----------------------------------
from dash import Dash, dcc, html, Input, Output, ctx
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
from datetime import datetime
import dash_dangerously_set_inner_html
import time
import sys
import pymysql
import email
import imaplib

tempthresh = 30 
lightthresh = 2000

global theme
theme = False

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
#broker = '192.168.2.155' #Home
broker = '192.168.0.148' #School 

# Assigning the subscribe topics for the phase 3 (Photo Resistor)
# and the phase 4 (RFID) + Assigning port number and client_id for MQTT
topic = "light"
topic2 = "tagnumber"
port = 1883
client_id = f'python-mqtt-{random.randint(0, 100)}'
client_id2 = f'python-mqtt-{random.randint(0, 100)}'
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

#Implementing GPIO code for the phase 2 (Motor)
Motor1 = 13 # Enable Pin 22
Motor2 = 6 # Input Pin 27
Motor3 = 5 # Input Pin 17
GPIO.setup(Motor1,GPIO.OUT)
GPIO.setup(Motor2,GPIO.OUT)
GPIO.setup(Motor3,GPIO.OUT)
#-----------------------------------------------------------------------------------

# Phase 2 variable to avoid email spamming
sent = False

#----------------------------------Dash Page Setup----------------------------------
app = Dash(__name__)

# Page Name
app.title = "IoT Dashboard"
#-----------------------------------------------------------------------------------

#----------------------------------Dashboard Layout---------------------------------
app.layout = html.Div([
# header
html.Div([
html.H1('IoT Dashboard', id='h1', style={'color':'white', 'text-align':'center'})],id='h',
style = {'width': '98%', 'height':'10%', 'background-color':'#203354', 'border':'2px solid','border-color':'#FFFFFF', 'border-radius':'10px',
'position':'absolute', 'top':'2.5%', 'left':'1%', 'box-sizing':'border-box',
'padding-left':'20px', 'padding-right':'20px'}),
# User Info
html.Div([
html.H1('User Information', id='uinf', style={'color':'white', 'text-align':'center'}),
html.Div([html.Img(id="user", height="100", width="100",
src=app.get_asset_url("../assets/images/user.png"))], style={'text-align':'center'}),
html.H3('Tag Id: ', id='ut', style={'color':'white'}),
dcc.Input(id="tagid", readOnly=True, style={'height':'2.5%', 'width':'95%'}),
html.H3('User: ', id='uu',style={'color':'white', 'margin-top':'10%'}),
dcc.Input(id="username", readOnly=True, style={'height':'2.5%', 'width':'95%'}),
html.H3('Temperature Threshold: ', id='utemp',style={'color':'white', 'margin-top':'10%'}),
dcc.Input(id="usertemp", readOnly=True, style={'height':'2.5%', 'width':'95%'}),
html.H3('Light Threshold: ', id='uthr',style={'color':'white', 'margin-top':'10%'}),
dcc.Input(id="userlight", readOnly=True, style={'height':'2.5%', 'width':'95%'})],id='u',
style = {'width': '17.5%', 'height':'60.5%', 'background-color':'#203354', 'border':'2px solid','border-color':'#FFFFFF', 'border-radius':'10px',
'position':'absolute', 'top':'15%', 'left':'1%', 'box-sizing':'border-box',
'padding-left':'20px', 'padding-right':'20px'}), 
# Phase 1 Layout
html.Div([
html.H1('Phase 1', id='p1t', style={'color':'white'}),
html.H3('Toggle the switch to turn on/off the led diode!', id='p1st', style={'color':'white'}),
html.Img(id="led", height=100, width=100,
src=app.get_asset_url("../assets/images/lightbulb-off.png"),
style = {'position':'absolute', 'top':'52%', 'left':'25%'}),
daq.ToggleSwitch(id='ledswitch', color='#03a9f4', value=False,
style = {'color':'white','position':'absolute', 'top':'64%', 'left':'60%'})], id='p1',
style = {'width': '39.25%', 'height':'40%', 'background-color':'#203354', 'border':'2px solid','border-color':'#FFFFFF', 'border-radius':'10px',
'position':'absolute', 'top':'57.5%', 'left':'19.5%', 'box-sizing':'border-box',
'padding-left':'20px'}),
# Phase 2 Layout    
html.Div([
html.H1('Phase 2', id='p2t', style={'color':'white'}),
html.H3('Temperature and Humidity', id='p2st', style={'color':'white'}),
daq.Thermometer(id='thermometer', color='#FE8B02', value= 0, min= 0, max= 30, width=20, height=150, showCurrentValue=True, scale={'interval':5}, 
style = {'margin-bottom':'5%', 'position':'absolute', 'top':'22%',
'left':'30%'}),
daq.Gauge(color='#03a9f4', id='humidity', value= 0, min=0, max=100, showCurrentValue=True, 
style = {'margin-bottom':'5%', 'position':'absolute', 'top':'22.5%',
'left':'50%'}),
html.Div(id='latest-timestamp', style={"padding": "20px"}), 
dcc.Interval(id='interval-component', interval=1*5000, n_intervals=0)], id='p2',
style = {'width':'58%', 'height':'40.5%', 'background-color':'#203354', 'border':'2px solid','border-color':'#FFFFFF', 'border-radius':'10px',
'position':'absolute', 'top':'15%', 'left':'19.5%',
'box-sizing':'border-box', 'padding-left':'20px'}),
# Phase 3 Layout     
html.Div([
html.H1('Phase 3', id='p3t',style={'color':'white'}),
html.H3('Photoresistor and LED', id='p3st',style={'color':'white'}),
html.A(html.Img(id="led2", height=100, width=100,
src=app.get_asset_url("../assets/images/lightbulb-off.png")),
style = {'position':'absolute', 'top':'52%', 'left':'25%'}),
html.Div(id='latest-timestamp2', style={"padding":"20px"}),
dcc.Interval(id='interval-component2', interval=1*5000, n_intervals=0),
daq.ToggleSwitch(id='prswitch', color='#03a9f4', value=False,
style = {'position':'absolute', 'top':'65%', 'left':'60%'})], id='p3',
style = {'width':'39.25%', 'height':'40%', 'background-color':'#203354', 'border':'2px solid','border-color':'#FFFFFF', 'border-radius':'10px',
'position':'absolute', 'top':'57.5%', 'left':'59.75%', 'box-sizing':'border-box',
'padding-left':'20px'}),
# Phase 4 Layout     
html.Div([
html.H1('Phase 4', id='p4t', style={'color':'white'}),
html.H3('RFID & Database', id='p4st', style={'color':'white'}),
html.Div(id='latest-timestamp3', style={"padding":"20px"}),
dcc.Interval(id='interval-component3', interval=1*5000, n_intervals=0),
daq.ToggleSwitch(id='rfidswitch', color='#03a9f4', value=False,
style = {'position':'absolute', 'top':'67.5%', 'left':'42%'})],id='p4',
style = {'width':'17.5%', 'height':'20%', 'background-color':'#203354', 'border':'2px solid','border-color':'#FFFFFF', 'border-radius':'10px',
'position':'absolute', 'top':'77.5%', 'left':'1%',
'box-sizing':'border-box', 'padding-left':'10px'}),
# Light Mode     
html.Div([
html.H1('Theme', id='tt', style={'color':'white'}),
html.H3('Press on the button to enable light mode', id='tst',style={'color':'white'}),
html.Button('Light Mode', id='mode', n_clicks=0, style={'width':'20%','height':'15%','color':'white','position':'absolute', 'top':'52%', 'left':'40%',
'background-color':'#232b2b', 'border': '2px solid white', 'border-radius':'6px','cursor':'pointer'})], id='t',
style = {'width':'20.5%', 'height':'40.5%', 'background-color':'#203354', 'border':'2px solid','border-color':'#FFFFFF', 'border-radius':'10px',
'position':'absolute', 'top':'15%', 'left':'78.5%',
'box-sizing':'border-box', 'padding-left':'10px'})], id='maindiv',
style = {'width':'100%', 'height':'100%', 'background-color':'#152238',
'position':'absolute', 'top':'0px', 'left':'0px', 'box-sizing':'border-box',
'padding-left':'20px'})
#-----------------------------------------------------------------------------------

                             # Callbacks and Functions
                             
#---------------------------------Start of Theme----------------------------------
@app.callback([
    #header
    Output('h', 'style'),
    Output('h1', 'style'),
    #root div
    Output('maindiv', 'style'),
    #user info
    Output('u', 'style'),
    Output('uinf', 'style'),
    Output('ut', 'style'),
    Output('uu', 'style'),
    Output('utemp', 'style'),
    Output('uthr', 'style'),
    #phase 1
    Output('p1', 'style'),
    Output('p1t', 'style'),
    Output('p1st', 'style'),
    #phase 2
    Output('p2', 'style'),
    Output('p2t', 'style'),
    Output('p2st', 'style'),
    #phase 3
    Output('p3', 'style'),
    Output('p3t', 'style'),
    Output('p3st', 'style'),
    #Output('latest-timestamp2','style'),
    #phase 4
    Output('p4', 'style'),
    Output('p4t', 'style'),
    Output('p4st', 'style'),
    #theme
    Output('t', 'style'),
    Output('tt', 'style'),
    Output('tst', 'style'),
    Output('mode', 'style')],          
    Input('mode', 'n_clicks'))
def update_background(n_clicks):
    global theme 
    if (theme == False):
        theme = True
        
        return [
        #header
        {'width': '98%', 'height':'10%', 'background-color':'white', 'border':'2px solid','border-color':'black', 'border-radius':'10px',
        'position':'absolute', 'top':'2.5%', 'left':'1%', 'box-sizing':'border-box',
        'padding-left':'20px', 'padding-right':'20px'},        
        {'color':'black', 'text-align':'center'},    
        #main div
        {"backgroundColor": "#d3d3d3", "width":"100%", "height":"100%", 'position':'absolute', 'top':'0px', 'left':'0px'},
        #user info
        {'width': '17.5%', 'height':'60.5%', 'background-color':'white', 'border':'2px solid','border-color':'black', 'border-radius':'10px',
        'position':'absolute', 'top':'15%', 'left':'1%', 'box-sizing':'border-box',
        'padding-left':'20px', 'padding-right':'20px'},
        {'color':'black'},
        {'color':'black'},
        {'color':'black'},
        {'color':'black'},
        {'color':'black'},
        #phase 1
        {'width': '39.25%', 'height':'40%', 'background-color':'white', 'border':'2px solid','border-color':'black', 'border-radius':'10px',
        'position':'absolute', 'top':'57.5%', 'left':'19.5%', 'box-sizing':'border-box',
        'padding-left':'20px'},
        {'color':'black'},
        {'color':'black'},
        #phase 2
        {'width':'58%', 'height':'40.5%', 'background-color':'white', 'border':'2px solid','border-color':'black', 'border-radius':'10px',
        'position':'absolute', 'top':'15%', 'left':'19.5%',
        'box-sizing':'border-box', 'padding-left':'20px'},        
        {'color':'black'},
        {'color':'black'},
        #phase 3
        {'width':'39.25%', 'height':'40%', 'background-color':'white', 'border':'2px solid','border-color':'black', 'border-radius':'10px',
        'position':'absolute', 'top':'57.5%', 'left':'59.75%', 'box-sizing':'border-box',
        'padding-left':'20px'},        
        {'color':'black'},
        {'color':'black'},
       # {'color':'black'},
        #phase 4
        {'width':'17.5%', 'height':'20%', 'background-color':'white', 'border':'2px solid','border-color':'black', 'border-radius':'10px',
        'position':'absolute', 'top':'77.5%', 'left':'1%',
        'box-sizing':'border-box', 'padding-left':'10px'},
        {'color':'black'},
        {'color':'black'},
        #theme
        {'width':'20.5%', 'height':'40.5%', 'background-color':'white', 'border':'2px solid','border-color':'black', 'border-radius':'10px',
        'position':'absolute', 'top':'15%', 'left':'78.5%',
        'box-sizing':'border-box', 'padding-left':'10px'},        
        {'color':'black'},
        {'color':'black'},
        {'width':'20%','height':'15%','color':'black','position':'absolute', 'top':'52%', 'left':'40%',
        'background-color':'#03a9f4', 'border': '2px solid black', 'border-radius':'6px','cursor':'pointer'}]
    else:
        theme = False
        return [
        #header
        {'width': '98%', 'height':'10%', 'background-color':'#203354', 'border':'2px solid','border-color':'#FFFFFF', 'border-radius':'10px',
        'position':'absolute', 'top':'2.5%', 'left':'1%', 'box-sizing':'border-box',
        'padding-left':'20px', 'padding-right':'20px'},    
        {'color':'white', 'text-align':'center'},    
        #main div
        {"backgroundColor": "#152238", "width":"100%", "height":"100%", 'position':'absolute', 'top':'0px', 'left':'0px'},
        #user info
        {'width': '17.5%', 'height':'60.5%', 'background-color':'#203354', 'border':'2px solid','border-color':'#FFFFFF', 'border-radius':'10px',
        'position':'absolute', 'top':'15%', 'left':'1%', 'box-sizing':'border-box',
        'padding-left':'20px', 'padding-right':'20px'},
        {'color':'white'},
        {'color':'white'},
        {'color':'white'},
        {'color':'white'},
        {'color':'white'},
        #phase 1
        {'width': '39.25%', 'height':'40%', 'background-color':'#203354', 'border':'2px solid','border-color':'#FFFFFF', 'border-radius':'10px',
        'position':'absolute', 'top':'57.5%', 'left':'19.5%', 'box-sizing':'border-box',
        'padding-left':'20px'},
        {'color':'white'},
        {'color':'white'},
        #phase 2
        {'width':'58%', 'height':'40.5%', 'background-color':'#203354', 'border':'2px solid','border-color':'#FFFFFF', 'border-radius':'10px',
        'position':'absolute', 'top':'15%', 'left':'19.5%',
        'box-sizing':'border-box', 'padding-left':'20px'},        
        {'color':'white'},
        {'color':'white'},
        #phase 3
        {'width':'39.25%', 'height':'40%', 'background-color':'#203354', 'border':'2px solid','border-color':'#FFFFFF', 'border-radius':'10px',
        'position':'absolute', 'top':'57.5%', 'left':'59.75%', 'box-sizing':'border-box',
        'padding-left':'20px'},        
        {'color':'white'},
        {'color':'white'},
        #{'color':'white'},
        #phase 4
        {'width':'17.5%', 'height':'20%', 'background-color':'#203354', 'border':'2px solid','border-color':'#FFFFFF', 'border-radius':'10px',
        'position':'absolute', 'top':'77.5%', 'left':'1%',
        'box-sizing':'border-box', 'padding-left':'10px'},
        {'color':'white'},
        {'color':'white'},
        #theme
        {'width':'20.5%', 'height':'40.5%', 'background-color':'#203354', 'border':'2px solid','border-color':'#FFFFFF', 'border-radius':'10px',
        'position':'absolute', 'top':'15%', 'left':'78.5%',
        'box-sizing':'border-box', 'padding-left':'10px'},        
        {'color':'white'},
        {'color':'white'},
        {'width':'20%','height':'15%','color':'white','position':'absolute', 'top':'52%', 'left':'40%',
        'background-color':'#232b2b', 'border': '2px solid white', 'border-radius':'6px','cursor':'pointer'}]
        quit() 
#----------------------------------End of Theme-----------------------------------

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
@app.callback([Output('thermometer', 'value'), Output('humidity', 'value'),
Output(component_id='latest-timestamp', component_property='children')],
[Input('interval-component', 'n_intervals')])
def update_thermo(n_intervals):
    temp = dht11.temperature
    humi = dht11.humidity
    global tempthresh
    global sent
    if temp > tempthresh:
        if (not sent):
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
                sent = True
            except smtplib.SMTPException:
                print ("Error: unable to send email")
    
            time.sleep(60)
            
            #CODE FOR READING MAIL + COMPARE BY PAYLOAD + RUN MOTOR
            EMAIL = '1945421@iotvanier.com'
            PASSWORD = '1945421'
            SERVER = '192.168.0.11'
            
            mail = imaplib.IMAP4_SSL(SERVER)
            mail.login(EMAIL, PASSWORD)
            
            mail.select('inbox')
            
            status, data = mail.search(None, 'ALL')
            # the list returned is a list of bytes separated
            # by white spaces on this format: [b'1 2 3', b'4 5 6']
            # so, to separate it first we create an empty list
            mail_ids = []
            # then we go through the list splitting its blocks
            # of bytes and appending to the mail_ids list
            for block in data:
               # the split function called without parameter
               # transforms the text or bytes into a list using
               # as separator the white spaces:
               # b'1 2 3'.split() => [b'1', b'2', b'3']
               mail_ids += block.split()
      
            # now for every id we'll fetch the email
            # to extract its content
            for i in mail_ids:
               #Converting int to string for length 
               lastmail = str(len(mail_ids))
               print (lastmail)
               print(i)
#       print ('b' + "\'"+str(lastmail)+"\'")
               # Converting byte to string
               string = i.decode('ASCII')
               print(string)
#       print(string[1:3])
               if (string == lastmail):
                  print("This is the last mail")
                  # the fetch function fetch the email given its id
                  # and format that you want the message to be
                  status, data = mail.fetch(i, '(RFC822)')

                  # the content data at the '(RFC822)' format comes on
                  # a list with a tuple with header, content, and the closing
                  # byte b')'
                  for response_part in data:
                     # so if its a tuple...
                     if isinstance(response_part, tuple):
                         # we go for the content at its second element
                         # skipping the header at the first and the closing
                         # at the third
                         message = email.message_from_bytes(response_part[1])

                         # with the content we can extract the info about
                         # who sent the message and its subject
                         mail_from = message['from']
                         mail_subject = message['subject']
                         print(mail_subject)
                         if (mail_subject != None):
                             if ("yes" in mail_subject):
                                print("Fan On")
                                GPIO.output(Motor1,GPIO.HIGH)
                                GPIO.output(Motor2,GPIO.LOW)
                                GPIO.output(Motor3,GPIO.HIGH)
                                time.sleep(10)
                                GPIO.output(Motor1,GPIO.HIGH)
                                GPIO.output(Motor2,GPIO.HIGH)
                                GPIO.output(Motor3,GPIO.HIGH)
                             else:
                                # if the message isn't multipart, just extract it
                                mail_content = message.get_payload()
                                print("mail subject is not yes")
            
    return [temp, humi, html.Span(f"Last updated: {datetime.now()}", style = {'position':'absolute', 'top':'32px', 'left':'140px', 'color':'white'})]
#----------------------------------End of Phase 2-----------------------------------

#---------------------------------Start of Phase 3----------------------------------
@app.callback([Output('led2', 'src'),
Output(component_id='latest-timestamp2', component_property='children')],
[Input('interval-component2', 'n_intervals')])
def update_lightint(n_intervals):
    global lightthresh 
    if (lightint < lightthresh):
        return ["../assets/images/lightbulb-on.png",
        html.Span(f"Light Intensity: {lightint}, Email Sent!", style={'color':'white'})]
    elif (lightint > lightthresh):
        return ["../assets/images/lightbulb-off.png",
        html.Span(f"Light Intensity: {lightint}",  style={'color':'white'})]


def connect_mqtt() -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)
    client = mqtt_client.Client(client_id)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client

def connect_mqtt2() -> mqtt_client:
    def on_connect2(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(client_id2)
    client.on_connect = on_connect2
    client.connect(broker, port)
    return client

def subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        global lightint
        global lightthresh 
        lightint = int(msg.payload.decode())
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        if (int(msg.payload.decode()) < lightthresh):
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
            
        elif (int(msg.payload.decode()) > lightthresh):
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
    if value:
        run()
#----------------------------------End of Phase 3-----------------------------------

#---------------------------------Start of Phase 4----------------------------------
@app.callback([
Output(component_id='latest-timestamp3', component_property='children'),
Output('tagid', 'value'), Output('username', 'value'),
Output('usertemp', 'value'), Output('userlight', 'value'),],
[Input('interval-component3', 'n_intervals')])
def update_tagint(n_intervals):
        #DISPLAY ALL VALUES FROM THAT SPECIFIC USER
        return [f"",f"{tagid}", f"{name}", f"{tempthresh}", f"{lightthresh}"]
        #return [html.Span(f"Tag Id: {tagid} | User: {name} | Temperature Threshold: {tempthresh} | Light Threshold: {lightthresh}")]

def subscribe2(client: mqtt_client):
    def on_message2(client, userdata, msg):
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
                
                # SEND NOTIFICATION EMAIL MAILCOW
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                sender = ['1945421@iotvanier.com']
                receivers = ['1945421@iotvanier.com']

                SUBJECT = "RFID Reader"
                TEXT = f'From: From You <1945421@iotvanier.com>\r\n To: To Person <to1945421@iotvanier.com>\r\n\r\n User {name} has accessed the reader at {current_time}.'
                message = 'Subject: {}\n\n{}'.format(SUBJECT, TEXT)
                
                try:
                    smtpObj = smtplib.SMTP('192.168.0.11')
                    smtpObj.sendmail(sender, receivers, message)         
                    print ("Successfully sent email")
                except smtplib.SMTPException:
                    print ("Error: unable to send email")

    client.subscribe(topic2)
    client.on_message = on_message2
    
def run2():
    client2 = connect_mqtt2()
    subscribe2(client2)
    client2.loop_forever()
    
# Phase 4
@app.callback(Output('latest-timestamp3', 'style'), Input('rfidswitch', 'value'))
def update_rfid(value):
    if value == True:
        run2()    

#----------------------------------End of Phase 4-----------------------------------      

if __name__ == '__main__':
    app.run_server(debug=True)