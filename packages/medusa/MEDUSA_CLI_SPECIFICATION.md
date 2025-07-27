# Medusa CLI Specification

## 📋 Cel

Implementacja minimalnego CLI dla biblioteki Medusa umożliwiającego upload wideo na YouTube z poziomu fermata.

## 🎯 Wymagania Funkcjonalne

### F1: Command Line Interface

**F1.1 Upload Command**
```bash
uv run --package medusa upload <video_path> --config <config_path> [OPTIONS]
```

**Argumenty:**
- `video_path` (pozycyjny, wymagany) - ścieżka do pliku wideo
- `--config` (wymagany) - ścieżka do pliku konfiguracji JSON

**Opcje:**
- `--title` - tytuł wideo (domyślnie: auto-generated z timestamp)
- `--description` - opis wideo (domyślnie: "Uploaded via Medusa")
- `--privacy` - ustawienia prywatności (domyślnie: "private")
  - Wartości: `private`, `unlisted`, `public`
- `--tags` - tagi wideo (opcjonalne, rozdzielone przecinkami)

**Wyjście:**
- Sukces: kod 0, URL wideo na stdout
- Błąd: kod != 0, komunikat błędu na stderr

### F1.2 Help Command
```bash
uv run --package medusa --help
uv run --package medusa upload --help
```

## 🏗️ Architektura

### Struktura plików (TDD approach)
```
packages/medusa/
├── src/medusa/
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── commands.py      # Upload command implementation
│   │   └── validators.py    # Input validation (DRY)
│   └── main.py             # CLI entry point (KISS)
├── tests/
│   ├── cli/
│   │   ├── test_commands.py     # Tests dla upload command
│   │   ├── test_validators.py   # Tests dla validation
│   │   └── test_integration.py  # Integration tests
│   └── fixtures/
│       ├── test_config.json
│       └── test_video.mp4
└── pyproject.toml          # CLI dependencies
```

### Komponenty (KISS principle)

**1. CLI Parser (Click-based)**
- Jedna komenda: `upload`
- Prosta walidacja argumentów
- Jasne komunikaty błędów

**2. Config Loader (DRY)**
- Wykorzystuje istniejący `ConfigLoader`
- Walidacja konfiguracji YouTube
- Informative error messages

**3. Upload Orchestrator (Single Responsibility)**
- Wykorzystuje istniejący `YouTubeUploader`
- Async execution z sync CLI wrapper
- Progress reporting na stderr

**4. Error Handling (Consistent)**
- Wykorzystuje istniejące `MedusaError` exceptions
- Exit codes zgodne z Unix conventions
- User-friendly error messages

## 📝 API Design

### Command Interface
```python
@click.command()
@click.argument('video_path', type=click.Path(exists=True, readable=True))
@click.option('--config', required=True, type=click.Path(exists=True, readable=True))
@click.option('--title', help='Video title')
@click.option('--description', help='Video description')
@click.option('--privacy', default='private', type=click.Choice(['private', 'unlisted', 'public']))
@click.option('--tags', help='Comma-separated tags')
def upload(video_path, config, title, description, privacy, tags):
    """Upload video to YouTube using Medusa."""
```

### Config Format (zgodny z istniejącym)
```json
{
    "youtube": {
        "client_secrets_file": "path/to/client_secrets.json",
        "credentials_file": "path/to/credentials.json"
    }
}
```

### Output Format
**Sukces:**
```
✅ Upload successful: https://www.youtube.com/watch?v=abc123
```

**Błąd:**
```
❌ Upload failed: Authentication failed - check your credentials
```

## 🧪 Test Strategy (TDD)

### Unit Tests
1. **Command Parsing Tests**
   - Valid arguments
   - Invalid arguments
   - Missing required options
   - Default values

2. **Validation Tests**
   - File existence validation
   - Config file validation
   - Privacy option validation
   - Video file format validation

3. **Integration Tests**
   - Full upload workflow (with mocks)
   - Error scenarios
   - Progress reporting

### Test Fixtures
- `test_config.json` - valid config
- `test_config_invalid.json` - invalid config
- `test_video.mp4` - small test video
- Mock YouTube API responses

## 🔗 Integracja z Fermata

### Istniejące wywołanie w ProcessRunner
```rust
// packages/fermata/src-tauri/src/services/process_runner.rs
pub async fn run_medusa_upload(&self, video_path: &Path, config_path: &Path) -> anyhow::Result<ProcessResult> {
    let mut cmd = AsyncCommand::new(&self.uv_path);
    cmd.args(&["run", "--package", "medusa", "upload"])
        .arg(video_path)
        .args(&["--config", &config_path.to_string_lossy()])
        .current_dir(&self.workspace_root);

    self.execute_command(cmd).await
}
```

### Wymagane zmiany
1. Aktualizacja `pyproject.toml` z CLI entry point
2. Implementacja `medusa.main:main`
3. Brak zmian w fermata (już gotowe!)

## ✅ Definition of Done

1. **Implementacja zgodna z TDD**
   - Testy napisane przed kodem
   - 100% coverage dla CLI logic
   - Integration tests przechodzą

2. **CLI działa z fermata**
   - `ProcessRunner.run_medusa_upload()` działa
   - Upload do YouTube successful
   - Error handling działa

3. **Kod zgodny z DRY/KISS**
   - Wykorzystuje istniejące komponenty
   - Minimalna implementacja
   - Czytelny i maintainable

4. **Dokumentacja**
   - README updated
   - CLI help messages
   - Error messages are helpful

## 🚀 Success Criteria

- [ ] CLI zainstalowany: `uv run --package medusa --help` działa
- [ ] Upload działa: video zostaje uploadowany na YouTube
- [ ] Fermata integracja: pipeline `Rendered → Upload` działa
- [ ] Error handling: błędy są czytelnie raportowane
- [ ] Tests pass: wszystkie testy przechodzą
