# Specyfikacja Biblioteki Medusa (Media Upload & Social Automation)

## Cel

Biblioteka **Medusa** ma na celu uproszczenie i automatyzację procesu przesyłania różnych typów mediów (w tym plików wideo) do serwisów hostingowych (np. YouTube, Vimeo, Google Drive) oraz publikacji powiązanych treści na platformach społecznościowych (np. Facebook, Twitter, LinkedIn).

## Wymagania funkcjonalne

### Podstawowa funkcjonalność:

- Automatyczny upload plików wideo na serwis YouTube.
- Automatyczne publikowanie posta na Facebooku zawierającego link do przesłanego wideo.
- Możliwość ustawienia parametrów posta (tekst posta, tytuł, opis filmu, prywatność).

### Rozszerzalność:

- Obsługa innych platform hostingowych (np. Vimeo, Google Drive).
- Obsługa dodatkowych platform społecznościowych (Twitter, LinkedIn, Instagram).
- Obsługa różnych typów plików (wideo, zdjęcia, dokumenty PDF, audio).

## Architektura biblioteki

### Moduły główne:

- **Uploader**: Odpowiada za przesyłanie plików do określonych platform hostingowych.
  - Klasy: `YouTubeUploader`, `VimeoUploader`, `GoogleDriveUploader` (opcjonalne).
- **Publisher**: Odpowiada za publikację treści na platformach społecznościowych.
  - Klasy: `FacebookPublisher`, `TwitterPublisher`, `LinkedInPublisher` (opcjonalne).
- **MedusaCore**: Centralny interfejs użytkownika, który integruje moduły Uploader i Publisher.

### Przykładowe API:

```python
from medusa import MedusaCore

medusa = MedusaCore(config_file="medusa_config.json")

medusa.publish(
    media_file="path/to/video.mp4",
    platform="youtube",
    metadata={
        "title": "Mój nowy film",
        "description": "Opis filmu",
        "tags": ["demo", "test"],
        "privacy": "unlisted"
    },
    social_platform="facebook",
    post_content="Sprawdźcie mój najnowszy film!"
)
```

## Konfiguracja

- Konfiguracja przechowywana w pliku JSON lub zmiennych środowiskowych.
- Obejmuje dane uwierzytelniające do API poszczególnych platform.

### Przykład konfiguracji (`medusa_config.json`):

```json
{
    "youtube": {
        "client_secrets_file": "secrets/youtube_client_secrets.json",
        "credentials_file": "secrets/youtube_credentials.json"
    },
    "facebook": {
        "page_id": "1234567890",
        "access_token": "your_facebook_access_token"
    }
}
```

## Wymagania techniczne

- Python 3.8+
- Biblioteki:
  - `google-api-python-client`
  - `google-auth-oauthlib`
  - `requests`
  - opcjonalnie `PyDrive2` (dla Google Drive)

## Możliwość obsługi wielu plików i typów

- Biblioteka jest projektowana z myślą o rozszerzalności, umożliwiając obsługę wielu typów mediów (wideo, zdjęcia, dokumenty).
- Możliwa jest obsługa batch upload (jednoczesne przesyłanie wielu plików).

## Zagrożenia i przeciwwskazania

- **Bezpieczeństwo**: Przechowywanie danych uwierzytelniających i tokenów dostępu wymaga szczególnej uwagi (zalecane stosowanie bezpiecznych magazynów danych jak HashiCorp Vault).
- **API Rate Limits**: Konieczność uwzględnienia limitów API platform hostingowych i społecznościowych.
- **Zgodność z regulaminami**: Konieczność ścisłego przestrzegania regulaminów serwisów (np. ograniczenia publikowania automatycznego na platformach społecznościowych).

## Potencjalny rozwój

- Implementacja obsługi kolejek zadań (Celery, RabbitMQ).
- Integracja z narzędziami monitorującymi status przesyłania i publikacji (logging, monitoring).

