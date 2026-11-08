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
START_PARAM = "r2005545171"

# ─── TMA TOKEN ────────────────────────────────────────────────────────────────

async def join_channel(session_string: str, url: str):
    username = url.rstrip("/").split("/")[-1]
    client = Client(
        name="myage_tmp",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
    )
    async with client:
        try:
            await client.join_chat(username)
            print(f"     joined {username}")
        except Exception as e:
            print(f"     skip {username}: {e}")

async def get_tma_token(session_string: str) -> str:
    client = Client(
        name="myage_tmp",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
    )
    async with client:
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

def do_onboarding(token):
    print("  [ONBOARDING] Welcome + claim AGE awal...")
    try:
        r = api(token, "/welcome", {})
        welcome = r.get("welcome", {})
        pts = r.get("points", 0)
        years = welcome.get("years", "?")
        older = welcome.get("olderThan", "?")
        print(f"  ✓ welcome | years={years} | olderThan={older}% | points={pts}")
    except Exception as e:
        print(f"  ! welcome skip: {e}")
    time.sleep(1)

    try:
        r = api(token, "/story", {"to": "story"})
        sid = r.get("id", "?")
        print(f"  ✓ story[story] id={sid}")
    except Exception as e:
        print(f"  ! story[story] skip: {e}")
    time.sleep(1)

async def do_tasks(token, session_string):
    do_onboarding(token)
    print("  [TASK] Ambil daftar task...")
    data = api(token, "/tasks")  # GET
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

        kind = t.get("kind", "")
        pressesRequired = t.get("pressesRequired", 1)
        presses = t.get("presses", 0)
        remaining = pressesRequired - presses

        if kind == "channel":
            print(f"  → [{title}] join + claim...")
            url = t.get("url", "")
            if url:
                await join_channel(session_string, url)
                time.sleep(1)
            r = api(token, "/tasks", {"taskId": tid})
            msg = r.get("message", "")
            paid = r.get("paid", 0)
            print(f"     paid={paid} | {msg}")
            time.sleep(1.5)

        else:
            # custom, x_follow, dll — tekan sampai paid > 0
            print(f"  → [{title}] press x{remaining}...")
            for i in range(remaining):
                r = api(token, "/tasks", {"taskId": tid})
                msg = r.get("message", "")
                paid = r.get("paid", 0)
                print(f"     press {i+1}/{remaining} | paid={paid} | {msg}")
                if paid > 0:
                    break
                time.sleep(2)

    time.sleep(1)
    try:
        r = api(token, "/story", {"to": "chat"})
        reward = r.get("reward", 0)
        pts = r.get("points", 0)
        print(f"  ✓ story[chat] reward={reward} | points={pts}")
    except Exception as e:
        print(f"  ! story[chat] skip: {e}")
    # story[x] di-skip

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
    round_num = 0
    while True:
        r = api(token, "/spin", {})
        next_ts = r.get("next")
        prize = r.get("prize", 0)
        kind = r.get("kind", "?")
        pts = r.get("points", 0)
        msg = r.get("message", "")
        round_num += 1

        if next_ts:
            wait = max(0, (next_ts - int(time.time() * 1000)) / 1000)
            print(f"  ✓ spin #{round_num} | {prize} {kind} | points={pts}")
            print(f"     spin habis, next in {wait:.0f}s")
            break

        if msg and prize == 0:
            print(f"  ! spin stop: {msg}")
            break

        print(f"  ✓ spin #{round_num} | {prize} {kind} | points={pts}")
        time.sleep(1.5)

def do_mystery(token):
    print("  [MYSTERY] Spin mystery...")
    round_num = 0
    while True:
        r = api(token, "/mystery", {})
        amount = r.get("amount", 0)
        kind = r.get("kind", "?")
        left = r.get("left", 0)
        pts = r.get("points", 0)
        msg = r.get("message", "")
        round_num += 1

        print(f"  ✓ mystery #{round_num} | {amount} {kind} | left={left} | points={pts}")

        if left <= 0 or msg:
            if msg:
                print(f"     stop: {msg}")
            break
        time.sleep(1.5)

# ─── MENU ────────────────────────────────────────────────────────────────────

def menu_account(total: int):
    print("\n=== Pilih Akun ===")
    print("  1. 1 akun")
    print("  2. semua")
    print("  3. dari akun ke-X sampai akhir")
    val = input("Pilih: ").strip()

    if val == "1":
        n = int(input(f"Nomor akun (1-{total}): ").strip())
        return (n-1, n)
    elif val == "2":
        return (0, total)
    elif val == "3":
        n = int(input("Mulai dari akun ke-: ").strip())
        return (n-1, total)
    else:
        print("Pilihan tidak valid")
        return None

def menu_mode():
    print("\n=== Pilih Mode ===")
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

# ─── MAIN ────────────────────────────────────────────────────────────────────

def load_sessions():
    path = Path("sessions.txt")
    if not path.exists():
        print("sessions.txt tidak ditemukan!")
        sys.exit(1)
    return [l.strip() for l in path.read_text().splitlines() if l.strip()]

async def run_account(session_string: str, idx: int, action_fn):
    print(f"\n{'='*40}")
    print(f"Akun #{idx}")
    token = await get_tma_token(session_string)
    do_session(token)
    if asyncio.iscoroutinefunction(action_fn):
        await action_fn(token, session_string)
    else:
        action_fn(token)

async def main():
    sessions = load_sessions()

    while True:
        result = menu_account(len(sessions))
        if result is None:
            continue
        start, end = result

        mode = menu_mode()
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

        for i, ss in enumerate(sessions[start:end], start=start+1):
            try:
                await run_account(ss, i, action)
            except Exception as e:
                print(f"  ✗ Error [akun #{i}]: {e}")
            time.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
