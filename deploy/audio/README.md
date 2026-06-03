# Drop-iny audio (systemd --user)

## wireplumber — auto-restart po wybudzeniu

**Problem:** po suspend/resume `wireplumber` bywa ubijany SIGTERM-em (albo wychodzi czysto).
Pakietowy `Restart=on-failure` traktuje to jako czysty stop i **nie wskrzesza** usługi —
menedżer sesji audio zostaje martwy, aż ręcznie zrobisz `systemctl --user start wireplumber`.

**Fix:** drop-in `wireplumber.service.d/override.conf` ustawia `Restart=always` (+ `RestartSec=2`,
`StartLimitIntervalSec=0`), więc systemd sam podnosi wireplumbera po SIGTERM/czystym wyjściu.
Nie rusza intencjonalnego `systemctl --user stop`.

`pipewire`/`pipewire-pulse` są socket-activated i wracają same — drop-in ich nie dotyczy.

## Instalacja

```bash
deploy/audio/install.sh
systemctl --user restart wireplumber   # by Restart=always weszło w życie od razu
```

## Weryfikacja

```bash
systemctl --user show wireplumber -p Restart   # → Restart=always
# Test zachowania (SIGTERM jak przy wybudzeniu → auto-restart):
systemctl --user kill -s TERM wireplumber && sleep 4 && systemctl --user is-active wireplumber  # → active
```

**Ograniczenie:** `always` łapie wyjście procesu (SIGTERM, crash, czyste wyjście), ale **nie**
zawiśnięcie (proces żyje, lecz nie odpowiada). Gdyby po wybudzeniu zdarzał się zawis, trzeba
będzie dołożyć watchdog albo hook na resume.
