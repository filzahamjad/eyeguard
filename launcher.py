#!/usr/bin/env python3
"""
EyeGuard Launcher
Automatically starts Django server and opens browser
"""

import multiprocessing
# MUST be called before any other code when frozen by PyInstaller so that
# child processes spawned by multiprocessing (e.g. via Twisted/Channels)
# are handled correctly and don't re-run this launcher.
multiprocessing.freeze_support()

import os
import sys
import time
import socket
import threading
import webbrowser
from pathlib import Path


def _get_project_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return str(Path(__file__).parent.absolute())


def _acquire_lock(retries=3):
    """
    Bind a local socket so only one instance can hold it.
    Returns the socket on success, or None if another instance is running.
    Retries a few times in case a just-killed previous instance is releasing.
    """
    for attempt in range(retries):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        try:
            s.bind(('127.0.0.1', 47200))
            s.listen(1)
            return s
        except OSError:
            s.close()
            if attempt < retries - 1:
                time.sleep(1)
    return None


def _wait_for_server(host='127.0.0.1', port=8000, timeout=45, ready_event=None):
    """Poll until the Django server is accepting connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        # Abort early if the caller signals failure.
        if ready_event and ready_event.is_set():
            return False
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def _open_browser_when_ready(server_failed_event):
    """Run in a background thread: wait for server then open browser once."""
    # If Django reported a failure before the server came up, abort.
    if server_failed_event.wait(timeout=0.1):
        return
    if _wait_for_server(ready_event=server_failed_event):
        try:
            webbrowser.open("http://localhost:8000/admin/")
        except Exception as exc:
            print(f"⚠  Browser open failed: {exc}")
            print("   Visit manually: http://localhost:8000/admin/")
    else:
        print("\n⚠  Server did not respond within 45 s.")
        print("   Check the error messages above.")
        print("   If the server started, visit: http://localhost:8000/admin/")


def main():
    lock = None
    try:
        # ── Single-instance guard ────────────────────────────────────────
        lock = _acquire_lock()
        if lock is None:
            # Another process holds the lock — but only open the browser if
            # Django is actually responding (the other process might have died
            # while leaving the lock socket open).
            if _wait_for_server(timeout=5):
                print("EyeGuard is already running.")
                print("Visit: http://localhost:8000/admin/")
            else:
                print("A previous instance appears to have crashed (port 47200 is held but Django is not responding).")
                print("Please kill any lingering EyeGuard processes and try again.")
                print("\nPress Enter to exit...")
                input()
            return True

        project_dir = _get_project_dir()

        print("=" * 60)
        print("EyeGuard Camera Management System")
        print("=" * 60)
        print(f"\nWorking directory: {project_dir}")

        # ── Configure Django before importing it ─────────────────────────
        if project_dir not in sys.path:
            sys.path.insert(0, project_dir)
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyeguard.settings')

        # When frozen, Daphne/Twisted deadlocks during django.setup() due to
        # incompatibilities with PyInstaller's frozen environment.
        # Remove it from INSTALLED_APPS so Django uses its built-in WSGI server.
        if getattr(sys, 'frozen', False):
            import django.conf as _conf
            _s = _conf.settings
            # Force settings to load then patch the list
            _ = _s.INSTALLED_APPS
            _conf.settings.INSTALLED_APPS = [
                app for app in _s.INSTALLED_APPS
                if app not in ('daphne', 'channels', 'channels_redis')
            ]
            # Also switch to WSGI application
            _conf.settings.ASGI_APPLICATION = None

        # ── Open browser from a background thread once port 8000 is up ───
        # Event is set if Django fails, so the browser thread aborts early.
        server_failed = threading.Event()

        # ── Run migrations and create default admin on first launch ──────
        try:
            import django
            django.setup()
            from django.core.management import call_command as _cmd
            # Apply any pending migrations (creates tables on first run)
            _cmd('migrate', '--run-syncdb', verbosity=0)
            # Create default superuser if no users exist
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if not User.objects.filter(is_superuser=True).exists():
                User.objects.create_superuser(
                    username='admin',
                    password='admin1234',
                    email=''
                )
                print("=" * 60)
                print("  Default admin account created:")
                print("    Username : admin")
                print("    Password : admin1234")
                print("  Change your password after first login!")
                print("=" * 60)
                print()
        except Exception as _e:
            print(f"⚠  Setup warning: {_e}")
            import traceback; traceback.print_exc()
        browser_thread = threading.Thread(
            target=_open_browser_when_ready, args=(server_failed,), daemon=True
        )
        browser_thread.start()

        # Log file so errors are visible even when console output is hidden.
        log_path = os.path.join(os.path.expanduser('~'), 'EyeGuard_startup.log')
        print(f"Starting Django server on http://127.0.0.1:8000 ...")
        print(f"(browser will open automatically once ready)\n")
        sys.stdout.flush()

        # ── Run Django in the MAIN thread ─────────────────────────────────
        # Daphne/Twisted's reactor must run in the main thread.
        django_exit_code = 0
        try:
            import django
            django.setup()
            from django.core.management import call_command
            call_command('runserver', '127.0.0.1:8000', '--noreload')
        except SystemExit as e:
            django_exit_code = e.code if e.code is not None else 0
            if django_exit_code not in (0, None):
                server_failed.set()
                print(f"\n❌ Django exited with code {django_exit_code}")
                print(f"   See log: {log_path}")
                print("\nPress Enter to exit...")
                input()
        except Exception as exc:
            server_failed.set()
            print(f"\n❌ Django error: {exc}")
            import traceback
            traceback.print_exc()
            try:
                with open(log_path, 'a') as _log:
                    import traceback as _tb
                    _log.write(f'EXCEPTION: {exc}\n')
                    _tb.print_exc(file=_log)
            except Exception:
                pass
            print(f"   See log: {log_path}")
            print("\nPress Enter to exit...")
            input()

        return True

    except KeyboardInterrupt:
        print("\n\nStopping server...")
        print("Server stopped.")
        return True
    except Exception as exc:
        print(f"\n❌ Error: {exc}")
        import traceback
        traceback.print_exc()
        print("\nPress Enter to exit...")
        input()
        return False
    finally:
        if lock is not None:
            try:
                lock.close()
            except Exception:
                pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

