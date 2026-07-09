Pico2.ino - Nodo sensore LoRa (STANZA1)

DESCRIZIONE
Sketch per un Raspberry Pi Pico periferico, identificato come STANZA1, dotato di due sensori DHT11 e di un modulo radio SX1262. Riceve comandi via LoRa dal gateway (pico1.ino), esegue letture di temperatura/umidita' e rimanda i dati indietro via LoRa.

HARDWARE RICHIESTO
- Raspberry Pi Pico
- Modulo LoRa SX1262
- 2x sensori DHT11:
  Sensore interno -> pin GPIO4
  Sensore esterno -> pin GPIO45


LIBRERIE NECESSARIE
- RadioLib (https://github.com/jgromes/RadioLib)
- DHT sensor library (https://github.com/adafruit/DHT-sensor-library, compatibile con DHT.h)
- SPI

IDENTIFICATIVO DISPOSITIVO
#define DEVICE_ID "STANZA1"
Da modificare per distinguere nodi diversi (es. "STANZA2" per un secondo nodo basato sullo stesso sketch).

FUNZIONAMENTO
1. Setup: inizializza seriale, sensori DHT11, SPI1, switch antenna, pin motore e radio LoRa a 433.0 MHz.
2. Loop principale: resta in ascolto di comandi LoRa (timeout 2s).
   - Riceve un messaggio del tipo CMD:MOTOR:ON oppure CMD:MOTOR:ON:STANZA1 (il comando puo' essere globale o diretto a un dispositivo specifico, verificato tramite il terzo ":" nel messaggio).
   - Se il comando e' indirizzato a questo dispositivo (o e' generico):
     CMD:MOTOR:ON  -> invia ACK, poi legge il sensore 1 (checkTemp(1))
     CMD:MOTOR:OFF -> spegne il pin motore, invia ACK, poi legge il sensore 2 (checkTemp(2))
3. Lettura sensore (checkTemp): legge temperatura/umidita'; se il DHT11 restituisce NaN, invia un messaggio di errore (inviaErrore); altrimenti invia i dati via LoRa (inviaDati) insieme a RSSI e SNR del collegamento.

FORMATO MESSAGGI LORA
- Dati inviati: DATA:STANZA1,<temperatura>,<umidita>,<rssi>,<snr>
- Errore inviato: ERRORE:STANZA1:DHT11
- ACK inviato: ACK:STANZA1:MOTOR:ON / ACK:STANZA1:MOTOR:OFF
