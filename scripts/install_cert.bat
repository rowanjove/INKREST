@echo off
title NovelAgent Developer Certificate Installer
echo =========================================================
echo       NovelAgent Developer Certificate Installer
echo =========================================================
echo.

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running as administrator.
) else (
    echo [ERROR] This script must be run as Administrator.
    echo Please right-click this file and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

echo Generating self-signed developer certificate...
powershell -Command "New-SelfSignedCertificate -Type CodeSigning -Subject 'CN=NovelAgent Test Developer, O=NovelAgent, C=CN' -KeyUsage DigitalSignature -FriendlyName 'NovelAgent Test CodeSign' -CertStoreLocation 'Cert:\CurrentUser\My' -NotAfter (Get-Date).AddYears(5)"

if %errorLevel% == 0 (
    echo [OK] Certificate generated successfully in CurrentUser\My.
) else (
    echo [ERROR] Failed to generate certificate.
    pause
    exit /b %errorLevel%
)

echo Exporting certificate to trust...
powershell -Command "$cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -like '*CN=NovelAgent Test Developer*' } | Select-Object -First 1; Export-Certificate -Cert $cert -FilePath '%temp%\novelagent_test.cer'"

echo Installing certificate into Trusted Root Certification Authorities...
certutil -addstore -f "Root" "%temp%\novelagent_test.cer"

if %errorLevel% == 0 (
    echo [OK] Certificate installed into Trusted Root. Windows will now trust this publisher.
    del "%temp%\novelagent_test.cer"
) else (
    echo [ERROR] Failed to import certificate into Trusted Root.
    pause
    exit /b %errorLevel%
)

echo.
echo =========================================================
echo   Setup completed! You can now compile and sign the app.
echo =========================================================
echo.
pause
