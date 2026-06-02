# ABOUTME: Pydantic models for Paternologia - MIDI device configurations and songs.
# ABOUTME: Defines Device, Action, PacerButton, DeviceSettings, and Song schemas.

import re
from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator


class ActionType(str, Enum):
    """Types of MIDI actions that can be performed."""

    PRESET = "preset"
    PATTERN = "pattern"
    CC = "cc"
    NOTE = "note"


class Device(BaseModel):
    """MIDI device definition with supported action types."""

    id: str = Field(..., description="Unique device identifier")
    name: str = Field(..., description="Display name of the device")
    description: str = Field(default="", description="Device description")
    action_types: list[ActionType] = Field(
        default_factory=list, description="Supported action types"
    )
    midi_channel: int = Field(
        default=0, ge=0, le=15, description="MIDI channel (0-15) for this device"
    )


class DevicesConfig(BaseModel):
    """Configuration file structure for devices.yaml."""

    devices: list[Device] = Field(default_factory=list)


class Action(BaseModel):
    """Single MIDI action performed by a PACER button."""

    device: str = Field(..., description="Target device ID")
    type: ActionType = Field(..., description="Action type")
    value: int | str | None = Field(
        default=None, description="Action value (preset/pattern number)"
    )
    cc: int | None = Field(default=None, description="MIDI CC number (for cc type)")
    label: str | None = Field(default=None, description="Optional display label")
    bank_lsb: int = Field(
        default=0, ge=0, le=127, description="Bank LSB (CC 32) for PRESET type"
    )
    bank_msb: int = Field(
        default=0, ge=0, le=127, description="Bank MSB (CC 0) for PRESET type"
    )
    note: str | int | None = Field(
        default=None,
        description="MIDI note (musical notation like 'C4' or number 0-127)",
    )
    velocity: int | None = Field(
        default=None, ge=1, le=127, description="Note velocity (1-127)"
    )

    @model_validator(mode="after")
    def validate_action_fields(self) -> "Action":
        """Walidacja pól w zależności od typu akcji."""
        if self.type == ActionType.CC:
            if self.value is None:
                raise ValueError("ActionType.CC wymaga pola 'value' (0-127)")
            if not isinstance(self.value, int) or self.value < 0 or self.value > 127:
                raise ValueError(
                    f"ActionType.CC value musi być 0-127, otrzymano: {self.value}"
                )
        if self.type == ActionType.NOTE:
            if self.note is None:
                raise ValueError("ActionType.NOTE wymaga pola 'note'")
        return self


class PacerButton(BaseModel):
    """PACER button configuration with up to 6 actions."""

    name: str = Field(..., description="Button display name")
    actions: Annotated[list[Action], Field(max_length=6)] = Field(
        default_factory=list, description="Actions to perform (max 6)"
    )


VALID_PRESETS = {f"{row}{col}" for row in "ABCD" for col in range(1, 7)}


class PacerExportSettings(BaseModel):
    """Ustawienia eksportu/transferu do Pacera."""

    target_preset: str = Field(
        default="A1",
        description="Docelowy preset Pacera (A1-D6)",
    )

    @field_validator("target_preset")
    @classmethod
    def validate_preset(cls, v: str) -> str:
        """Waliduje, że preset jest w zakresie A1-D6."""
        v = v.upper()
        if v not in VALID_PRESETS:
            raise ValueError(f"Invalid preset: {v}. Valid: A1-D6.")
        return v


class PacerConfig(BaseModel):
    """Globalna konfiguracja portu amidi."""

    device_name: str = Field(
        default="PACER",
        description="Nazwa urządzenia MIDI do auto-detekcji (szukana w amidi -l)",
    )
    amidi_timeout_seconds: int = Field(
        default=5,
        ge=1,
        le=30,
        description="Timeout dla amidi w sekundach",
    )
    sysex_interval_ms: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Interwał między wiadomościami SysEx w ms (CRITICAL: 20 wymagane!)",
    )
    record_trigger_channel: int = Field(
        default=0,
        ge=0,
        le=15,
        description="Kanał MIDI (0-15) not triggera record na PACER (MIDI2 = ch1 = 0)",
    )
    record_start_note: int = Field(
        default=94,
        ge=0,
        le=127,
        description="Nota startująca nagranie OBS + Bitwig (PACER MIDI2)",
    )
    record_stop_note: int = Field(
        default=93,
        ge=0,
        le=127,
        description="Nota zatrzymująca nagranie OBS + Bitwig (PACER MIDI2)",
    )
    record_trigger_port: str | None = Field(
        default=None,
        description=(
            "Opcjonalny fragment nazwy portu, na którym akceptowane są noty "
            "triggera record (np. 'MIDI2'). None = dowolny port PACER."
        ),
    )

    @model_validator(mode="after")
    def _distinct_record_notes(self) -> "PacerConfig":
        """Start i stop muszą się różnić, inaczej stop nigdy nie zadziała."""
        if self.record_start_note == self.record_stop_note:
            raise ValueError(
                "record_start_note i record_stop_note muszą się różnić "
                f"(oba = {self.record_start_note})"
            )
        return self


class ObsConfig(BaseModel):
    """Połączenie z OBS przez obs-websocket v5."""

    enabled: bool = Field(
        default=True, description="Czy paternologia steruje nagrywaniem OBS"
    )
    host: str = Field(default="localhost", description="Host obs-websocket")
    port: int = Field(default=4455, ge=1, le=65535, description="Port obs-websocket")
    password: str = Field(default="", description="Hasło obs-websocket (puste = brak)")


class SongMetadata(BaseModel):
    """Song metadata information."""

    id: str = Field(
        ..., description="Unique song identifier (filename without extension)"
    )
    name: str = Field(..., description="Display name of the song")
    author: str = Field(default="", description="Song author")
    created: date = Field(default_factory=date.today, description="Creation date")
    notes: str = Field(default="", description="Additional notes")
    pacer_export: PacerExportSettings = Field(
        default_factory=PacerExportSettings,
        description="Ustawienia eksportu Pacera",
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Wymusza kebab-case i bezpieczne ID dla plików."""
        v = v.strip()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", v):
            raise ValueError(
                "Song ID musi być kebab-case: małe litery, cyfry, myślniki."
            )
        return v


class Song(BaseModel):
    """Complete song configuration with PACER buttons."""

    song: SongMetadata = Field(..., description="Song metadata")
    pacer: Annotated[list[PacerButton], Field(max_length=6)] = Field(
        default_factory=list, description="PACER button configurations (max 6)"
    )
