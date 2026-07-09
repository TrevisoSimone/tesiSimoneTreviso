nodoCentrale.py - Nodo centrale su Raspberry Pi

DESCRIZIONE
Script Python eseguito sul Raspberry Pi, collegato via USB al gateway LoRa (pico1.ino). Gestisce l'invio di comandi ai nodi sensore periferici (es. STANZA1, STANZA2), riceve le risposte (dati o errori), le salva su file CSV e mantiene un log di sistema. Esegue inoltre misurazioni automatiche a intervalli regolari.

REQUISITI
- Python 3
- Librerie:
  pip install pyserial schedule
- Raspberry Pi collegato al Pico gateway sulla porta seriale (default /dev/ttyACM0)

CONFIGURAZIONE PRINCIPALE
PORTA_SERIALE      Porta seriale del Pico gateway        default: /dev/ttyACM0
BAUD_RATE          Velocita' seriale                     default: 115200
CARTELLA_DATI      Cartella di output per CSV e log      default: /home/simone/dati_lora
INTERVALLO_MIN     Intervallo misure automatiche (min)   default: 10
TIMEOUT_RISPOSTA   Timeout attesa risposta da un nodo(s) default: 9
DISPOSITIVI_ATTESI Elenco ID dei nodi sensore da gestire default: ["STANZA1", "STANZA2"]

FUNZIONAMENTO
1. Connessione seriale: si connette al Pico gateway; se la connessione cade, riprova automaticamente ogni 5 secondi.
2. Test iniziale: verifica che il Pico1 comunichi correttamente all'avvio.
3. Thread di ricezione (leggi_risposte): in background, legge continuamente la seriale, interpreta i messaggi (DATA:, ACK:, ERRORE:) e:
   - salva i dati di temperatura/umidita'/RSSI/SNR in CSV
   - salva gli errori in CSV
   - segnala la ricezione tramite un flag per sbloccare l'attesa del comando inviato
4. Invio comandi: send_e_aspetta() invia un comando (es. CMD:MOTOR:ON:STANZA1) e attende la risposta entro il timeout; se scade, registra un errore di timeout.
5. Misure: misura_dispositivo() esegue una singola misura (interno "on" o esterno "off") per un dispositivo; misura_automatica() esegue in sequenza interno+esterno per tutti i dispositivi.
6. Scheduling: tramite la libreria schedule, misura_automatica() viene eseguita ogni INTERVALLO_MIN minuti.
7. Interfaccia a riga di comando (non bloccante): mentre lo scheduler gira in background, e' possibile digitare comandi manuali.

COMANDI DA TERMINALE DISPONIBILI
on  <ID>     -> misura interno per il dispositivo <ID>
off <ID>     -> misura esterno per il dispositivo <ID>
on all       -> misura interno per tutti i dispositivi
off all      -> misura esterno per tutti i dispositivi
lista        -> mostra i dispositivi monitorati
Ctrl+C       -> esce dal programma

OUTPUT GENERATO
Per ogni dispositivo e tipo (interno/esterno), un file CSV mensile in CARTELLA_DATI:
dati_<DEVICE_ID>_<interno|esterno>_<AAAA-MM>.csv

Formato riga:
timestamp;device_id;temperatura_C;umidita_%;rssi_dBm;snr_dB;note

In caso di errore, i campi dati vengono sostituiti da "ERRORE" e la nota descrive il problema (es. timeout).

Un file di log generale viene salvato in:
<CARTELLA_DATI>/sistema.log

AVVIO
python3 nodoCentrale.py

Assicurarsi che il Pico gateway sia collegato e riconosciuto sulla porta configurata prima dell'avvio.
