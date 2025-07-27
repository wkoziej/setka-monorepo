# Jak uzyskać credentials Facebook do testowania

## Krok 1: Utwórz aplikację Facebook

1. Idź na https://developers.facebook.com/
2. Kliknij "My Apps" → "Create App"
3. Wybierz "Business" jako typ aplikacji
4. Podaj nazwę aplikacji (np. "Medusa Test")
5. Kliknij "Create App"

## Krok 2: Dodaj produkt "Facebook Login"

1. W panelu aplikacji kliknij "Add Product"
2. Znajdź "Facebook Login" i kliknij "Set Up"
3. Wybierz "Web" jako platformę
4. Podaj URL swojej strony (może być localhost dla testów)

## Krok 3: Skonfiguruj uprawnienia

1. Idź do "App Review" → "Permissions and Features"
2. Znajdź i dodaj uprawnienia:
   - `pages_manage_posts` - do publikowania postów
   - `pages_read_engagement` - do czytania danych strony
   - `pages_show_list` - do wyświetlania listy stron

## Krok 4: Uzyskaj Page Access Token

### Opcja A: Graph API Explorer (najłatwiejsza)
1. Idź na https://developers.facebook.com/tools/explorer/
2. Wybierz swoją aplikację z listy
3. Kliknij "Generate Access Token"
4. Wybierz uprawnienia: `pages_manage_posts`, `pages_read_engagement`
5. Skopiuj token

### Opcja B: Access Token Tool
1. Idź na https://developers.facebook.com/tools/accesstoken/
2. Znajdź swoją aplikację
3. Kliknij "Generate Token" dla User Token
4. Autoryzuj aplikację
5. Skopiuj token

## Krok 5: Znajdź Page ID

### Metoda 1: Graph API Explorer
1. W Graph API Explorer wklej token z kroku 4
2. W polu zapytania wpisz: `me/accounts`
3. Kliknij "Submit"
4. Znajdź swoją stronę na liście i skopiuj `id`

### Metoda 2: Ustawienia strony Facebook
1. Idź na swoją stronę Facebook
2. Kliknij "Settings" → "Page Info"
3. Znajdź "Page ID" na dole strony

## Krok 6: Testowanie

1. Otwórz plik `examples/test_real_scheduled_facebook.py`
2. Zamień `TWÓJ_PAGE_ID` na rzeczywisty Page ID
3. Zamień `TWÓJ_ACCESS_TOKEN` na rzeczywisty token
4. Uruchom test:
   ```bash
   uv run python examples/test_real_scheduled_facebook.py
   ```

## Ważne uwagi

### Bezpieczeństwo
- **NIE COMMITUJ** credentials do repozytorium
- Używaj zmiennych środowiskowych w produkcji
- Token ma ograniczony czas życia (zwykle 1-2 godziny)

### Limity Facebook API
- Minimalne opóźnienie dla zaplanowanych postów: ~10 minut
- Maksymalne opóźnienie: ~6 miesięcy
- Limit postów na godzinę: zależny od typu strony

### Troubleshooting

**Błąd: "Invalid access token"**
- Token wygasł - wygeneruj nowy
- Sprawdź czy token ma odpowiednie uprawnienia

**Błąd: "Insufficient permissions"**
- Dodaj brakujące uprawnienia w App Review
- Sprawdź czy jesteś adminem strony

**Błąd: "Invalid page ID"**
- Sprawdź czy Page ID jest prawidłowy
- Sprawdź czy masz dostęp do tej strony

## Przykład konfiguracji

```python
FACEBOOK_CONFIG = {
    "page_id": "123456789012345",  # Twój rzeczywisty Page ID
    "access_token": "EAABwzLixnjYBO1234567890..."  # Twój rzeczywisty token
}
```

## Gdzie sprawdzić zaplanowane posty

Po utworzeniu zaplanowanego postu możesz go zobaczyć w:
1. **Facebook Creator Studio** → Content Library → Posts
2. **Facebook Business Suite** → Content → Posts
3. **Strona Facebook** → Publishing Tools → Scheduled Posts

Zaplanowane posty będą oznaczone jako "Scheduled" i będą miały datę publikacji.
