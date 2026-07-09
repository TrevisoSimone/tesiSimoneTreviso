#include <RadioLib.h>
#include <SPI.h>
#include <DHT.h>
#include <hardware/watchdog.h>

#define DEVICE_ID "STANZA1"

#define DHT_PIN_1 4
#define DHT_PIN_2 5
#define DHT_TYPE DHT11

DHT dht1(DHT_PIN_1, DHT_TYPE);
DHT dht2(DHT_PIN_2, DHT_TYPE);

SX1262 radio = new Module(3, 20, 15, 2, SPI1, RADIOLIB_DEFAULT_SPI_SETTINGS);

void setup() {
  Serial.begin(115200);
  delay(2000);

  dht1.begin();
  dht2.begin();
  Serial.println("DHT11 x2 OK");

  SPI1.setRX(12);
  SPI1.setTX(11);
  SPI1.setSCK(10);
  SPI1.begin();
  Serial.println("SPI1 OK");

  pinMode(22, OUTPUT);
  digitalWrite(22, HIGH);
  pinMode(14, OUTPUT);
  digitalWrite(14, LOW);
  Serial.println("ANT_SW OK");

  int state = radio.begin(433.0);
  Serial.print("Stato: ");
  Serial.println(state);

  if (state == RADIOLIB_ERR_NONE) {
    Serial.println("LoRa pronto!");
  }

  radio.startReceive();
  Serial.print("In ascolto... (ID: ");
  Serial.print(DEVICE_ID);
  Serial.println(")");
}

void inviaErrore() {
  String errMsg = "ERRORE:" + String(DEVICE_ID) + ":DHT11";
  radio.transmit(errMsg);
  delay(100);
  radio.startReceive();
}

void inviaDati(float temperature, float humidity, float rssi, float snr) {
  char buffer[120];
  snprintf(buffer, sizeof(buffer),
           "DATA:%s,%.1f,%.1f,%.0f,%.1f",
           DEVICE_ID, temperature, humidity, rssi, snr);
  radio.transmit(buffer);
  delay(100);
  radio.startReceive();
}

void checkTemp(int stanza) {
  float temperature, humidity;

  if (stanza == 1) {
    temperature = dht1.readTemperature();
    humidity    = dht1.readHumidity();
  } else {
    temperature = dht2.readTemperature();
    humidity    = dht2.readHumidity();
  }

  if (isnan(temperature) || isnan(humidity)) {
    Serial.print("Errore lettura DHT11 stanza ");
    Serial.println(stanza);
    inviaErrore();
    return;
  }

  Serial.print("Stanza ");
  Serial.print(stanza);
  Serial.print(" → T = ");
  Serial.print(temperature, 1);
  Serial.print(" °C, H = ");
  Serial.print(humidity, 1);
  Serial.println(" %");

  float rssi = radio.getRSSI();
  float snr  = radio.getSNR();

  inviaDati(temperature, humidity, rssi, snr);
}

void loop() {
  String msg;
  int state = radio.receive(msg, 2000);

  if (state == RADIOLIB_ERR_NONE) {
    msg.trim();
    Serial.print("CMD ricevuto: ");
    Serial.println(msg);

    // formati:
    //   CMD:MOTOR:ON           → tutti
    //   CMD:MOTOR:ON:STANZA1   → solo STANZA1
    //   CMD:MOTOR:OFF:STANZA1  → solo STANZA1

    bool commanded = false;
    int colonCount = 0;
    String target = "";
    for (int i = 0; i < (int)msg.length(); i++) {
      if (msg[i] == ':') colonCount++;
      if (colonCount == 3) { target = msg.substring(i + 1); break; }
    }

    if (target == "" || target == String(DEVICE_ID)) {
      commanded = true;
    }

    if (commanded) {
      if (msg.startsWith("CMD:MOTOR:ON")) {
        radio.transmit("ACK:" + String(DEVICE_ID) + ":MOTOR:ON");
        delay(100);
        checkTemp(1);   // sensore 1
      }

      if (msg.startsWith("CMD:MOTOR:OFF")) {
        digitalWrite(14, LOW);
        Serial.println("Motore OFF");
        radio.transmit("ACK:" + String(DEVICE_ID) + ":MOTOR:OFF");
        delay(100);
        checkTemp(2);   // sensore 2
      }
    }
  }

  radio.startReceive();
}