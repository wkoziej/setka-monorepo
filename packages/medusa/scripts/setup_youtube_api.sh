#!/bin/bash
# YouTube API Setup Script - Automatyzacja przez Google Cloud CLI

set -e  # Exit on any error

echo "🎬 YouTube API Setup Script"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if gcloud is installed
check_gcloud() {
    if ! command -v gcloud &> /dev/null; then
        print_error "Google Cloud CLI nie jest zainstalowane!"
        echo ""
        echo "Instalacja Google Cloud CLI:"
        echo "1. Snap (Ubuntu/Debian):"
        echo "   sudo snap install google-cloud-cli --classic"
        echo ""
        echo "2. Apt (Ubuntu/Debian):"
        echo "   curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -"
        echo "   echo 'deb https://packages.cloud.google.com/apt cloud-sdk main' | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list"
        echo "   sudo apt-get update && sudo apt-get install google-cloud-cli"
        echo ""
        echo "3. Manual download:"
        echo "   https://cloud.google.com/sdk/docs/install"
        echo ""
        read -p "Czy chcesz zainstalować przez snap? (y/N): " install_snap
        if [[ $install_snap =~ ^[Yy]$ ]]; then
            echo "Instaluję Google Cloud CLI..."
            sudo snap install google-cloud-cli --classic
            print_status "Google Cloud CLI zainstalowane!"
        else
            print_error "Zainstaluj Google Cloud CLI i uruchom skrypt ponownie"
            exit 1
        fi
    else
        print_status "Google Cloud CLI jest zainstalowane"
        gcloud --version
    fi
}

# Authenticate with Google Cloud
authenticate_gcloud() {
    print_info "Sprawdzam authentication..."
    
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null 2>&1; then
        print_warning "Nie jesteś zalogowany do Google Cloud"
        echo "Uruchamiam proces logowania..."
        gcloud auth login
    else
        current_account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1)
        print_status "Zalogowany jako: $current_account"
    fi
}

# List and select/create project
setup_project() {
    print_info "Konfiguracja projektu..."
    
    echo ""
    echo "Dostępne projekty:"
    gcloud projects list --format="table(projectId,name,projectNumber)" || {
        print_warning "Brak dostępu do projektów lub brak projektów"
    }
    
    echo ""
    echo "Opcje:"
    echo "1. Użyj istniejący projekt"
    echo "2. Utwórz nowy projekt"
    read -p "Wybierz opcję (1/2): " project_option
    
    case $project_option in
        1)
            read -p "Podaj Project ID: " PROJECT_ID
            if gcloud projects describe "$PROJECT_ID" > /dev/null 2>&1; then
                print_status "Projekt $PROJECT_ID istnieje"
            else
                print_error "Projekt $PROJECT_ID nie istnieje!"
                exit 1
            fi
            ;;
        2)
            read -p "Podaj nowy Project ID (np. medusa-youtube-test): " PROJECT_ID
            read -p "Podaj nazwę projektu (np. 'Medusa YouTube Test'): " PROJECT_NAME
            
            print_info "Tworzę projekt $PROJECT_ID..."
            gcloud projects create "$PROJECT_ID" --name="$PROJECT_NAME"
            print_status "Projekt utworzony!"
            ;;
        *)
            print_error "Nieprawidłowa opcja!"
            exit 1
            ;;
    esac
    
    # Set as default project
    gcloud config set project "$PROJECT_ID"
    print_status "Aktywny projekt: $PROJECT_ID"
}

# Enable YouTube Data API
enable_youtube_api() {
    print_info "Włączam YouTube Data API v3..."
    
    gcloud services enable youtube.googleapis.com
    print_status "YouTube Data API v3 włączone!"
    
    # Wait a moment for API to be fully enabled
    sleep 2
}

# Create OAuth 2.0 credentials
create_oauth_credentials() {
    print_info "Tworzę OAuth 2.0 credentials..."
    
    # Check if OAuth consent screen is configured
    print_info "Sprawdzam OAuth consent screen..."
    
    # Try to get consent screen info
    if ! gcloud alpha iap oauth-brands list > /dev/null 2>&1; then
        print_warning "OAuth consent screen może nie być skonfigurowany"
        echo ""
        echo "WAŻNE: Musisz skonfigurować OAuth consent screen w Google Cloud Console:"
        echo "1. Idź do: https://console.cloud.google.com/apis/credentials/consent"
        echo "2. Wybierz 'External' user type"
        echo "3. Wypełnij wymagane pola:"
        echo "   - App name: Medusa YouTube Test"
        echo "   - User support email: twój email"
        echo "   - Developer contact: twój email"
        echo "4. Dodaj scope: ../auth/youtube.upload"
        echo "5. Dodaj test users (twój email)"
        echo ""
        read -p "Naciśnij Enter gdy skonfigurujesz OAuth consent screen..."
    fi
    
    # Create OAuth 2.0 client
    CLIENT_NAME="medusa-youtube-client"
    
    print_info "Tworzę OAuth 2.0 client..."
    
    # Create the OAuth client
    gcloud alpha iap oauth-clients create \
        --display_name="$CLIENT_NAME" \
        --brand="projects/$PROJECT_ID/brands/$(gcloud alpha iap oauth-brands list --format='value(name)' | head -n1 | cut -d'/' -f4)" 2>/dev/null || {
        
        print_warning "Nie udało się utworzyć przez gcloud, używam alternatywnej metody..."
        
        # Alternative: create through API
        echo "Tworzę credentials przez Google Cloud Console..."
        echo ""
        echo "Otwórz w przeglądarce:"
        echo "https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID"
        echo ""
        echo "1. Kliknij 'Create Credentials' > 'OAuth 2.0 Client IDs'"
        echo "2. Wybierz 'Desktop application'"
        echo "3. Nazwa: 'Medusa YouTube Client'"
        echo "4. Kliknij 'Create'"
        echo "5. Pobierz plik JSON"
        echo ""
        read -p "Naciśnij Enter gdy pobierzesz plik JSON..."
        
        # Ask for the downloaded file
        echo "Opcje dla pliku credentials:"
        echo "1. Plik jest w ~/Downloads/"
        echo "2. Podaj ścieżkę do pliku"
        read -p "Wybierz opcję (1/2): " file_option
        
        case $file_option in
            1)
                CRED_FILE=$(ls ~/Downloads/client_secret_*.json 2>/dev/null | head -n1)
                if [[ -f "$CRED_FILE" ]]; then
                    cp "$CRED_FILE" ./client_secrets.json
                    print_status "Plik credentials skopiowany!"
                else
                    print_error "Nie znaleziono pliku w ~/Downloads/"
                    exit 1
                fi
                ;;
            2)
                read -p "Podaj pełną ścieżkę do pliku: " CRED_PATH
                if [[ -f "$CRED_PATH" ]]; then
                    cp "$CRED_PATH" ./client_secrets.json
                    print_status "Plik credentials skopiowany!"
                else
                    print_error "Plik nie istnieje: $CRED_PATH"
                    exit 1
                fi
                ;;
        esac
    }
}

# Verify setup
verify_setup() {
    print_info "Weryfikuję setup..."
    
    if [[ -f "client_secrets.json" ]]; then
        print_status "Plik client_secrets.json istnieje"
        
        # Validate JSON format
        if python3 -c "import json; json.load(open('client_secrets.json'))" 2>/dev/null; then
            print_status "Plik JSON jest prawidłowy"
        else
            print_error "Plik JSON jest nieprawidłowy!"
            exit 1
        fi
        
        # Show client info
        CLIENT_ID=$(python3 -c "import json; data=json.load(open('client_secrets.json')); print(data.get('installed', data.get('web', {})).get('client_id', 'N/A'))")
        print_status "Client ID: ${CLIENT_ID:0:20}..."
        
    else
        print_error "Brak pliku client_secrets.json!"
        exit 1
    fi
    
    # Test our implementation
    print_info "Testuję implementację Medusa..."
    python3 -c "
import sys
sys.path.insert(0, 'src')
from medusa.uploaders.youtube import YouTubeUploader
from medusa.models import MediaMetadata, PlatformConfig

metadata = MediaMetadata(
    title='Test Video',
    description='Test description', 
    tags=['test'],
    privacy='private'
)

config = PlatformConfig(
    platform_name='youtube',
    credentials={'client_secrets_file': 'client_secrets.json'}
)

uploader = YouTubeUploader(config=config)
uploader._validate_metadata(metadata)
print('✅ Medusa implementation works!')
" || {
        print_error "Problem z implementacją Medusa!"
        exit 1
    }
}

# Main execution
main() {
    echo "Ten skrypt pomoże skonfigurować YouTube API dla projektu Medusa"
    echo ""
    
    check_gcloud
    authenticate_gcloud
    setup_project
    enable_youtube_api
    create_oauth_credentials
    verify_setup
    
    echo ""
    echo "🎉 Setup zakończony pomyślnie!"
    echo ""
    echo "Następne kroki:"
    echo "1. Przetestuj authentication:"
    echo "   python test_youtube_simple.py"
    echo ""
    echo "2. Uruchom pełne testy:"
    echo "   python -m pytest tests/integration/test_youtube_real_api.py -v"
    echo ""
    echo "3. Sprawdź quota usage:"
    echo "   https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas?project=$PROJECT_ID"
    echo ""
    print_status "Gotowe do testowania YouTube API!"
}

# Run main function
main "$@" 