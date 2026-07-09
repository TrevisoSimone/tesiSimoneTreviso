#include <RadioLib.h>
#include <SPI.h>

// ─────────────────────────────────────────
// CONFIGURAZIONE SX1262 (Waveshare) SU PICO1
// ─────────────────────────────────────────

// SX1262: NSS=3, DIO1=20, NRST=15, BUSY=2, SPI1
SX1262 radio = new Module(3, 20, 15, 2, SPI1, RADIOLIB_DEFAULT_SPI_SETTINGS);

// ─────────────────────────────────────────
// PULIZIA STRINGHE
// ─────────────────────────────────────────
String cleanString(String s) {
  String out = "";
  for (int i = 0; i < s.length(); i++) {
    char c = s[i];
    if (c >= 32 && c <= 126) out += c;
  }
  return out;
}

// ─────────────────────────────────────────
// SETUP
// ─────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("Pico1 gateway LoRa ↔ Raspberry avvio...");

  SPI1.setRX(12);
  SPI1.setTX(11);
  SPI1.setSCK(10);
  SPI1.begin();
  Serial.println("SPI1 OK");

  pinMode(22, OUTPUT);
  digitalWrite(22, HIGH);
  Serial.println("ANT_SW OK");

  int state = radio.begin(433.0);
  Serial.print("LoRa begin stato: ");
  Serial.println(state);

  if (state == RADIOLIB_ERR_NONE) {
    Serial.println("LoRa pronto (Pico1 gateway).");
  } else {
    Serial.println("ERRORE inizializzazione LoRa!");
  }

  radio.startReceive();
  Serial.println("In ascolto LoRa...");
}

// ─────────────────────────────────────────
// INVIO COMANDO LoRa DAL RASPBERRY
// ─────────────────────────────────────────
void inviaComandoLoRa(String cmd) {   // <<< NON const String
  Serial.print("TX: ");
  Serial.println(cmd);

  int state = radio.transmit(cmd);

  Serial.print("Stato TX LoRa: ");
  Serial.println(state);

  radio.startReceive();
}

// ─────────────────────────────────────────
// GESTIONE LINEA DA SERIAL (RASPBERRY PI)
// ─────────────────────────────────────────
String serialBuffer = "";

void gestisciSeriale() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (serialBuffer.length() > 0) {
        String linea = serialBuffer;
        serialBuffer = "";

        linea.trim();
        linea = cleanString(linea);

        if (linea.startsWith("CMD:")) {
          inviaComandoLoRa(linea);stampa sul 
        } else {
          Serial.print("Comando seriale ignorato: ");
          Serial.println(linea);
        }
      }
    } else {
      serialBuffer += c;
    }
  }
}

// ─────────────────────────────────────────
// GESTIONE RICEZIONE LoRa
// ─────────────────────────────────────────
void gestisciLoRa() {
  String msg;
  int state = radio.receive(msg);   // NON bloccante

  if (state == RADIOLIB_ERR_NONE) {
    msg.trim();
    msg = cleanString(msg);

    if (msg.length() > 0) {
      Serial.print("RX LoRa: ");
      Serial.println(msg);
    }

    radio.startReceive();
  }
}

// ─────────────────────────────────────────
// LOOP PRINCIPALE
// ─────────────────────────────────────────
void loop() {
  gestisciSeriale();
  gestisciLoRa();
  delay(5);
}
