# ABOUTME: Tests for the watcher tick — watchdog ping must survive subsystem faults.
# ABOUTME: Guards the failure-isolation rule: an OBS/PACER error never starves it.

from types import SimpleNamespace

from paternologia import main as main_mod


class _Listener:
    def __init__(self, boom=False):
        self._boom = boom
        self.polled = 0

    def poll_reconnect(self):
        self.polled += 1
        if self._boom:
            raise RuntimeError("rtmidi exploded")


class _Obs:
    def __init__(self, boom=False):
        self._boom = boom
        self.ensured = 0
        self.connected = True

    def ensure_connected(self):
        self.ensured += 1
        if self._boom:
            raise ConnectionError("obs hung")
        return True


def _app(listener=None, obs=None):
    state = SimpleNamespace(
        midi_listener=listener,
        obs_client=obs,
        last_heartbeat_ts=None,
        obs_connected=False,
    )
    return SimpleNamespace(state=state)


async def test_tick_pings_watchdog_and_stamps_heartbeat(monkeypatch):
    pings = []
    monkeypatch.setattr(main_mod, "_sd_notify", pings.append)
    app = _app(listener=_Listener(), obs=_Obs())
    await main_mod._watch_tick(app)
    assert pings == ["WATCHDOG=1"]
    assert app.state.last_heartbeat_ts is not None
    assert app.state.obs_connected is True


async def test_watchdog_pinged_even_when_pacer_poll_raises(monkeypatch):
    pings = []
    monkeypatch.setattr(main_mod, "_sd_notify", pings.append)
    app = _app(listener=_Listener(boom=True), obs=_Obs())
    await main_mod._watch_tick(app)
    # The ping must precede subsystem maintenance, so a raising poll cannot
    # suppress it — this is the core failure-isolation guarantee.
    assert pings == ["WATCHDOG=1"]
    assert app.state.last_heartbeat_ts is not None


async def test_watchdog_pinged_even_when_obs_maintenance_raises(monkeypatch):
    pings = []
    monkeypatch.setattr(main_mod, "_sd_notify", pings.append)
    obs = _Obs(boom=True)
    app = _app(listener=_Listener(), obs=obs)
    await main_mod._watch_tick(app)
    assert pings == ["WATCHDOG=1"]
    assert obs.ensured == 1  # maintenance attempted off the loop thread
