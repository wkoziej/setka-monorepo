# ⚡ Szybki Setup YouTube API przez Command Line

## 🚀 **Jednokomendowy setup:**

```bash
# Sprawdź aktualny status
./check_gcloud_status.sh

# Pełny automatyczny setup
./setup_youtube_api.sh
```

## 📋 **Co robi automatyczny setup:**

### **Krok 1: Instalacja Google Cloud CLI**
```bash
# Automatycznie instaluje przez snap
sudo snap install google-cloud-cli --classic

# Lub instrukcje dla manualnej instalacji
```

### **Krok 2: Autentykacja**
```bash
# Otwiera browser do logowania Google
gcloud auth login
```

### **Krok 3: Projekt**
```bash
# Lista istniejących projektów
gcloud projects list

# Lub tworzenie nowego
gcloud projects create medusa-youtube-test --name="Medusa YouTube Test"
gcloud config set project medusa-youtube-test
```

### **Krok 4: Włączenie API**
```bash
# Włącza YouTube Data API v3
gcloud services enable youtube.googleapis.com
```

### **Krok 5: OAuth Credentials**
- Automatyczne tworzenie (jeśli możliwe)
- Lub instrukcje do Google Cloud Console
- Automatyczne kopiowanie pliku `client_secrets.json`

### **Krok 6: Weryfikacja**
```bash
# Test implementacji Medusa
python -c "from src.medusa.uploaders.youtube import YouTubeUploader; print('✅ OK')"
```

## 🛠️ **Manualne komendy (jeśli potrzebujesz):**

### **Instalacja gcloud:**
```bash
# Ubuntu/Debian przez snap
sudo snap install google-cloud-cli --classic

# Ubuntu/Debian przez apt
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
echo "deb https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update && sudo apt-get install google-cloud-cli
```

### **Setup projektu:**
```bash
# Logowanie
gcloud auth login

# Lista projektów
gcloud projects list

# Nowy projekt
gcloud projects create my-youtube-project --name="My YouTube Project"

# Aktywuj projekt
gcloud config set project my-youtube-project

# Włącz API
gcloud services enable youtube.googleapis.com
```

### **Sprawdzenie statusu:**
```bash
# Aktywne konto
gcloud auth list

# Aktywny projekt
gcloud config get-value project

# Włączone APIs
gcloud services list --enabled --filter="youtube"

# Quota usage
gcloud logging read "resource.type=api" --limit=10
```

## 🔍 **Diagnostyka:**

### **Sprawdź instalację:**
```bash
which gcloud
gcloud --version
gcloud components list
```

### **Sprawdź autentykację:**
```bash
gcloud auth list
gcloud auth application-default print-access-token
```

### **Sprawdź projekt i API:**
```bash
gcloud config list
gcloud services list --enabled
gcloud projects get-iam-policy $(gcloud config get-value project)
```

### **Sprawdź credentials:**
```bash
ls -la *.json
python3 -c "import json; print(json.load(open('client_secrets.json')))" 2>/dev/null || echo "Brak lub błędny plik"
```

## 🎯 **Szybkie testy:**

### **Test 1: Podstawowa implementacja**
```bash
python3 -c "
import sys; sys.path.insert(0, 'src')
from medusa.uploaders.youtube import YouTubeUploader
from medusa.models import MediaMetadata, PlatformConfig
print('✅ Import działa')
"
```

### **Test 2: Validation**
```bash
python3 -c "
import sys; sys.path.insert(0, 'src')
from medusa.uploaders.youtube import YouTubeUploader
from medusa.models import MediaMetadata, PlatformConfig

metadata = MediaMetadata(title='Test', description='Test', privacy='private')
config = PlatformConfig(platform_name='youtube')
uploader = YouTubeUploader(config=config)
uploader._validate_metadata(metadata)
print('✅ Validation działa')
"
```

### **Test 3: Authentication (wymaga credentials)**
```bash
python youtube_manual_example.py
```

### **Test 4: Pełne testy**
```bash
python -m pytest tests/test_uploaders/test_youtube_uploader.py -v
python -m pytest tests/integration/test_youtube_real_api.py -v
```

## 🚨 **Troubleshooting:**

### **Problem: "gcloud command not found"**
```bash
# Sprawdź PATH
echo $PATH | grep -o google-cloud-sdk

# Reinstall
sudo snap remove google-cloud-cli
sudo snap install google-cloud-cli --classic

# Restart shell
exec $SHELL
```

### **Problem: "Authentication failed"**
```bash
# Reset auth
gcloud auth revoke --all
gcloud auth login

# Check scopes
gcloud auth list --filter=status:ACTIVE --format="table(account,status)"
```

### **Problem: "Project not found"**
```bash
# Lista wszystkich projektów
gcloud projects list --format="table(projectId,name,lifecycleState)"

# Sprawdź uprawnienia
gcloud projects get-iam-policy PROJECT_ID
```

### **Problem: "API not enabled"**
```bash
# Sprawdź dostępne APIs
gcloud services list --available --filter="youtube"

# Włącz ponownie
gcloud services enable youtube.googleapis.com

# Sprawdź status
gcloud services list --enabled --filter="youtube"
```

### **Problem: "OAuth consent screen"**
```bash
# Musi być skonfigurowany przez web console
echo "Idź do: https://console.cloud.google.com/apis/credentials/consent"
```

## 📊 **Monitoring i quota:**

### **Sprawdź quota:**
```bash
# Web console
echo "https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas"

# CLI (podstawowe info)
gcloud logging read "resource.type=api AND resource.labels.service=youtube.googleapis.com" --limit=10
```

### **Monitor API calls:**
```bash
# Ostatnie API calls
gcloud logging read "resource.type=api" --limit=10 --format="table(timestamp,resource.labels.service,severity)"
```

---

## 🎉 **Po setup'ie:**

```bash
# Status check
./check_gcloud_status.sh

# Pierwszy test
python youtube_manual_example.py

# Pełne testy
python -m pytest tests/integration/test_youtube_real_api.py -v
```

**Gotowe do testowania YouTube API! 🚀**
