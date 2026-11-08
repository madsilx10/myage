import asyncio
import requests
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs
from pyrogram import Client
from pyrogram.raw import functions
from config import API_ID, API_HASH

BASE_URL = "https://myageapp.xyz/api"
BOT_USERNAME = "MyAgeApp"
START_PARAM = "r5663015431"

# ─── TMA TOKEN ────────────────────────────────────────────────────────────────

async def get_tma_token(client: Client) -> str:
    peer = await client.resolve_peer(BOT_USERNAME)
    web_view = await client.invoke(
        functions.messages.RequestWebView(
            peer=peer,
            bot=peer,
            platform="android",
            url=f"https://myageapp.xyz/?tgWebAppStartParam={START_PARAM}",
            start_param=START_PARAM,
        )
    )
    fragment = web_view.url.split("#")[1]
    params = parse_qs(fragment)
    tg_data = params.get("tgWebAppData", [""])[0]
    return f"tma {tg_data}"

# ─── API ──────────────────────────────────────────────────────────────────────

def api(token: str, path: str, body: dict = None):
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "Origin": "https://myageapp.xyz",
        "Referer": f"https://myageapp.xyz/?tgWebAppStartParam={START_PARAM}",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    }
    url = BASE_URL + path
    if body is None:
        r = requests.get(url, headers=headers, timeout=30)
    else:
        r = requests.post(url, headers=headers, json=body, timeout=30)
    return r.json()

# ─── ACTIONS ─────────────────────────────────────────────────────────────────

def do_session(token):
    data = api(token, "/session", {})
    name = data.get("user", {}).get("name", "?")
    pts = data.get("user", {}).get("points", 0)
    print(f"  → Session OK | name={name} | points={pts}")
    return data

def do_tasks(token):
    print("  [TASK] Ambil daftar task...")
    data = api(token, "/tasks", {})
    tasks = data.get("tasks", [])
    print(f"  → {len(tasks)} task ditemukan")

    for t in tasks:
        tid = t["id"]
        title = t["title"]
        done = t.get("done", False)
        step = t.get("step", 0)

        if done:
            print(f"  ✓ [{title}] sudah selesai")
            continue

        if step == 1:
            print(f"  → [{title}] step 1, claim...")
            r = api(token, "/tasks", {"taskId": tid})
            msg = r.get("message", "")
            paid = r.get("paid", 0)
            print(f"     paid={paid} | {msg}")
            time.sleep(1.5)

        elif step == 2:
            pressesRequired = t.get("pressesRequired", 4)
            presses = t.get("presses", 0)
            remaining = pressesRequired - presses
            print(f"  → [{title}] step 2, sisa press={remaining}")
            for i in range(remaining):
                r = api(token, "/tasks", {"taskId": tid})
                msg = r.get("message", "")
                paid = r.get("paid", 0)
                print(f"     press {i+1}/{remaining} | paid={paid} | {msg}")
                if paid > 0:
                    break
                time.sleep(2)

        else:
            print(f"  ? [{title}] step={step}, skip")

def do_achievements(token):
    print("  [ACHIEVEMENT] Ambil list...")
    data = api(token, "/achievements")
    items = data.get("list", [])
    claimable = [a for a in items if a.get("done") and not a.get("claimed")]
    print(f"  → {len(claimable)} achievement bisa diclaim")
    for a in claimable:
        key = a["key"]
        title = a["title"]
        r = api(token, "/achievements", {"key": key})
        reward = r.get("reward", 0)
        pts = r.get("points", 0)
        print(f"  ✓ [{title}] reward={reward} | points={pts}")
        time.sleep(1)

def do_vault(token):
    print("  [VAULT] Claim...")
    r = api(token, "/vault", {})
    amount = r.get("amount", 0)
    pts = r.get("points", 0)
    print(f"  ✓ vault amount={amount} | points={pts}")

def do_daily(token):
    print("  [DAILY] Claim...")
    r = api(token, "/daily", {})
    day = r.get("day", 0)
    reward = r.get("reward", 0)
    streak = r.get("streak", 0)
    pts = r.get("points", 0)
    print(f"  ✓ daily day={day} | reward={reward} | streak={streak} | points={pts}")

def do_spin(token):
    print("  [SPIN] Putar...")
    r = api(token, "/spin", {})
    prize = r.get("prize", 0)
    kind = r.get("kind", "?")
    pts = r.get("points", 0)
    next_ts = r.get("next")
    print(f"  ✓ spin prize={prize} {kind} | points={pts}")
    if next_ts:
        wait = max(0, (next_ts - int(time.time() * 1000)) / 1000)
        print(f"     next spin in {wait:.0f}s")

def do_mystery(token):
    print("  [MYSTERY] Spin mystery...")
    r = api(token, "/mystery", {})
    amount = r.get("amount", 0)
    kind = r.get("kind", "?")
    left = r.get("left", 0)
    print(f"  ✓ mystery amount={amount} {kind} | left={left}")

# ─── MENU ────────────────────────────────────────────────────────────────────

def menu_main():
    print("\n=== MyAge Bot ===")
    print("  1. task")
    print("  2. claim")
    print("  3. spin")
    print("  0. exit")
    return input("Pilih: ").strip()

def menu_claim():
    print("\n=== Claim ===")
    print("  1. vault + daily")
    print("  2. vault")
    print("  3. daily")
    print("  4. achievement")
    return input("Pilih: ").strip()

def menu_spin():
    print("\n=== Spin ===")
    print("  1. spin biasa")
    print("  2. mystery spin")
    return input("Pilih: ").strip()

def menu_account(sessions: list):
    print("\n=== Pilih Akun ===")
    print("  0. semua")
    for i, s in enumerate(sessions, 1):
        print(f"  {i}. {s}")
    n = len(sessions)
    val = input(f"Pilih (0-{n}) atau range (misal 2-5): ").strip()
    if "-" in val and not val.startswith("-"):
        a, b = val.split("-")
        return sessions[int(a)-1:int(b)]
    elif val == "0":
        return sessions
    else:
        return [sessions[int(val)-1]]

# ─── MAIN ────────────────────────────────────────────────────────────────────

def load_sessions():
    path = Path("sessions.txt")
    if not path.exists():
        print("sessions.txt tidak ditemukan!")
        sys.exit(1)
    return [l.strip() for l in path.read_text().splitlines() if l.strip()]

async def run_account(session_name: str, action_fn):
    print(f"\n{'='*40}")
    print(f"Akun: {session_name}")
    client = Client(session_name, api_id=API_ID, api_hash=API_HASH, workdir=".")
    async with client:
        token = await get_tma_token(client)
    do_session(token)
    action_fn(token)

async def main():
    sessions = load_sessions()

    while True:
        mode = menu_main()
        if mode == "0":
            break

        if mode == "1":
            action = do_tasks
        elif mode == "2":
            sub = menu_claim()
            if sub == "1":
                def action(t):
                    do_vault(t)
                    do_daily(t)
            elif sub == "2":
                action = do_vault
            elif sub == "3":
                action = do_daily
            elif sub == "4":
                action = do_achievements
            else:
                print("Pilihan tidak valid")
                continue
        elif mode == "3":
            sub = menu_spin()
            if sub == "1":
                action = do_spin
            elif sub == "2":
                action = do_mystery
            else:
                print("Pilihan tidak valid")
                continue
        else:
            print("Pilihan tidak valid")
            continue

        chosen = menu_account(sessions)
        for sname in chosen:
            try:
                await run_account(sname, action)
            except Exception as e:
                print(f"  ✗ Error [{sname}]: {e}")
            time.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
