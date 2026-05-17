#!/usr/bin/env python3
"""
ABOS — AI-powered crowd congestion prediction (prototype).

Run: python main.py
"""

from abos import config
from abos.simulation import SimulationState
from abos.visualizer import Visualizer


def main() -> None:
    state = SimulationState.create(
        config.SCREEN_WIDTH,
        config.SCREEN_HEIGHT,
        config.NUM_AGENTS,
    )
    viz = Visualizer(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)

    running = True
    try:
        while running:
            running = viz.handle_events()
            state.step()
            viz.draw(state, state.responder.warnings)
            viz.tick()
    finally:
        viz.quit()


if __name__ == "__main__":
    main()
