"""Fixed protocol constants for the DiGiCo ↔ DS100 bridge."""

DB_MIN = -120.0
DB_MAX = 10.0
ECHO_THRESHOLD_DB = 0.05

AUX_NUMBER = 1

DS100_SEND_PORT = 50010
DS100_LISTEN_PORT = 50011
DS100_PREFIX = "/dbaudio1"

# En-Space zones (reverbinputprocessing gain/mute 1–4)
ENSPACE_ZONE_COUNT = 4

# Companion-style continuous poll for mapped reverbsendgain channels (ms).
DS100_POLL_INTERVAL_MS = 500
DS100_POLL_INTERVAL_MIN_MS = 100
DS100_POLL_INTERVAL_MAX_MS = 60000

# Quantum / SD Pad protocol (see OSCWebMixer2 mock-desk.js)
DIGICO_HANDSHAKE_PATH = "/Console/Channels/?"
