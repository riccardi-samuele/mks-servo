# Caratterizzazione MKS SERVO42D RS485 + NEMA17 — Design

**Data:** 2026-05-09
**Autore:** Samuele (in collaborazione con Claude)
**Stato:** spec di design, in attesa di plan implementativo

## 1. Obiettivo

Caratterizzare il comportamento di un motore stepper NEMA17 controllato da driver MKS SERVO42D via RS485, in vista di un futuro impiego in robotica (lo stepper closed-loop usato come "brushless economico con encoder"). I test devono produrre numeri concreti su tre aspetti:

1. **Precisione** angolare (ripetibilità, errore di posizionamento, errore di inseguimento)
2. **Velocità** raggiungibile e sostenibile (RPM massimo per modalità, profili di accelerazione, soglia di stallo)
3. **Persistenza** della configurazione e della calibrazione attraverso power-cycle del motore

Deliverable: una libreria Python `mks_servo` riutilizzabile + suite di benchmark eseguibili che produce CSV e plot.

## 2. Setup hardware

| Componente | Note |
|---|---|
| MKS SERVO42D RS485 (firmware ≥ V1.0.6) | Driver closed-loop integrato sul motore |
| NEMA17 collegato al driver | Resistenza fase < 10 Ω (requisito manuale) |
| Alimentatore 12-24 V su V+/GND | Tensione effettiva da annotare nei report |
| Convertitore USB↔RS485 generico | Collegato ad A/B; lato PC `/dev/ttyUSB*` |
| Riferimento visivo | Puntatore + scala graduata o video del telefono — usato solo per i test V1/V2 |

L'MKS APT v1.0 è una mainboard per stampanti 3D, non un adattatore: non viene usato in questi test.

## 3. Architettura software

```
stepper_motor_test/
├── mks_servo/              # libreria riutilizzabile
│   ├── __init__.py
│   ├── protocol.py         # frame FA/FB, checksum 8bit, transact()
│   ├── driver.py           # classe MKSServo42D (API alto livello)
│   ├── constants.py        # opcodes, enum WorkMode/BaudRate
│   └── exceptions.py       # CommTimeout, ChecksumError, MotorFault, ...
├── benchmarks/
│   ├── 01_smoke.py
│   ├── 02_precision.py
│   ├── 03_speed.py
│   ├── 04_persistence.py
│   └── _common.py          # apertura porta, logging CSV, plot helpers
├── results/                # output CSV/PNG/MD (gitignored)
├── docs/superpowers/specs/ # questo doc
└── pyproject.toml          # pyserial, numpy, matplotlib
```

**Configurazione porta** (file `config.toml` o env): `port=/dev/ttyUSB0`, `baud=38400`, `slave_addr=1`, `timeout=0.5`. Default coerenti con quelli di fabbrica del manuale.

## 4. API libreria `mks_servo`

### 4.1 Layer protocollo (`protocol.py`)

```python
def build_frame(addr: int, code: int, data: bytes = b"") -> bytes
def parse_frame(buf: bytes) -> tuple[int, int, bytes]
def checksum8(buf: bytes) -> int          # sum & 0xFF
def transact(ser, addr, code, data=b"", expect_len=None, timeout=0.5) -> bytes
```

### 4.2 Classe `MKSServo42D` (`driver.py`)

**Read / telemetria** (opcodes 0x30–0x3E, 0xF1, 0x47):

```python
read_encoder() -> tuple[int, int]       # 0x30  (carry int32, value 0..0x3FFF)
read_encoder_addition() -> int          # 0x31  (int48 cumulato)
read_speed_rpm() -> int                 # 0x32  (firmato; <0 = CW)
read_pulses() -> int                    # 0x33
read_angle_error() -> int               # 0x39  (51200 → 360°)
read_motor_status() -> MotorStatus      # 0xF1  (stop/up/down/full/cal/home)
read_protect_status() -> bool           # 0x3E
read_all_config() -> dict               # 0x47  (snapshot 38 byte)
```

**Config** (persistenti in flash, opcodes 0x80–0x9E, 0x3F, 0x41):

```python
calibrate()                             # 0x80  ⚠ motore SCARICO
set_work_mode(WorkMode.SR_vFOC)         # 0x82
set_work_current_ma(1600)               # 0x83
set_subdivision(16)                     # 0x84  (1..256)
set_zero_point()                        # 0x92
restore_defaults()                      # 0x3F  ⚠ richiede ricalibrazione
restart()                               # 0x41
release_protection()                    # 0x3D
```

**Motion** (richiede mode `SR_*`, opcodes 0xF3–0xFE, 0xFF):

```python
enable(on: bool)                        # 0xF3
move_speed(rpm, acc=2, direction=CW)    # 0xF6  velocità continua
move_relative_pulses(pulses, rpm, acc)  # 0xFD  pos. relativa step
move_absolute_pulses(pulses, rpm, acc)  # 0xFE
move_relative_axis(counts, rpm, acc)    # 0xF4  encoder counts (0x4000=1giro)
move_absolute_axis(counts, rpm, acc)    # 0xF5  supporta update real-time
emergency_stop()                        # 0xF7
wait_until_idle(timeout=10.0)           # poll su 0xF1
save_speed_mode_state(save: bool)       # 0xFF C8/CA
```

**Helpers di conversione** (in `driver.py`):

- `degrees_to_encoder_counts(deg) → int(deg * 0x4000 / 360)`
- `degrees_to_pulses(deg, microsteps=16) → int(deg * 200 * microsteps / 360)`
- `read_angle_degrees() → read_encoder_addition() * 360 / 0x4000`

**Pattern d'uso (context manager):**

```python
with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
    m.set_work_mode(WorkMode.SR_vFOC)
    m.enable(True)
    m.move_relative_axis(0x4000, rpm=300, acc=10)
    m.wait_until_idle()
    print(m.read_angle_degrees())
```

Il context manager apre la seriale all'ingresso e la chiude all'uscita (anche su eccezione). **Non** gestisce `enable()` automaticamente: l'utente deve chiamarlo esplicitamente, per evitare di energizzare il motore solo aprendo una connessione di lettura. Su `__exit__` viene comunque chiamato `enable(False)` come safety net se il motore era stato abilitato.

## 5. Benchmark di caratterizzazione

### 5.1 Precisione (`02_precision.py`) — scope MVP

| ID | Test | Procedura |
|---|---|---|
| P1 | Ripetibilità statica | 100×: vai a θ_random, poi vai a 90°, registra residuo. Out: σ, peak |
| P3 | Errore vs velocità | Sweep RPM ∈ {50, 100, 300, 600, 1000, 1500, 2000, 3000}, 20× ciascuno. Plot RMS/peak vs RPM |
| P5 | Errore di inseguimento | Move 1 giro a 60 RPM con `acc=2`; poll 0x39 ogni 20 ms. Plot error(t) |
| V1 | Verifica calibrazione (visivo) | `move_relative_axis(10*0x4000, ...)`, conta giri a video. Una volta sola |

Test **opzionali post-MVP**: P2 (isteresi/backlash CW vs CCW), P4 (errore vs subdivisions), P6 (drift cumulativo su 500 cicli), V2 (verifica zero point).

### 5.2 Velocità (`03_speed.py`) — scope MVP

| ID | Test | Procedura |
|---|---|---|
| S1 | RPM massimo per modalità | Per `SR_OPEN`/`SR_CLOSE`/`SR_vFOC`: comanda RPM crescenti, leggi `read_speed_rpm()`. Plot comandato vs misurato |
| S2 | Curva di accelerazione | Per `acc ∈ {1, 50, 100, 200, 255}`: `move_speed(2000, acc)`, campiona RPM ogni 10 ms. Confronta con teoria `Δt = (256-acc)·50µs · ΔRPM` |
| S3 | Soglia di stallo | In `SR_CLOSE`: `move_relative_pulses(10 giri, rpm)` per `rpm ∈ {500…3000}`. Leggi `read_angle_error()` e `read_pulses()` finali. Identifica punto di rottura |

Test opzionale post-MVP: S4 (coppia di tenuta a riposo, qualitativo "a dita").

**Sicurezza:** `acc ≠ 0` per RPM > 800 (il manuale sconsiglia stop bruschi sopra 1000 RPM).
**Note:** RPM è calibrato su 16/32/64 subdivisions; tutti i test S1/S3 a 16 subdiv (default).

### 5.3 Persistenza (`04_persistence.py`) — scope MVP

| ID | Test | Procedura |
|---|---|---|
| C1 | Diff config completo | `cfg_pre = read_all_config()`, power-cycle manuale, `cfg_post = read_all_config()`. Assert `pre == post` |
| C2 | Calibrazione persiste | `calibrate()`, V1 ok, power-cycle, rifai V1 senza ricalibrare → ok |
| C3 | Parametri custom sopravvivono | Set `current=2200`, `subdiv=64`, `addr=7`, power-cycle, riapri seriale a `addr=7`, leggi config → tutti i 3 valori intatti. **Try/finally**: ripristina `addr=1` alla fine |

Test opzionali post-MVP: C4 (`restore_defaults()` effettivo, distruttivo), C5 (`save_speed_mode_state()` autostart al power-on).

**Convenzione power-cycle:** stacca solo i 12 V del motore (USB resta collegata). Lo script chiede `input("Stacca i 12V, aspetta 3s, riattacca, poi premi ENTER")` nei punti chiave.

## 6. Output condiviso

Ogni benchmark scrive in `results/<bench_name>_<ISO_timestamp>/`:

- `raw.csv` — campioni grezzi (test_id, iter, target, measured, residual, ...)
- `comm.log` — log strutturato di ogni transazione seriale (timestamp, opcode, req, resp, latenza ms)
- `plots/*.png` — un PNG per test
- `report.md` — sommario con statistiche (σ, peak, drift, PASS/FAIL) e link ai plot

Lo schema dei CSV include sempre i parametri di setup come colonne fisse (voltage, current_ma, subdivisions, mode) per permettere confronti tra run con setup diversi.

## 7. Gestione errori (in `_common.py`)

- Wrapper `safe_transact` che ritenta una volta dopo `CommTimeout` (USB-RS485 generici a volte perdono il primo byte)
- Logging strutturato di **ogni** transazione (sopra)
- `try/finally` globale: `enable(False)` all'uscita; in C3 e C4 anche ripristino di stato (address, calibrazione)

## 8. Rischi e limiti noti (da annotare nel report finale)

- `read_speed_rpm()` dipende dalle subdivisions correnti → registrare nel CSV
- Cmd `0x39` (errore angolo) significativo solo in `SR_CLOSE`/`SR_vFOC`
- Nessun ground-truth meccanico esterno → tutti i numeri di precisione sono "secondo l'encoder interno del driver"; il test V1 funge da unico contro-controllo grezzo
- 12 V vs 24 V cambiano coppia e RPM massimi → annotare la tensione usata
- L'MKS APT v1.0 è una mainboard per stampanti 3D, non un adattatore: non in questo progetto
- I default del manuale (mode=2/SR_vFOC, current=1600 mA, subdiv=16, baud=38400, addr=1) sono assunti come stato iniziale del driver

## 9. Ordine di esecuzione raccomandato

1. `01_smoke.py` — ping, dump config, calibrazione una tantum
2. `02_precision.py` — P1, P3, P5 + V1
3. `03_speed.py` — S1, S2, S3
4. `04_persistence.py` — C1, C2, C3 (C4/C5 fuori MVP)

## 10. Fuori scope

- ROS2 / nodi robot → fase successiva, non in questo progetto
- Test in modalità Modbus-RTU (cmd `0x8E`) → resta protocollo nativo FA/FB
- Multi-slave (più motori sullo stesso bus)
- Modalità interfaccia pulses (CR_*) → solo seriale, dato l'obiettivo
- Configurazione end-stop / home (cmd `0x90`/`0x91`) → utile sul robot, non per la caratterizzazione del motore
