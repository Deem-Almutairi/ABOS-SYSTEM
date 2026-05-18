#!/usr/bin/env python3
"""
ABOS — AI-powered behavioral optimization system (operational prototype).

Run:  py -3 main.py
      (or: python main.py  if python points to a real interpreter)

Scenario keys: 1=Evacuation  2=Gate overcrowd  3=Overload  4=Crowd surge  0=Clear
"""

from __future__ import annotations

import sys
import traceback


def _ensure_dependencies() -> bool:
    """Verify pygame is installed for THIS Python interpreter."""
    try:
        import pygame  # noqa: F401
        return True
    except ImportError:
        print("ERROR: pygame is not installed for:", sys.executable, file=sys.stderr)
        print(file=sys.stderr)
        print("Install dependencies:", file=sys.stderr)
        print("  py -3 -m pip install -r requirements.txt", file=sys.stderr)
        print(file=sys.stderr)
        print("Then start the simulation:", file=sys.stderr)
        print("  py -3 main.py", file=sys.stderr)
        print(file=sys.stderr)
        print(
            "Tip: On Windows, if 'python' does nothing, use the 'py' launcher instead.",
            file=sys.stderr,
        )
        return False


def main() -> int:
    if not _ensure_dependencies():
        return 1

    from abos import config
    from abos.simulation import SimulationState
    from abos.visualization import Dashboard

    ui: Dashboard | None = None
    try:
        # Open the window first so the app is visible while the sim loads
        ui = Dashboard()
        ui.show_loading("Initializing ABOS simulation…")

        state = SimulationState.create(config.NUM_AGENTS)

        running = True
        while running:
            running = ui.handle_events(state)
            state.bootstrap_pending_routes()
            state.step()
            ui.draw(state)
            ui.tick()
    except Exception:
        traceback.print_exc()
        if ui is not None:
            try:
                ui.quit()
            except Exception:
                pass
        print("\nABOS exited due to an error (see traceback above).", file=sys.stderr)
        return 1
    finally:
        if ui is not None:
            ui.quit()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
