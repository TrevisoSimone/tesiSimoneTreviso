import serial
import time
import threading
import os
import schedule
import logging
import sys
import select

PORTA_SERIALE    = '/dev/ttyACM0'
BAUD_RATE        = 115200
CARTELLA_DATI    = '/home/simone/dati_lora'
INTERVALLO_MIN   = 10
TIMEOUT_RISPOSTA = 9

DISPOSITIVI_ATTESI = ["STANZA1", "STANZA2"]

# Ricorda se l’ultima misura era interno (on) o esterno (off)
ultimo_tipo = {dev: "interno" for dev in DISPOSITIVI_ATTESI}

os.makedirs(CARTELLA_DATI, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(CARTELLA_DATI, 'sistema.log'),
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log(msg, livello='info'):
    print(msg)
    if livello == 'info':
        logging.info(msg)
    elif livello == 'warning':
        logging.warning(msg)
    elif livello == 'error':
        logging.error(msg)

# ---------------------------------------------------------
# FILEPATH CON interno/esterno
# ---------------------------------------------------------
def get_filepath(device_id, tipo):
    mese = time.strftime("%Y-%m")
    nome = f"dati_{device_id}_{tipo}_{mese}.csv"
    return os.path.join(CARTELLA_DATI, nome)

def inizializza_csv(filepath):
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f:
            f.write("timestamp;device_id;temperatura_C;umidita_%;rssi_dBm;snr_dB;note\n")
        log(f"Creato nuovo file: {filepath}")

def salva_dati(device_id, temperatura, umidita, rssi, snr, tipo):
    filepath = get_filepath(device_id, tipo)
    inizializza_csv(filepath)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    riga = f"{timestamp};{device_id};{temperatura};{umidita};{rssi};{snr};\n"
    with open(filepath, 'a') as f:
        f.write(riga)
    log(f"  >> SALVATO [{device_id} - {tipo}]: T={temperatura}°C H={umidita}% RSSI={rssi}dBm SNR={snr}dB")

def salva_errore(device_id, messaggio, tipo):
    filepath = get_filepath(device_id, tipo)
    inizializza_csv(filepath)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    riga = f"{timestamp};{device_id};ERRORE;ERRORE;ERRORE;ERRORE;{messaggio}\n"
    with open(filepath, 'a') as f:
        f.write(riga)
    log(f"  >> ERRORE salvato [{device_id} - {tipo}]: {messaggio}", 'warning')

# ---------------------------------------------------------
# CONNESSIONE SERIAL
# ---------------------------------------------------------
ser = None

def connetti():
    global ser
    while True:
        try:
            ser = serial.Serial(PORTA_SERIALE, BAUD_RATE, timeout=1)
            time.sleep(2)
            log("Connesso al Pico 1!")
            return
        except serial.SerialException as e:
            log(f"Connessione fallita: {e} — riprovo tra 5 secondi...", 'error')
            time.sleep(5)

connetti()

# ---------------------------------------------------------
# TEST PICO1
# ---------------------------------------------------------
def test_pico1_identico_vecchio():
    log("Verifica Pico 1...")

    inizio = time.time()
    while time.time() - inizio < 2:
        if ser.in_waiting:
            linea = ser.readline().decode('utf-8', errors='ignore').strip()
            if linea:
                log(f"{linea}")
                log("Pico 1 OK — comunicazione attiva!")
                return True
        time.sleep(0.05)

    log("ATTENZIONE: nessun messaggio dal Pico 1 all'avvio.")
    return False

test_pico1_identico_vecchio()

# ---------------------------------------------------------
# THREAD DI RICEZIONE
# ---------------------------------------------------------
risposte_attese = {dev: False for dev in DISPOSITIVI_ATTESI}
lock_risposte = threading.Lock()

def normalizza_linea(linea):
    if "RX LoRa:" in linea:
        linea = linea.split("RX LoRa:", 1)[1].strip()
    if "TX:" in linea:
        linea = linea.split("TX:", 1)[1].strip()
    return linea

def estrai_device_id(linea):
    linea = normalizza_linea(linea)
    for prefisso in ("DATA:", "ACK:", "ERRORE:"):
        if linea.startswith(prefisso):
            resto = linea[len(prefisso):]
            sep = ',' if prefisso == "DATA:" else ':'
            candidate = resto.split(sep)[0]
            if candidate in DISPOSITIVI_ATTESI:
                return candidate
    return None

def leggi_risposte():
    global ser
    while True:
        try:
            if ser and ser.in_waiting:
                linea_raw = ser.readline().decode('utf-8', errors='ignore').strip()
                if not linea_raw:
                    continue

                log(f"  << RISPOSTA: {linea_raw}")

                linea = normalizza_linea(linea_raw)
                device_id = estrai_device_id(linea)

                if "DATA:" in linea and device_id:
                    try:
                        parte_dati = linea[linea.index("DATA:") + 5:]
                        parte_dati = parte_dati.replace("\r", "").replace("\n", "").strip()
                        parti = parte_dati.split(',')

                        if len(parti) >= 5:
                            temperatura = float(parti[1])
                            umidita     = float(parti[2])
                            rssi        = float(parti[3])
                            snr         = float(parti[4])

                            salva_dati(device_id, temperatura, umidita, rssi, snr, ultimo_tipo[device_id])

                            with lock_risposte:
                                risposte_attese[device_id] = True
                        else:
                            log(f"Formato dati non valido: {linea}", 'warning')

                    except Exception as e:
                        log(f"Errore parsing dati: {e}", 'error')

                elif linea.startswith("ACK:") and device_id:
                    log(f"  ACK da [{device_id}]")
                    with lock_risposte:
                        risposte_attese[device_id] = True

                elif linea.startswith("ERRORE:") and device_id:
                    salva_errore(device_id, linea, ultimo_tipo[device_id])
                    with lock_risposte:
                        risposte_attese[device_id] = True

        except serial.SerialException:
            log("Connessione seriale persa, riconnessione...", 'error')
            connetti()

        time.sleep(0.05)

thread_rx = threading.Thread(target=leggi_risposte, daemon=True)
thread_rx.start()

# ---------------------------------------------------------
# INVIO COMANDI
# ---------------------------------------------------------
def send(cmd):
    global ser
    try:
        ser.write((cmd + "\n").encode())
        log(f"  >> INVIATO: {cmd}")
    except serial.SerialException:
        log("Errore invio comando, riconnessione...", 'error')
        connetti()

def send_e_aspetta(cmd, device_id, tipo, timeout=TIMEOUT_RISPOSTA):
    with lock_risposte:
        risposte_attese[device_id] = False

    send(cmd)

    inizio = time.time()
    while time.time() - inizio < timeout:
        with lock_risposte:
            if risposte_attese[device_id]:
                log(f"  Risposta ricevuta da [{device_id}] in {time.time()-inizio:.1f}s")
                return True
        time.sleep(0.1)

    salva_errore(device_id, f"Timeout dopo {timeout}s", tipo)
    return False

# ---------------------------------------------------------
# MISURE
# ---------------------------------------------------------
def misura_dispositivo(device_id, quale):
    tipo = "interno" if quale == "on" else "esterno"
    ultimo_tipo[device_id] = tipo

    if quale == "on":
        comando = f"CMD:MOTOR:ON:{device_id}"
    else:
        comando = f"CMD:MOTOR:OFF:{device_id}"

    log(f"--- Misura [{device_id}] ({tipo}) ---")
    ok = send_e_aspetta(comando, device_id, tipo)

    if not ok:
        log(f"  [{device_id}] saltato.", 'warning')

    time.sleep(2)

# ---------------------------------------------------------
# MISURA AUTOMATICA (INTERNO + ESTERNO)
# ---------------------------------------------------------
def misura_automatica():
    log("═══ Misura automatica (interno + esterno) ═══")
    for dev in DISPOSITIVI_ATTESI:
        misura_dispositivo(dev, "on")
        misura_dispositivo(dev, "off")
    log("═══ Misura automatica completata ═══")

schedule.every(INTERVALLO_MIN).minutes.do(misura_automatica)

log(f"Misure automatiche ogni {INTERVALLO_MIN} minuti attive.")
log(f"Dispositivi monitorati: {', '.join(DISPOSITIVI_ATTESI)}")

# ---------------------------------------------------------
# LOOP PRINCIPALE NON BLOCCANTE
# ---------------------------------------------------------
print("\nComandi disponibili:")
print("  on  <ID>   → misura interno")
print("  off <ID>   → misura esterno")
print("  on all     → interno tutti")
print("  off all    → esterno tutti")
print("  lista      → mostra dispositivi")
print("  Ctrl+C     → esci\n")

while True:
    try:
        schedule.run_pending()

        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            raw = input(">> ").strip()
            if raw:
                parti = raw.split()
                cmd   = parti[0].lower()

                if cmd in ("on", "off") and len(parti) >= 2:
                    target = parti[1].upper()
                    if target == "ALL":
                        for dev in DISPOSITIVI_ATTESI:
                            misura_dispositivo(dev, cmd)
                    elif target in DISPOSITIVI_ATTESI:
                        misura_dispositivo(target, cmd)
                    else:
                        print(f"Dispositivo '{target}' non riconosciuto.")

                elif cmd == "lista":
                    print(f"Dispositivi: {', '.join(DISPOSITIVI_ATTESI)}")

                else:
                    print("Comandi: on <ID>, off <ID>, on all, off all, lista")

        time.sleep(0.2)

    except KeyboardInterrupt:
        print("\nUscita...")
        if ser:
            ser.close()
        break
