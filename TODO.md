
## 3. Usuń to_dict oraz convert_to_internal
- [ ] Usuń metodę to_dict z BlenderYAMLConfig
- [ ] Usuń metodę convert_to_internal z YAMLConfigLoader
- [ ] Zaktualizuj vse_script.py aby bezpośrednio używał struktury strip_animations
- [ ] Zaktualizuj project_manager.py aby nie używał convert_to_internal
- [ ] Zaktualizuj wszystkie testy

## 4. Dodatkowe zadania
- [ ] Usuń zduplikowany plik config_loader.py z blender_addon
- [ ] Uruchom wszystkie testy aby upewnić się że nic nie zepsuliśmy

## 5. Paternologia: odporność mostu MIDI na re-enumerację PACER-a
Kontekst: 2026-06-03 MIDI przestało działać — PACER re-enumerował się (zmiana `card`),
most wejściowy paternologii zgubił subskrypcję ALSA do PACER-a i jej nie odtworzył.
`/health` dalej raportował `pacer_input_open=true`, mimo że `aconnect -l` nie pokazywał
żadnego połączenia z PACER-em. Ręczny fix: `systemctl --user restart paternologia.service`.
- [x] Auto-reconnect: gdy subskrypcja wejścia PACER znika (re-enumeracja/replug), most ma
      re-otworzyć port zamiast tylko logować „Found N rtmidi port(s)" co ~2,5 s.
      `poll_reconnect` sprawdza teraz realną subskrypcję (`pacer_input_subscribed` po
      `aconnect -l`) i przy zwietrzałych uchwytach robi stop+start.
- [x] `/health` ma sprawdzać REALNĄ subskrypcję wejścia (np. po `aconnect`/stanie portu),
      nie samo istnienie obiektu portu — inaczej raportuje `pacer_input_open=true` przy
      zerwanym wejściu. `pacer_input_open` opiera się teraz na `listener.input_subscribed`.

## 6. Stabilność USB rigu live (re-enumeracja zrywa audio/MIDI)
Kontekst: 2026-06-03 — 15 re-enumeracji USB w ciągu dnia (huby na `power/control=auto`,
brak błędów -71/-110 → runtime-PM, nie brownout). Każdy flap gubi kartę w WirePlumber
(RC-600/Notepad znikają z PipeWire). `setka-live` NIE jest sprawcą (ostatni stop/start
22:14/22:16 = 0 re-enumeracji; preflight tylko czyta). Szczegóły: `deploy/usb/README.md`.
- [x] Preflight blokuje start GUI, gdy brak karty audio rigu w PipeWire
      (`preflight_audio_cards_ok`, `REQUIRED_AUDIO_CARDS=RC-600 Notepad`).
- [ ] **Akcja operatora (sudo):** zainstaluj regułę no-autosuspend albo dodaj
      `usbcore.autosuspend=-1` do GRUB. `sudo deploy/usb/install.sh`.
- [ ] **Akcja operatora (bez sudo):** re-instaluj warstwę live, by nowy preflight wszedł:
      `deploy/live/install.sh`.
- [ ] Fizyka: RC-600/Notepad/PACER na zasilany hub; skróć łańcuch (Notepad 4 poziomy hubów).
- [ ] Jeśli flapy zostają mimo no-autosuspend — rozważ nieinwazyjny re-trigger udev
      brakującej karty (bez restartu wireplumbera, który mruga audio w secie).
