"""ABOS operational simulation — configuration."""

# ── Display ──────────────────────────────────────────────────────────────────
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SIDEBAR_WIDTH = 300
FPS = 60
TITLE = "ABOS | AI Behavioral Optimization System"

SIM_WIDTH = SCREEN_WIDTH - SIDEBAR_WIDTH
HEADER_HEIGHT = 52
SIM_HEIGHT = SCREEN_HEIGHT - HEADER_HEIGHT  # drawable simulation area

# ── Grid / world ─────────────────────────────────────────────────────────────
CELL_SIZE = 12
GRID_COLS = SIM_WIDTH // CELL_SIZE
GRID_ROWS = SIM_HEIGHT // CELL_SIZE

NUM_AGENTS = 140
AGENT_RADIUS = 3
BASE_SPEED = 2.0

# ── Density & prediction ─────────────────────────────────────────────────────
DENSITY_LOW = 0.30
DENSITY_MEDIUM = 0.50
DENSITY_HIGH = 0.70
CONGESTION_THRESHOLD = 0.72
PREDICT_WINDOW = 60
FRAMES_PER_MINUTE = 3600  # 60 fps × 60 s

# Prediction weights
W_DENSITY = 0.35
W_GROWTH = 0.30
W_FLOW = 0.20
W_INFLUX = 0.15

# ── Pathfinding ────────────────────────────────────────────────────────────────
PATH_REPLAN_INTERVAL = 45
MAX_REPLANS_PER_FRAME = 20
CONGESTION_COST_MULT = 8.0
PREDICTED_COST_MULT = 5.0

# ── Behavioral mix (must sum ≈ 1) ─────────────────────────────────────────────
BEHAVIOR_WEIGHTS = {
    "compliant": 0.45,
    "impatient": 0.25,
    "follower": 0.20,
    "panic_prone": 0.10,
}

# ── Emergency scenarios ──────────────────────────────────────────────────────
SCENARIO_DURATION = 900  # frames (~15 s at 60 fps)
SURGE_SPAWN_COUNT = 25

# ── Facility ─────────────────────────────────────────────────────────────────
FACILITY_MODE = "airport"  # airport | hospital | transit

# ── Dashboard palette (futuristic control-center) ────────────────────────────
COLOR_BG = (8, 12, 20)
COLOR_PANEL = (14, 20, 32)
COLOR_PANEL_BORDER = (30, 55, 90)
COLOR_ACCENT = (0, 200, 255)
COLOR_ACCENT_DIM = (0, 120, 160)
COLOR_TEXT = (210, 225, 240)
COLOR_TEXT_DIM = (110, 130, 155)
COLOR_OK = (40, 200, 120)
COLOR_WARN = (255, 190, 50)
COLOR_ALERT = (255, 70, 90)
COLOR_CRITICAL = (255, 40, 60)

COLOR_WALL = (22, 30, 45)
COLOR_FLOOR = (12, 18, 28)
COLOR_HALLWAY = (16, 24, 38)

COLOR_HEAT_LOW = (20, 60, 90)
COLOR_HEAT_MED = (180, 140, 30)
COLOR_HEAT_HIGH = (220, 50, 40)

COLOR_AGENT = {
    "compliant": (60, 180, 255),
    "impatient": (255, 160, 60),
    "follower": (140, 220, 140),
    "panic_prone": (255, 90, 140),
}
COLOR_REROUTE = (255, 220, 80)
COLOR_PATH = (0, 180, 255, 60)

# Zone tints (operational areas)
ZONE_COLORS = {
    "main_entrance": (30, 50, 70),
    "check_in": (35, 55, 75),
    "security": (40, 45, 65),
    "waiting_lounge": (30, 60, 80),
    "gate_a": (45, 40, 70),
    "gate_b": (45, 40, 70),
    "gate_c": (45, 40, 70),
    "bottleneck": (55, 35, 45),
    "exit": (35, 70, 55),
}
