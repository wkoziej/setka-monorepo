# launchpad-rc600

Launchpad Mini (1st gen) → Boss RC-600 MIDI translator (`lp-rc600`) and a virtual RC-600 (`rc600-sim`).

- `lp-rc600` reads the Launchpad pads and sends CC on channel 13 to a target port (the virtual or the real RC-600). The pad LEDs show the state.
- `rc600-sim` opens the ALSA port `RC-600 SIM`, applies the RC-600 ASSIGN rules from `assign.toml`, and shows 6 PLAY LEVEL bars, 4 Track FX states, and a message log.

`assign.toml` is the single source of the mapping. Both programs and the ASSIGN sheet below use it.

## Layout

```
col:  1    2    3    4    5    6    7     8
row0 100  100  100  100  100  100  FX A  FX B
row1  86   86   86   86   86   86  FX C  FX D
row2  71   …                         (unused)
row3  57
row4  43
row5  29
row6  14
row7   0    0    0    0    0    0   (unused)
     TRK1 TRK2 TRK3 TRK4 TRK5 TRK6
```

- Fader pad: sets the TRK level. LEDs: a bar from the pressed row down; level 0 = dark column.
- FX pad: flips the FX and sends an explicit value (127 = on, 0 = off). Red = on, dim green = off.
- Unused pads and round buttons: ignored, with a log line.
- At start, the translator sends all levels 71 (about 70%, so you can raise them to unity 100) and all FX off. **This changes the sound on the real RC-600.**

## Install and test (development machine)

```
uv sync
uv run pytest -q
```

Tests need the ALSA sequencer (`snd_seq`); they use real virtual ports.

## Run

Run order: start `rc600-sim` first, then `lp-rc600`.

```
uv run rc600-sim                 # TUI; --plain prints one log line per event
uv run lp-rc600 --out "RC-600 SIM"
```

Options: `--config PATH` (default `assign.toml`) for both programs; `--launchpad PART` (default `Launchpad Mini`) for `lp-rc600`. Ports are found by a name part. If no port or more than one port matches, the program stops and lists the ports.

- At start, `lp-rc600` drops Launchpad presses that waited in the device buffer (log: "discarded N stale Launchpad messages"), so they cannot change the start state.
- Ctrl+C, SIGTERM, or SIGHUP (SSH drop) stops `lp-rc600` and turns off all LEDs.
- A port that disappears while `lp-rc600` runs is not handled. Restart `lp-rc600` after a simulator restart or a Launchpad reconnect.
- For the real RC-600: `uv run lp-rc600 --out "RC-600 MIDI"` (port `RC-600 MIDI 1`; the name part "RC-600" alone also matches "RC-600 SIM").

## Run on the live host (auto-deploy)

On the host that runs the paternologia auto-deploy (lubudu), `lp-rc600 --out "RC-600 MIDI"` starts at boot and restarts when it exits.

- The paternologia cron job `autoupdate.sh` checks `master` every 2 minutes. It runs `deploy/remote/install.sh` only when a commit changes `packages/launchpad-rc600`.
- `install.sh` installs the package into `~/launchpad-rc600/venv` (system Python, because no i686 Python 3.12+ build is available from uv), adds an `@reboot` cron entry for `run.sh`, and restarts `lp-rc600`.
- **Each restart sends the startup state (levels 71, FX off) to the RC-600.** Thus, do not push changes to this package to `master` while you play.
- `run.sh` restarts `lp-rc600` 5 s after it exits. If the Launchpad or the RC-600 is not connected, it tries again every 5 s.
- Log: `~/launchpad-rc600/lp-rc600.log`.

## ASSIGN sheet for the real RC-600

Set `SYSTEM → MIDI → RX CH CTL = 13`. Slots 1–4 are Pacer (CC 1–4), do not change them. Slots 15–16 are free.

ASSIGN is stored **per memory**. Enter the slots and WRITE them to every memory where the Launchpad is used (manual, "ASSIGN", NOTE).

| Slot | SW | SOURCE | SOURCE MODE | ACT LO | ACT HI | TARGET | TARGET MIN | TARGET MAX |
|---|---|---|---|---|---|---|---|---|
| 5 | ON | MIDI CC#64 | MOMENT | 0 | 127 | TRK1 LEVEL | 0 | 100 |
| 6 | ON | MIDI CC#65 | MOMENT | 0 | 127 | TRK2 LEVEL | 0 | 100 |
| 7 | ON | MIDI CC#66 | MOMENT | 0 | 127 | TRK3 LEVEL | 0 | 100 |
| 8 | ON | MIDI CC#67 | MOMENT | 0 | 127 | TRK4 LEVEL | 0 | 100 |
| 9 | ON | MIDI CC#68 | MOMENT | 0 | 127 | TRK5 LEVEL | 0 | 100 |
| 10 | ON | MIDI CC#69 | MOMENT | 0 | 127 | TRK6 LEVEL | 0 | 100 |
| 11 | ON | MIDI CC#70 | MOMENT | 64 | 127 | T FX A | OFF | ON |
| 12 | ON | MIDI CC#71 | MOMENT | 64 | 127 | T FX B | OFF | ON |
| 13 | ON | MIDI CC#72 | MOMENT | 64 | 127 | T FX C | OFF | ON |
| 14 | ON | MIDI CC#73 | MOMENT | 64 | 127 | T FX D | OFF | ON |

Verified on the RC-600 (2026-11-01, slots 5 and 11): FX with ACT LO 64 — 127 → on, 127 again → on, 0 → off; level — CC 0/37/73/90/109/127 → 0/29/57/71/86/100.

`T FX A–D` acts on the **currently selected FX bank**. If another bank is selected, the pads switch other effects.

## Manual check with the physical Launchpad

1. Start `rc600-sim`, then `lp-rc600 --out "RC-600 SIM"`. The simulator shows levels 71 and FX off; the Launchpad shows green bars from row 3 down in columns 1–6 and dim green FX pads.
2. In each fader column, press every row from top to bottom. The simulator shows 100, 86, 71, 57, 43, 29, 14, 0; the LED bar follows; at 0 the column is dark.
3. Press each FX pad twice: on (red), then off (dim green). The simulator agrees.
4. Press an unused pad (for example column 7, row 5) and a round button: no change; `lp-rc600` logs "ignored".
5. Press Ctrl+C in `lp-rc600`: all LEDs turn off.

## Checks on the real RC-600 (in this order)

1. ~~**`T FX` with SOURCE MODE = MOMENT**~~ (done, see the ASSIGN sheet): CC 127 → FX on; CC 127 again → FX still on; CC 0 → FX off. Check that TARGET MIN/MAX for `T FX` shows OFF/ON. The FX `SW MODE` should have no effect.
2. ~~**Level rounding:**~~ (done: rows 71 and 86 are correct) for each of the 8 rows, read PLAY LEVEL on the RC-600 screen. Look closely at the rows for levels 71 and 86 (CC 90 and 109). If they differ, change only `cc_for_level` in `src/launchpad_rc600/translator.py`.
3. ~~**USB MIDI from Linux:**~~ (done on lubudu, port `RC-600 MIDI 1`) the RC-600 appears in `aconnect -l` and reacts to `lp-rc600`.
4. **`USB IN THRU = OFF`** (SYSTEM → MIDI): otherwise CC 64–73 on channel 13 reach the downstream devices (Model:Samples, MicroFreak).

## RC-600 memories

ASSIGN and track state are per memory. After a memory change (for example a Program Change from Pacer), the Launchpad LEDs can show a stale state. The simulator logs Program Change as "memory change, state not modeled". The translator has no logic for this.

## What the simulator does not prove

The simulator checks port wiring, channel 13, CC numbers, the pad layout, LED agreement, and the config limits. It uses the same assumptions as the translator for the FX threshold (value ≥ 64 → on) and the level rounding (round half up), so it does not prove how the real RC-600 behaves. The checks above do that.
