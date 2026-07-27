# Wi‑Fi Texnik

Windows üçün təhlükəsiz Wi‑Fi, lokal şəbəkə, internet və ilkin GPON
diaqnostika tətbiqi.

## İmkanlar

- Yaxın Wi‑Fi access point-lərini SSID, BSSID, siqnal, kanal, radio və
  təhlükəsizlik növü ilə göstərir.
- Qoşulu Wi‑Fi, default gateway, `1.1.1.1`, TCP 443 və DNS testləri aparır.
- Paket itkisini və orta ping-i hesablayır.
- Problemi lokal Wi‑Fi/LAN, gateway, WAN/provayder və ya DNS istiqamətində
  təsnif edir.
- ONT panelindən götürülmüş optik RX və LOS məlumatına ilkin qiymət verir.
- Texniki nəticəni UTF‑8 mətn hesabatı kimi saxlayır.
- Default gateway-in modem panelini bir kliklə açır.

Tətbiq Wi‑Fi şifrəsi sınamır, yaxın şəbəkələrə qoşulmağa cəhd etmir və
Windows-da saxlanmış şəbəkə profillərini silmir.

## Birbaşa işə salmaq

1. Windows-a Python 3.11 və ya daha yeni versiya quraşdır.
2. Quraşdırmada **Add Python to PATH** seçimini aktiv et.
3. `run_windows.bat` faylını aç.

Tətbiqin işləməsi üçün əlavə Python paketi lazım deyil.

## EXE hazırlamaq

`build_windows.bat` faylını aç. Skript ayrıca `.venv` yaradacaq, PyInstaller
quraşdıracaq və nəticəni burada verəcək:

```text
dist\WifiTexnik.exe
```

Build prosesi üçün internet bağlantısı lazımdır. Hazır EXE işləyərkən Python
tələb etmir.

GitHub-dakı **Build Windows EXE** workflow-u da hər dəyişiklikdə avtomatik
`WifiTexnik-Windows` adlı artifact yaradır. Actions bölməsindən uğurlu build-i
açıb artifact-i endirmək mümkündür.

## Test

Repo qovluğunda:

```powershell
py -3 -m unittest discover -s tests -v
```

## GPON barədə

Wi‑Fi siqnalından fiberin optik RX gücünü hesablamaq mümkün deyil. RX/TX və
LOS məlumatı ONT/modem panelindən və ya provayderin OLT/ACS sistemindən
alınmalıdır. Fiziki qırılmanın yerini dəqiq müəyyənləşdirmək üçün OTDR
lazımdır.

Tətbiqdəki RX hədləri ümumi orientirdir; provayder və ONT modelinə görə
dəyişə bilər.

## Məxfilik

Bütün testlər lokal kompüterdə aparılır. Tətbiq hesabatı və şəbəkə
məlumatlarını heç bir serverə göndərmir.
