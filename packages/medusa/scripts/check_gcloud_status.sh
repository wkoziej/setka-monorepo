#!/bin/bash
# Quick Google Cloud status check

echo "🔍 Google Cloud Status Check"
echo "=============================="

# Check if gcloud is installed
if command -v gcloud &> /dev/null; then
    echo "✅ Google Cloud CLI: ZAINSTALOWANE"
    echo "   Wersja: $(gcloud --version | head -n1)"

    # Check authentication
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null 2>&1; then
        current_account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1)
        echo "✅ Authentication: AKTYWNE"
        echo "   Konto: $current_account"

        # Check current project
        current_project=$(gcloud config get-value project 2>/dev/null)
        if [[ -n "$current_project" ]]; then
            echo "✅ Aktywny projekt: $current_project"

            # Check if YouTube API is enabled
            if gcloud services list --enabled --filter="name:youtube.googleapis.com" --format="value(name)" | grep -q youtube; then
                echo "✅ YouTube Data API v3: WŁĄCZONE"
            else
                echo "❌ YouTube Data API v3: WYŁĄCZONE"
            fi
        else
            echo "⚠️  Brak aktywnego projektu"
        fi
    else
        echo "❌ Authentication: BRAK"
    fi
else
    echo "❌ Google Cloud CLI: BRAK"
    echo ""
    echo "Instalacja opcje:"
    echo "1. sudo snap install google-cloud-cli --classic"
    echo "2. ./setup_youtube_api.sh (automatyczna instalacja)"
fi

echo ""
echo "📁 Pliki credentials:"
if [[ -f "client_secrets.json" ]]; then
    echo "✅ client_secrets.json: ISTNIEJE"

    # Validate JSON
    if python3 -c "import json; json.load(open('client_secrets.json'))" 2>/dev/null; then
        echo "✅ Format JSON: PRAWIDŁOWY"

        # Show client info
        CLIENT_ID=$(python3 -c "import json; data=json.load(open('client_secrets.json')); print(data.get('installed', data.get('web', {})).get('client_id', 'N/A'))" 2>/dev/null)
        echo "   Client ID: ${CLIENT_ID:0:20}..."
    else
        echo "❌ Format JSON: NIEPRAWIDŁOWY"
    fi
else
    echo "❌ client_secrets.json: BRAK"
fi

if [[ -f "credentials.json" ]]; then
    echo "✅ credentials.json: ISTNIEJE (auth tokens)"
else
    echo "⚠️  credentials.json: BRAK (potrzebna autentykacja)"
fi

echo ""
echo "🧪 Status testów:"
echo "1. Testy jednostkowe (mocki): GOTOWE"
echo "2. Testy integracyjne: $(if [[ -f "client_secrets.json" ]]; then echo "GOTOWE"; else echo "POTRZEBNE CREDENTIALS"; fi)"
echo "3. Rzeczywiste API: $(if [[ -f "client_secrets.json" && -f "credentials.json" ]]; then echo "GOTOWE"; else echo "POTRZEBNA AUTENTYKACJA"; fi)"

echo ""
echo "📋 Następne kroki:"
if ! command -v gcloud &> /dev/null; then
    echo "1. ./setup_youtube_api.sh (pełny setup)"
elif [[ ! -f "client_secrets.json" ]]; then
    echo "1. ./setup_youtube_api.sh (dokończ setup)"
elif [[ ! -f "credentials.json" ]]; then
    echo "1. python youtube_manual_test.py (test authentication)"
else
    echo "1. python youtube_manual_test.py (test upload)"
    echo "2. python -m pytest tests/integration/test_youtube_real_api.py -v"
fi
