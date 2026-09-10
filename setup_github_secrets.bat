@echo off
echo ================================================================
echo  AUTO MAKE MONEY - Setup GitHub Repo Secrets
echo  Repo: kowinvestor0/automation
echo ================================================================
echo.
REM Check if gh CLI is authenticated
gh auth status >nul 2>&1
if errorlevel 1 (
    echo [!] GitHub CLI chua dang nhap. Dang mo trinh duyet de dang nhap...
    gh auth login -p https -w
    if errorlevel 1 (
        echo [X] Khong the dang nhap GitHub CLI. Vui long thu lai.
        pause
        exit /b 1
    )
)
echo [1/3] Dang them PLANLY_TOKEN...
echo CoM0+pEPTicn960fkPZNPxdvi5IHDqwX+SceJKgfwGw| gh secret set PLANLY_TOKEN -R kowinvestor0/automation
echo [2/3] Dang them PLANLY_TEAM_ID...
echo c22dbf1e-b00e-42be-b254-c8549182abf5| gh secret set PLANLY_TEAM_ID -R kowinvestor0/automation
echo [3/3] Dang them PEXELS_API_KEY...
echo 5GXaomChWu5mXmxU6lSC9jE06i5BZ0FXYhqP9tGMInrbyWKGifnogN1e| gh secret set PEXELS_API_KEY -R kowinvestor0/automation
echo.
echo ================================================================
echo  [OK] Da thiet lap xong 3 secrets cho GitHub Actions Cloud!
echo ================================================================
pause
