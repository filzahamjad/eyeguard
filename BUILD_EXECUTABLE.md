# 🎯 EyeGuard Standalone Executable Guide

## Quick Start (For Users)

### On Windows without Python installed:

1. **Download files from another Windows machine that has Python:**
   - Someone with Python runs: `python build_exe.py`
   - This creates `EyeGuard.exe` in the `dist/` folder
2. **Copy the .exe to your computer**
   - Double-click `EyeGuard.exe`
   - Browser automatically opens to `http://localhost:8000/admin/`
   - ✅ Done! No Python installation needed

---

## For Developers (Building the Executable)

### Method 1: PyInstaller (Easiest)

#### Step 1: Install PyInstaller

```bash
pip install pyinstaller
```

#### Step 2: Build the executable

```bash
python build_exe.py
```

This creates:

- `dist/EyeGuard.exe` - Single standalone file (~2-3 GB)
- Ready to run on any Windows machine without Python

#### Step 3: Distribute

```bash
# Copy to USB or send to other devices
copy dist\EyeGuard.exe D:\USB_Drive\
```

---

### Method 2: Portable Package (Smaller, Recommended)

This creates a folder that's easier to distribute and modify.

#### Step 1: Create portable folder structure

```bash
mkdir EyeGuard-Portable
cd EyeGuard-Portable

# Copy project files
xcopy /E /I ..\eyeguard eyeguard
xcopy /E /I ..\templates templates
xcopy /E /I ..\media media
xcopy /E /I ..\staticfiles staticfiles
copy ..\manage.py .
copy ..\launcher.py .
copy ..\run_eyeguard.bat .
copy ..\requirements.txt .
copy ..\db.sqlite3 .
```

#### Step 2: Create a venv inside the folder

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
deactivate
```

#### Step 3: Create a launcher batch file

Users just double-click this:

```batch
@echo off
call venv\Scripts\activate.bat
python launcher.py
```

#### Step 4: Distribute the entire folder

- Size: ~1-2 GB (much smaller than PyInstaller .exe)
- Users extract and run the batch file
- Can be run from USB drive

---

## How It Works

### launcher.py

1. Starts Django development server
2. Waits for server to be ready (3 seconds)
3. Automatically opens browser to `http://localhost:8000/admin/`
4. Keeps running until user closes it (Ctrl+C)

### run_eyeguard.bat

1. Checks if Python is installed
2. Runs `launcher.py`
3. Handles errors gracefully

---

## Troubleshooting

### "Python is not installed"

- Download Python from https://python.org
- **Important:** Check "Add Python to PATH" during installation
- Restart computer after installation

### "Server failed to start"

- Check if port 8000 is already in use
- Open command prompt and run: `netstat -ano | findstr :8000`
- Kill the process or use a different port

### "Browser didn't open"

- Manually open: `http://localhost:8000/admin/`
- Login with your credentials

### "Database error"

- Ensure `db.sqlite3` is in the project root
- Or run migrations: `python manage.py migrate`

---

## Security Considerations

⚠️ **Important for production:**

- This uses Django's development server (not production-safe)
- For deployment, use Gunicorn + Nginx
- Change SECRET_KEY in settings.py
- Set DEBUG=False
- Use HTTPS in production

For now, this is perfect for **local/internal use** on Windows machines!

---

## Next Steps

1. **Try it locally:**

   ```bash
   python launcher.py
   ```

2. **Build executable:**

   ```bash
   python build_exe.py
   ```

3. **Test on another machine:**
   - Copy `dist/EyeGuard.exe` to another Windows computer
   - Double-click it (should just work!)

---

## Support

Questions? Check:

- Django docs: https://docs.djangoproject.com/
- PyInstaller docs: https://pyinstaller.org/
- This project's README: README.md
