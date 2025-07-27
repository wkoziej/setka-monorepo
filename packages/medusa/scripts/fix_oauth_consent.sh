#!/bin/bash
# Fix OAuth Consent Screen - Add Test User

echo "🔧 OAuth Consent Screen Fix"
echo "============================"

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
USER_EMAIL="tomiejscenaspam@gmail.com"

echo "📋 Problem: Aplikacja medusa nie przeszła weryfikacji Google"
echo "💡 Rozwiązanie: Dodaj siebie jako test user"
echo ""

if [[ -n "$PROJECT_ID" ]]; then
    echo "🎯 Projekt: $PROJECT_ID"
    echo "👤 Email do dodania: $USER_EMAIL"
    echo ""

    echo "📝 Kroki do wykonania:"
    echo "1. Otwórz link:"
    echo "   https://console.cloud.google.com/apis/credentials/consent?project=$PROJECT_ID"
    echo ""
    echo "2. W sekcji 'Test users':"
    echo "   - Kliknij '+ ADD USERS'"
    echo "   - Dodaj email: $USER_EMAIL"
    echo "   - Kliknij 'Save'"
    echo ""
    echo "3. Sprawdź konfigurację:"
    echo "   ✅ User Type: External"
    echo "   ✅ Publishing status: Testing"
    echo "   ✅ Test users: $USER_EMAIL"
    echo ""

    read -p "Naciśnij Enter gdy dodasz test user..."

    echo "🧪 Testowanie autoryzacji..."
    echo "Uruchamiam test ponownie..."

    # Test authorization
    source venv/bin/activate
    python youtube_manual_test.py

else
    echo "❌ Nie można znaleźć aktywnego projektu"
    echo "Uruchom: gcloud config set project YOUR_PROJECT_ID"
fi
