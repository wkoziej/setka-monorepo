
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
- [ ] Auto-reconnect: gdy subskrypcja wejścia PACER znika (re-enumeracja/replug), most ma
      re-otworzyć port zamiast tylko logować „Found N rtmidi port(s)" co ~2,5 s.
- [ ] `/health` ma sprawdzać REALNĄ subskrypcję wejścia (np. po `aconnect`/stanie portu),
      nie samo istnienie obiektu portu — inaczej raportuje `pacer_input_open=true` przy
      zerwanym wejściu.
