DESCRIZIONE
Sketch per un Raspberry Pi Pico (con modulo radio SX1262 Waveshare) che funge da gateway: fa da ponte tra il Raspberry Pi (collegato via seriale USB) e la rete LoRa a cui sono connessi i nodi sensore periferici (es. Pico2.ino).

Riceve i comandi dal Raspberry via porta seriale e li inoltra via LoRa; riceve i messaggi LoRa dai nodi periferici e li inoltra al Raspberry via seriale.

HARDWARE RICHIESTO
- Raspberry Pi Pico H
- Modulo LoRa SX1262 (Waveshare)

LIBRERIE NECESSARIE
- RadioLib (https://github.com/jgromes/RadioLib)
- SPI (inclusa nel core Arduino)

FUNZIONAMENTO
1. Setup: inizializza seriale (115200 baud), bus SPI1, switch antenna e radio LoRa a 433.0 MHz. Si mette in ascolto LoRa.
2. Loop principale:
   - gestisciSeriale(): legge riga per riga dalla seriale (dal Raspberry). Se la riga inizia con "CMD:", la inoltra via LoRa tramite inviaComandoLoRa().
   - gestisciLoRa(): controlla se e' arrivato un messaggio LoRa; se si', lo pulisce e lo stampa sulla seriale con prefisso "RX LoRa:".
3. Pulizia stringhe: cleanString() rimuove caratteri non stampabili da ogni messaggio in transito.

FORMATO MESSAGGI
- Comando dal Raspberry verso LoRa: CMD:MOTOR:ON:STANZA1, CMD:MOTOR:OFF:STANZA1, ecc.
- Messaggio ricevuto da LoRa verso seriale: preceduto da "RX LoRa:" (es. RX LoRa: DATA:STANZA1,22.5,45.0,-80,9.5)
