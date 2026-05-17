"""Simulation and UI configuration."""

# Display
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
FPS = 60
TITLE = "ABOS — Crowd Congestion Prediction"

# World
NUM_AGENTS = 120
AGENT_RADIUS = 4
AGENT_SPEED = 1.8
AGENT_COLOR = (70, 130, 220)
REROUTE_COLOR = (255, 180, 60)

# Zone grid
ZONE_COLS = 6
ZONE_ROWS = 4
ZONE_PADDING = 8

# Density thresholds (agents per zone capacity ratio 0–1)
DENSITY_LOW = 0.35
DENSITY_MEDIUM = 0.55
DENSITY_HIGH = 0.75

# Prediction (rule-based)
PREDICT_WINDOW = 30  # frames of history
CONGESTION_THRESHOLD = 0.65
TREND_WEIGHT = 0.4  # how much rising density affects prediction score

# Adaptive response
REROUTE_BIAS = 0.85  # push rerouted agents toward sparse zones
WARNING_COOLDOWN = 90  # frames between repeated warnings per zone

# Colors
COLOR_BG = (24, 28, 36)
COLOR_ZONE_EMPTY = (40, 48, 58)
COLOR_ZONE_LOW = (50, 90, 70)
COLOR_ZONE_MED = (140, 120, 50)
COLOR_ZONE_HIGH = (160, 70, 50)
COLOR_ZONE_CRITICAL = (180, 40, 40)
COLOR_TEXT = (220, 225, 235)
COLOR_WARNING = (255, 90, 90)
