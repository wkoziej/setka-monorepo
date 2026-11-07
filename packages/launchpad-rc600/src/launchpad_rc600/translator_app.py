# ABOUTME: The lp-rc600 program: connects the Launchpad ports to a target port through the translator core.
# ABOUTME: Finds ports by name part, sends the start state, logs every message, resets the LEDs on exit.
import argparse
import signal
import sys
import time
from datetime import datetime

import mido

from launchpad_rc600 import launchpad
from launchpad_rc600.assign import ConfigError, load_config
from launchpad_rc600.translator import Output, Translator

STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)

# Time for input that waited in the device buffer to arrive after the port opens.
STALE_INPUT_SETTLE = 0.1


class Stop(Exception):
    """Raised by the signal handler to leave the receive loop."""


def log(tag: str, text: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{stamp} {tag:<4} {text}", flush=True)


def find_port(part: str, names: list[str], kind: str) -> str:
    """The one port whose name contains `part`; stop the program for zero or several matches."""
    matches = [n for n in names if part in n]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        listed = "\n".join(f"  {n}" for n in names) or "  (none)"
        sys.exit(f"no {kind} port matches {part!r}; available {kind} ports:\n{listed}")
    listed = "\n".join(f"  {n}" for n in matches)
    sys.exit(f"{kind} port name {part!r} matches more than one port:\n{listed}")


def send(output: Output, target, pad_out) -> None:
    for line in output.log:
        log("info", line)
    for msg in output.rc600:
        target.send(msg)
        log("out", str(msg))
    for msg in output.leds:
        pad_out.send(msg)
    if output.leds:
        log("led", f"{len(output.leds)} LED messages")


def discard_pending(pad_in, settle: float = STALE_INPUT_SETTLE) -> int:
    """Drop Launchpad input that waited in the buffer before startup; return how many messages."""
    time.sleep(settle)
    return sum(1 for _ in pad_in.iter_pending())


def _raise_stop(signum, frame):
    raise Stop(signal.Signals(signum).name)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="lp-rc600", description="Launchpad Mini → RC-600 translator"
    )
    parser.add_argument(
        "--launchpad", default="Launchpad Mini", help="Launchpad port name part"
    )
    parser.add_argument(
        "--out", required=True, help="target port name part, e.g. 'RC-600 SIM'"
    )
    parser.add_argument("--config", default="assign.toml", help="ASSIGN config file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        config = load_config(args.config, check=True)
    except ConfigError as e:
        sys.exit(
            f"config {args.config} is not valid:\n"
            + "\n".join(f"  {v}" for v in e.violations)
        )
    except OSError as e:
        sys.exit(f"cannot read config: {e}")

    pad_in_name = find_port(args.launchpad, mido.get_input_names(), "input")
    pad_out_name = find_port(args.launchpad, mido.get_output_names(), "output")
    target_name = find_port(args.out, mido.get_output_names(), "output")
    translator = Translator(config)

    for sig in STOP_SIGNALS:
        signal.signal(sig, _raise_stop)
    with (
        mido.open_input(pad_in_name) as pad_in,
        mido.open_output(pad_out_name) as pad_out,
        mido.open_output(target_name) as target,
    ):
        try:
            log("info", f"discarded {discard_pending(pad_in)} stale Launchpad messages")
            send(translator.startup(), target, pad_out)
            log("info", f"ready: launchpad {pad_in_name!r} → out {target_name!r}")
            for msg in pad_in:
                log("in", str(msg))
                send(translator.handle(msg), target, pad_out)
        except Stop as e:
            log("info", f"stop: {e}")
        finally:
            for sig in STOP_SIGNALS:
                signal.signal(
                    sig, signal.SIG_IGN
                )  # a second signal must not skip the LED reset
            pad_out.send(launchpad.reset())
            log("led", "reset (all LEDs off)")


if __name__ == "__main__":
    main()
