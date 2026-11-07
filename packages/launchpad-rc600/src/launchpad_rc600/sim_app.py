# ABOUTME: Virtual RC-600 app (rc600-sim): an ALSA virtual MIDI input port that feeds the RC-600 model.
# ABOUTME: Shows level bars, Track FX states and a message log (rich TUI), or one log line per event (--plain).
import argparse
import signal
import sys
import time
from collections import deque
from datetime import datetime

import mido
from rich.console import Group
from rich.live import Live
from rich.text import Text

from launchpad_rc600.assign import (
    FX_TARGETS,
    LEVEL_TARGETS,
    AssignConfig,
    ConfigError,
    load_config,
)
from launchpad_rc600.rc600 import FX_ON_THRESHOLD, Rc600Model, mapping_line

PORT_NAME = "RC-600 SIM"
LOG_LINES = 15
# RC-600 manual, ASSIGN: "TRK1–6 LEVEL: Control the PLAY LEVEL ... in the range of 0–200".
LEVEL_SCALE = 200
BAR_WIDTH = 40
POLL_SECONDS = 0.01
STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)


def log_line(msg: mido.Message, text: str) -> str:
    stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    return f"{stamp}  {msg.hex()}  {text}"


def level_bar(value: int | None) -> str:
    """Bar for the 0–200 PLAY LEVEL scale with a '|' mark at 100; '?' when the level is unknown."""
    filled = 0 if value is None else round(value * BAR_WIDTH / LEVEL_SCALE)
    cells = ["#" if i < filled else "." for i in range(BAR_WIDTH)]
    cells.insert(BAR_WIDTH // 2, "|")
    shown = "?" if value is None else str(value)
    return f"[{''.join(cells)}] {shown:>3}"


def fx_state(value: bool | None) -> str:
    if value is None:
        return "?"
    return "on" if value else "off"


def render(config: AssignConfig, model: Rc600Model, log: deque[str]) -> Group:
    lines = [Text(mapping_line(config), style="bold"), Text("")]
    lines += [
        Text(f"{target}  {level_bar(level)}")
        for target, level in zip(LEVEL_TARGETS, model.levels)
    ]
    lines.append(Text(""))
    lines.append(
        Text(
            "   ".join(
                f"{target}: {fx_state(on):<3}"
                for target, on in zip(FX_TARGETS, model.fx)
            )
        )
    )
    lines.append(
        Text(
            f"Track FX: current bank only; on = value ≥ {FX_ON_THRESHOLD} (assumption)",
            style="dim",
        )
    )
    lines.append(Text(""))
    lines += [Text(line) for line in log]
    return Group(*lines)


def run_plain(port, model: Rc600Model, stopping) -> None:
    while not stopping():
        for msg in port.iter_pending():
            print(log_line(msg, model.handle(msg).text), flush=True)
        time.sleep(POLL_SECONDS)


def run_tui(
    port, model: Rc600Model, config: AssignConfig, ready: str, stopping
) -> None:
    log: deque[str] = deque([ready], maxlen=LOG_LINES)
    with Live(render(config, model, log), auto_refresh=False) as live:
        while not stopping():
            changed = False
            for msg in port.iter_pending():
                log.append(log_line(msg, model.handle(msg).text))
                changed = True
            if changed:
                live.update(render(config, model, log), refresh=True)
            time.sleep(POLL_SECONDS)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="rc600-sim", description="Virtual RC-600 with an ALSA MIDI port."
    )
    parser.add_argument(
        "--config",
        default="assign.toml",
        help="ASSIGN config file (default: assign.toml)",
    )
    parser.add_argument(
        "--plain", action="store_true", help="print one log line per message, no screen"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = load_config(args.config, check=True)
    except FileNotFoundError:
        print(f"{args.config}: config file not found", file=sys.stderr)
        return 1
    except ConfigError as error:
        print(f"{args.config}: invalid ASSIGN config:", file=sys.stderr)
        for violation in error.violations:
            print(f"  {violation}", file=sys.stderr)
        return 1

    # Ctrl+C, SIGTERM and SIGHUP (SSH session drops) all stop the loop; the port then closes.
    stop_requested = []
    for sig in STOP_SIGNALS:
        signal.signal(sig, lambda signum, frame: stop_requested.append(signum))

    model = Rc600Model(config)
    with mido.open_input(PORT_NAME, virtual=True, client_name=PORT_NAME) as port:
        ready = f"ready: port {PORT_NAME!r} · {mapping_line(config)}"
        if args.plain:
            print(ready, flush=True)
            run_plain(port, model, lambda: bool(stop_requested))
        else:
            run_tui(port, model, config, ready, lambda: bool(stop_requested))
    return 0


if __name__ == "__main__":
    sys.exit(main())
