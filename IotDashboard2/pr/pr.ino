#include "WiFi.h"
#include <PubSubClient.h>
const char* ssid = "TP-Link_2AD8"; //Enter SSID
const char* password = "14730078"; //Enter Password
const char* mqtt_server = "192.168.0.148";
//
WiFiClient vanieriot;
PubSubClient client(vanieriot);

#define LIGHT_SENSOR_PIN 34

void setup_wifi() {
 delay(10);
 // We start by connecting to a WiFi network
 Serial.println();
 Serial.print("Connecting to ");
 Serial.println(ssid);
 WiFi.begin(ssid, password);
 while (WiFi.status() != WL_CONNECTED) {
 delay(500);
 Serial.print(".");
 }
 Serial.println("");
 Serial.print("WiFi connected - ESP-8266 IP address: ");
 Serial.println(WiFi.localIP());
}
void callback(String topic, byte* message, unsigned int length) {
 Serial.print("Message arrived on topic: ");
 Serial.print(topic);
 Serial.print(". Message: ");
 String messagein;

 for (int i = 0; i < length; i++) {
 Serial.print((char)message[i]);
 messagein += (char)message[i];
 }

}
void reconnect() {
 while (!client.connected()) {
 Serial.print("Attempting MQTT connection...");
 if (client.connect("vanieriot")) {
 Serial.println("connected");

 } else {
 Serial.print("failed, rc=");
 Serial.print(client.state());
 Serial.println(" try again in 3 seconds");
 // Wait 5 seconds before retrying
 delay(3000);
 }
 }
}
void setup() {
 pinMode(LIGHT_SENSOR_PIN, INPUT); // Set pResistor - A0 pin as an input (optional)
 
 Serial.begin(115200);
 setup_wifi();
 client.setServer(mqtt_server, 1883);
 client.setCallback(callback);
}
void loop() {
 if (!client.connected()) {
 reconnect();
 }
 if(!client.loop())
 client.connect("vanieriot");

 int analogValue = analogRead(LIGHT_SENSOR_PIN);
 Serial.println("Analog Value = ");
 Serial.println(analogValue);   // the raw analog reading


 char lightArr[8];
 dtostrf(analogValue,4,0, lightArr);

 client.publish("light",lightArr);

 delay(3000);
 }
