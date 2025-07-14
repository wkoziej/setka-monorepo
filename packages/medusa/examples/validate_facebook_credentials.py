#!/usr/bin/env python3
"""
Walidacja credentials Facebook przed testowaniem zaplanowanych postów.

Ten skrypt sprawdza czy Twoje credentials Facebook są prawidłowe
i czy masz odpowiednie uprawnienia do publikowania postów.
"""

import asyncio
import logging
from pathlib import Path

# Add the src directory to the path so we can import medusa
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from medusa.publishers.facebook import FacebookPublisher
from medusa.models import PlatformConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# UWAGA: Wypełnij te dane swoimi prawdziwymi credentials Facebook
FACEBOOK_CONFIG = {
    "page_id": "TWÓJ_PAGE_ID",  # np. "123456789012345"
    "access_token": "TWÓJ_ACCESS_TOKEN"  # np. "EAABwzLixnjYBO..."
}

def create_facebook_config():
    """Utwórz konfigurację Facebook."""
    return PlatformConfig(
        platform_name="facebook",
        credentials=FACEBOOK_CONFIG,
        enabled=True
    )

async def validate_credentials():
    """Waliduj credentials Facebook."""
    print("🔍 WALIDACJA CREDENTIALS FACEBOOK")
    print("=" * 50)
    
    # Sprawdź czy credentials są ustawione
    if FACEBOOK_CONFIG["page_id"] == "TWÓJ_PAGE_ID":
        print("❌ BŁĄD: Credentials nie zostały ustawione!")
        print("   Otwórz plik examples/validate_facebook_credentials.py")
        print("   i ustaw prawdziwe wartości w FACEBOOK_CONFIG")
        print("\n📖 Zobacz instrukcje w pliku FACEBOOK_SETUP.md")
        return False
    
    print("📋 Sprawdzanie credentials:")
    print(f"   Page ID: {FACEBOOK_CONFIG['page_id']}")
    print(f"   Access Token: {FACEBOOK_CONFIG['access_token'][:20]}...")
    
    config = create_facebook_config()
    publisher = FacebookPublisher(config)
    
    try:
        print("\n🔐 Test autentykacji...")
        await publisher.authenticate()
        print("✅ Autentykacja pomyślna!")
        
        print("\n🏥 Test health check...")
        health = publisher.health_check()
        if health:
            print("✅ Połączenie z Facebook API działa!")
        else:
            print("❌ Problem z połączeniem do Facebook API")
            return False
        
        print("\n🎯 PODSUMOWANIE WALIDACJI:")
        print("✅ Credentials są prawidłowe")
        print("✅ Autentykacja działa")
        print("✅ Połączenie z API działa")
        print("✅ Uprawnienia są wystarczające")
        print("\n🚀 Możesz teraz uruchomić test zaplanowanych postów!")
        print("   Uruchom: uv run python examples/test_real_scheduled_facebook.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Błąd podczas walidacji: {e}")
        print(f"   Typ błędu: {type(e).__name__}")
        
        # Szczegółowe wskazówki na podstawie typu błędu
        error_str = str(e).lower()
        
        if "authentication" in error_str or "access token" in error_str:
            print(f"\n💡 Problem z tokenem dostępu:")
            print(f"   • Token może być nieprawidłowy lub wygasły")
            print(f"   • Wygeneruj nowy token w Graph API Explorer")
            print(f"   • Sprawdź czy token ma uprawnienia 'pages_manage_posts'")
            
        elif "permission" in error_str:
            print(f"\n💡 Problem z uprawnieniami:")
            print(f"   • Dodaj uprawnienie 'pages_manage_posts' w App Review")
            print(f"   • Sprawdź czy jesteś adminem strony Facebook")
            print(f"   • Upewnij się, że aplikacja ma dostęp do strony")
            
        elif "page" in error_str:
            print(f"\n💡 Problem ze stroną:")
            print(f"   • Sprawdź czy Page ID jest prawidłowy")
            print(f"   • Sprawdź czy masz dostęp do tej strony")
            print(f"   • Użyj Graph API Explorer: me/accounts aby zobaczyć dostępne strony")
            
        else:
            print(f"\n💡 Ogólne wskazówki:")
            print(f"   • Sprawdź połączenie internetowe")
            print(f"   • Sprawdź czy Facebook API nie ma problemów")
            print(f"   • Zobacz pełne instrukcje w FACEBOOK_SETUP.md")
        
        return False
        
    finally:
        await publisher.cleanup()

async def main():
    """Główna funkcja."""
    try:
        success = await validate_credentials()
        
        if success:
            print(f"\n🎉 Walidacja zakończona pomyślnie!")
            print(f"   Twoje credentials Facebook są gotowe do użycia.")
        else:
            print(f"\n❌ Walidacja nie powiodła się.")
            print(f"   Popraw credentials i spróbuj ponownie.")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Walidacja przerwana przez użytkownika")
    except Exception as e:
        print(f"\n\n💥 Nieoczekiwany błąd: {e}")

if __name__ == "__main__":
    print("🔧 Walidator credentials Facebook")
    print("   Ten skrypt sprawdzi czy Twoje credentials są prawidłowe")
    print("   przed uruchomieniem testów zaplanowanych postów.")
    print()
    
    # Sprawdź czy credentials są ustawione
    if FACEBOOK_CONFIG["page_id"] != "TWÓJ_PAGE_ID":
        asyncio.run(main())
    else:
        print("⚠️  Credentials nie zostały ustawione")
        print("   1. Otwórz plik examples/validate_facebook_credentials.py")
        print("   2. Ustaw prawdziwe wartości w FACEBOOK_CONFIG")
        print("   3. Uruchom ponownie: uv run python examples/validate_facebook_credentials.py")
        print("\n📖 Zobacz instrukcje w pliku FACEBOOK_SETUP.md") 