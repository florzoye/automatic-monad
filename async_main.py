import os
import sqlite3
import datetime
import asyncio
from collections import defaultdict
from typing import List, Dict
import csv
from eth_account import Account
from colorama import Fore, Style, init
import logging

from async_utils.async_balance_native import AsyncTokenBalanceChecker
from sync_utils.create_evm_wallet import generate
from async_utils.async_buy_monad import AsyncGasZipBuyMonad

from async_tasks.async_monorail.swapper import MONORAIL
from async_tasks.async_nft.async_Lil_Chogstars import LilChogstarsMinter
from async_tasks.async_magma.async_magma_staiking import MAGMA
from async_tasks.async_pandaria.async_pandaria_wrap import DepositContract
from async_tasks.async_kinza.async_kinza_dak_supply import Kinza
from async_tasks.async_main_site.async_DAK.buy_dak_with_main_site import BUY_DAK
from async_tasks.async_main_site.async_CHOG.buy_chog_with_main_site import BUY_CHOG
from async_tasks.async_main_site.async_YAKI.buy_yaki_with_main_site import BUY_YAKI

from config import wallets, arb_rpc, monad_rpc, PROXY_FILE, DB_NAME

init(autoreset=True)
logging.basicConfig(filename='wallet_log.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def print_banner():
    print(Fore.CYAN + """
    ███╗   ███╗ ██████╗ ███╗   ██╗ █████╗ ██████╗                                                           
    ████╗ ████║██╔═══██╗████╗  ██║██╔══██╗██╔══██╗                                                          
    ██╔████╔██║██║   ██║██╔██╗ ██║███████║██║  ██║                                                          
    ██║╚██╔╝██║██║   ██║██║╚██╗██║██╔══██║██║  ██║                                                          
    ██║ ╚═╝ ██║╚██████╔╝██║ ╚████║██║  ██║██████╔╝                                                          
    ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚═════╝                                                           
                                         by @xflorzoye                                                                       
                                                                                                        
    """ + Style.RESET_ALL)
    print(Fore.YELLOW + f"Bot start: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" + Style.RESET_ALL)

async def load_wallets_from_csv(csv_path: str) -> List[Dict]:
    results = []
    if not os.path.exists(csv_path):
        print(f"File {csv_path} not found!")
        return results
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter='|')
        for row in reader:
            if not row.get('address'):
                pk = row.get('private_key')
                if pk:
                    acct = Account.from_key(pk)
                    row['address'] = acct.address
            results.append(dict(row))
    return results

async def load_wallets_from_list(list_data: List[Dict]) -> List[Dict]:
    res = []
    for item in list_data:
        pk = item.get('private_key') or item.get('key')
        proxy = item.get('proxy')
        if pk:
            acct = Account.from_key(pk)
            address = acct.address
            d = {
                'address': address,
                'private_key': pk,
            }
            if 'proxy' in item:
                d['proxy'] = item['proxy']
            res.append(d)
    return res

async def load_wallets_from_private_keys():
    private_keys_file = "private_key.txt"
    if not os.path.exists(private_keys_file):
        print(Fore.RED + f"❌ File {private_keys_file} not found!" + Style.RESET_ALL)
        return
    with open(private_keys_file, "r", encoding="utf-8") as f:
        private_keys = [line.strip() for line in f.readlines() if line.strip()]
    if not private_keys:
        print(Fore.YELLOW + "⚠️ File is empty. Add private keys to file" + Style.RESET_ALL)
        return
    wallets_list = []
    for private_key in private_keys:
        try:
            acct = Account.from_key(private_key)
            wallet_data = {
                'address': acct.address,
                'private_key': private_key
            }
            wallets_list.append(wallet_data)
        except Exception as e:
            print(Fore.RED + f"❌ Error: {private_key[:10]}... -> {e}" + Style.RESET_ALL)
    if wallets_list:
        await add_wallets_bulk(wallets_list)
        print(Fore.GREEN + f"✅ Successfully added {len(wallets_list)} wallets from {private_keys_file}!" + Style.RESET_ALL)

async def clear_all_wallets():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM wallets")
        conn.commit()
    print("ALL WALLETS CLEAR!")

async def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                address TEXT PRIMARY KEY,
                private_key TEXT,
                proxy TEXT,
                balance REAL,
                last_run_bean DATETIME,
                last_run_kinza DATETIME,
                last_run_magma DATETIME,
                last_run_chog DATETIME,
                last_run_dak DATETIME,
                last_run_yaki DATETIME,
                last_run_monorail DATETIME,
                last_run_nft DATETIME,
                last_run_pandaria DATETIME
            )
        """)
        conn.commit()

async def get_all_wallets() -> List[Dict]:
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute("SELECT * FROM wallets").fetchall()
        return [dict(r) for r in rows]

async def add_wallet_to_db(address: str, private_key: str, proxy: str = None) -> bool:
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT address FROM wallets WHERE address = ?", (address,))
        row = cur.fetchone()
        if row:
            return False
        if proxy is None:
            proxies = await load_proxies_from_file()
            if proxies:
                proxy = proxies.pop(0)
                print(f"A proxy has been issued {proxy} for {address}")
        cur.execute("INSERT INTO wallets (address, private_key, proxy) VALUES (?, ?, ?)", 
                    (address, private_key, proxy))
        conn.commit()
        return True

async def add_wallets_bulk(wallets_list: List[Dict]) -> None:
    added_count = 0
    skipped_count = 0
    for w in wallets_list:
        addr = w['address']
        pk = w['private_key']
        proxy = w.get("proxy")
        if await add_wallet_to_db(addr, pk, proxy):
            added_count += 1
        else:
            skipped_count += 1
    print(f"✅ Added: {added_count}, skipped (duplicates): {skipped_count}.")

async def update_balance_in_db(address: str, new_balance):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        new_balance_float = float(new_balance)
        cur.execute("UPDATE wallets SET balance = ? WHERE address = ?", (new_balance_float, address))
        conn.commit()

async def print_all_wallet_addresses():
    all_wallets = await get_all_wallets()
    if not all_wallets:
        print("🚨In database not wallets.")
        return
    print("\n📋 List all address wallets:")
    for idx, wallet in enumerate(all_wallets, start=1):
        address = wallet.get('address', 'N/A')
        print(f"{idx}. {address}")

async def update_last_run(script_name: str, address: str):
    now_str = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')
    col_name = f"last_run_{script_name}" 
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        query = f"UPDATE wallets SET {col_name} = ? WHERE address = ?"
        cur.execute(query, (now_str, address))
        conn.commit()

async def update_wallet_proxy(address: str, proxy: str):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT proxy FROM wallets WHERE address = ?", (address,))
        row = cur.fetchone()
        if row and row[0]: 
            return
        cur.execute("UPDATE wallets SET proxy = ? WHERE address = ?", (proxy, address))
        conn.commit()

async def load_proxies_from_file() -> List[str]:
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

async def assign_proxies_to_wallets():
    all_wallets = await get_all_wallets()
    proxies = await load_proxies_from_file()
    if not proxies:
        print(Fore.RED + "⚠️  In file proxy.txt not enogh proxy!" + Style.RESET_ALL)
        return
    unassigned_wallets = [w for w in all_wallets if not w.get("proxy")]
    if not unassigned_wallets:
        print(Fore.GREEN + "✅ All wallets already have a proxy!" + Style.RESET_ALL)
        return
    assigned_count = 0
    for wallet in unassigned_wallets:
        if proxies:
            proxy = proxies.pop(0)
            await update_wallet_proxy(wallet["address"], proxy)
            assigned_count += 1
        else:
            break
    print(Fore.GREEN + f"✅ Proxy issued {assigned_count} wallets. ")


async def buy_monad(wallet: Dict):
    try:
        ins = AsyncGasZipBuyMonad(rpc=arb_rpc, private_key=wallet['private_key'])
        await ins.buy_monad_on_GasZip()
    except Exception as e:
        print(f'Error at buy $MON for wallet {wallet["address"]}: {e}')

async def buy_monad_for_all_wallets():
    all_wallets = await get_all_wallets()
    if not all_wallets:
        print("🚨 In database not wallets")
        return
    tasks = []
    for wallet in all_wallets:
        task = buy_monad(wallet)
        tasks.append(task)
    await asyncio.gather(*tasks)
    print("✅ Buy $MON ended.")


async def run_kinza(wallet: Dict):
    try:
        k = Kinza(rpc_url=monad_rpc, private_key=wallet['private_key'])
        await k.infinity_approve()
        await k.Kinza_supply_DAK()
        await update_last_run("kinza", wallet['address'])
    except Exception as e:
        print(f"[run_kinza] Error: {e}")

async def run_magma(wallet: Dict):
    try:
        m = MAGMA(rpc_url=monad_rpc, private_key=wallet['private_key'])
        await m.magma_stake_mon()
        await asyncio.sleep(4)
        await m.magma_unstake_gmon()
        await update_last_run("magma", wallet['address'])
    except Exception as e:
        print(f"[run_magma] Error: {e}")

async def run_chog(wallet: Dict):
    try:
        chog = BUY_CHOG(private_key=wallet['private_key'], rpc=monad_rpc, proxy=wallet['proxy'])
        await chog.response_buy_chog()
        await update_last_run("chog", wallet['address'])
    except Exception as e:
        print(f"[run_chog] Error: {e}")

async def run_dak(wallet: Dict):
    try:
        dak = BUY_DAK(private_key=wallet['private_key'], rpc=monad_rpc, proxy=wallet['proxy'])
        await dak.response_buy_dak()
        await update_last_run("dak", wallet['address'])
    except Exception as e:
        print(f"[run_dak] Error: {e}")

async def run_yaki(wallet: Dict):
    try:
        yaki = BUY_YAKI(private_key=wallet['private_key'], rpc=monad_rpc,  proxy=wallet['proxy'])
        await yaki.response_buy_yaki()
        await update_last_run("yaki", wallet['address'])
    except Exception as e:
        print(f"[run_yaki] Error: {e}")

async def run_monorail(wallet: Dict):
    try:
        mn = MONORAIL(private_key=wallet['private_key'], rpc=monad_rpc, proxy=wallet.get("proxy"))
        await mn.monorail_swap()
        await update_last_run("monorail", wallet['address'])
    except Exception as e:
        print(f"[run_monorail] Error: {e}")

async def run_nft(wallet: Dict):
    try:
        minter = LilChogstarsMinter(rpc_url=monad_rpc, private_key=wallet['private_key'], quantity=1)
        await minter.lilChogstars_mint()
        await update_last_run("nft", wallet['address'])
    except Exception as e:
        print(f"[run_nft] Error: {e}")

async def run_pandaria(wallet: Dict):
    try:
        pand = DepositContract(rpc_url=monad_rpc, private_key=wallet['private_key'])
        await pand.pandaria_wrap()
        await update_last_run("pandaria", wallet['address'])
    except Exception as e:
        print(f"[run_pandaria] Error: {e}")

SCRIPT_MAP = {
    "kinza": run_kinza,
    "magma": run_magma,
    "chog": run_chog,
    "dak": run_dak,
    "yaki": run_yaki,
    "monorail": run_monorail,
    "nft": run_nft,
    "pandaria": run_pandaria,
}

DIGIT_MAP = {
    "1": "bean",
    "2": "kinza",
    "3": "magma",
    "4": "chog",
    "5": "dak",
    "6": "yaki",
    "7": "monorail",
    "8": "nft",
    "9": "pandaria",
}

async def auto_route():
    print(Fore.CYAN + "\n🚀 launching auto route..." + Style.RESET_ALL)
    delay = await set_custom_delay()  
    all_wallets = await get_all_wallets()
    if not all_wallets:
        print(Fore.RED + "❌ In database not wallets!" + Style.RESET_ALL)
        return
    print(f"📊 All wallets in DB: {len(all_wallets)}")
    tasks = defaultdict(list)
    skipped_wallets = set() 
    for wallet in all_wallets:
        try:
            checker = AsyncTokenBalanceChecker(rpc_url=monad_rpc, private_key=wallet["private_key"])
            balance = await checker.get_mon_balance()
            await update_balance_in_db(wallet["address"], balance)
            wallet["balance"] = balance
        except Exception as e:
            print(Fore.RED + f"⚠️ Error receiving balance {wallet['address']}: {e}" + Style.RESET_ALL)
            wallet["balance"] = 0.0
        if not wallet.get("proxy") or float(wallet["balance"] )< 0.1:
            if wallet["address"] not in skipped_wallets:
                print(Fore.YELLOW + f"⏩ SKIP: {wallet['address']} - not proxy or balance ({wallet['balance']:.6f}) < 0.1" + Style.RESET_ALL)
                skipped_wallets.add(wallet["address"]) 
            continue
        last_runs = {script: wallet.get(f"last_run_{script}") for script in SCRIPT_MAP.keys()}
        sorted_scripts = sorted(last_runs.items(), key=lambda x: x[1] or "1970-01-01T00:00:00")
        for script, _ in sorted_scripts:
            tasks[script].append(wallet)
    if not tasks:
        print(Fore.RED + "❌There are no tasks for the auto-route." + Style.RESET_ALL)
        return
    print(f"\n🔄 Total task: {sum(len(wl) for wl in tasks.values())}")
    for script_name, wallets in tasks.items():
        runner = SCRIPT_MAP.get(script_name)
        if not runner:
            continue
        print(Fore.GREEN + f"\n🚀 Run {script_name} for {len(wallets)} wallets!" + Style.RESET_ALL)
        async def do_one_task(wallet):
            await runner(wallet)
            await asyncio.sleep(delay)
        await asyncio.gather(*[do_one_task(wallet) for wallet in wallets])
    print(Fore.GREEN + "✅ Auto route ended." + Style.RESET_ALL)

async def manual_route():
    print(Fore.CYAN + "\n🎛️ launching manual route!" + Style.RESET_ALL)
    print(" 1 --- Bean", "\n",
          "2 --- Kinza", "\n",
          "3 --- Magma", "\n",
          "4 --- Buy Chog in main-site", "\n",
          "5 --- Buy Dak in main-site", "\n",
          "6 --- Buy Yaki in main-site", "\n",
          "7 --- Monorail - Swap any tokens", "\n",
          "8 --- Mint LilChogstars", "\n",
          "9 --- Pandaria"
    )
    route_str = input(Fore.YELLOW + "\n⏳  Enter the scripts sequence (fot example'15234'): " + Style.RESET_ALL).strip()
    if not route_str.isdigit():
        print(Fore.RED + "❌  ERROR: etner only numbers!" + Style.RESET_ALL)
        return
    all_wallets = await get_all_wallets()
    if not all_wallets:
        print(Fore.RED + "🚨In database not wallets." + Style.RESET_ALL)
        return
    print(Fore.GREEN + f"📊 Found {len(all_wallets)} wallets." + Style.RESET_ALL)
    delay = await set_custom_delay() 
    skipped_wallets = set()  
    big_task_list = []
    for digit in route_str:
        script_name = DIGIT_MAP.get(digit)
        if not script_name:
            continue
        runner = SCRIPT_MAP.get(script_name)
        if not runner:
            print(Fore.RED + f"⚠️ Script {script_name} not found." + Style.RESET_ALL)
            continue
        for wallet in all_wallets:
            try:
                checker = AsyncTokenBalanceChecker(rpc_url=monad_rpc, private_key=wallet["private_key"])
                balance = await checker.get_mon_balance()
                await update_balance_in_db(wallet["address"], balance)
                wallet["balance"] = balance
            except Exception as e:
                print(Fore.RED + f"⚠️ Error recevid balance {wallet['address']}: {e}" + Style.RESET_ALL)
                wallet["balance"] = 0.0
            if not wallet.get("proxy") or float(wallet["balance"] )< 0.1:
                if wallet["address"] not in skipped_wallets:
                    print(Fore.YELLOW + f"⏩ SKIP: {wallet['address']} - not proxy or balance ({wallet['balance']:.6f}) < 0.1" + Style.RESET_ALL)
                    skipped_wallets.add(wallet["address"]) 
                continue
            big_task_list.append((runner, wallet))
    if not big_task_list:
        print(Fore.RED + "❌  There are no tasks for the manual-route." + Style.RESET_ALL)
        return
    print(Fore.GREEN + f"\n🚀 Total tasks: {len(big_task_list)}" + Style.RESET_ALL)
    idx = 0
    total = len(big_task_list)
    async def do_one_task(task):
        runner, wallet = task
        await runner(wallet)
        await asyncio.sleep(delay)
    while idx < total:
        left = total - idx
        user_input = input(Fore.YELLOW + f"\n⏳ Fatigue {left} tasks. how many to run in this batch? ('q' for quit) " + Style.RESET_ALL).strip().lower()
        if user_input == 'q':
            print(Fore.RED + "🚪 Quit." + Style.RESET_ALL)
            return
        try:
            batch_size = int(user_input)
            if batch_size <= 0:
                print(Fore.RED + "❌  Enter number > 0 or 'q'." + Style.RESET_ALL)
                continue
        except ValueError:
            print(Fore.RED + "❌ Enter number or 'q'." + Style.RESET_ALL)
            continue
        chunk = big_task_list[idx: idx + batch_size]
        await asyncio.gather(*[do_one_task(task) for task in chunk])
        idx += len(chunk)
        if idx >= total:
            print(Fore.GREEN + "🎉 All tasks completed!" + Style.RESET_ALL)
            break
    print(Fore.GREEN + "✅ Manual route ended." + Style.RESET_ALL)

    
async def set_custom_delay():
    while True:
        try:
            delay = float(input(Fore.YELLOW + "\n⏳ Enter delay (in seconds, for example 10): " + Style.RESET_ALL).strip())
            if delay < 0:
                continue
            return delay
        except ValueError:
            print(Fore.RED + "❌ Enter number in seconds." + Style.RESET_ALL)

async def create_wallets_via_script():
    generate()
    csv_path = "new_addresses.csv"
    new_wallets = await load_wallets_from_csv(csv_path)
    if new_wallets:
        await add_wallets_bulk(new_wallets)
    else:
        print("Failed to load wallets from new_addresses.csv.")

async def select_wallet_source():
    while True:
        print("Откуда брать?")
        print("1) Load from private_key.txt")
        print("2) Python-list (from config.py)")
        print("3) Go back to previous menu ")
        choice = input("Выберите (1/2/3): ").strip()

        if choice == '1':
            load_wallets_from_private_keys() 

        elif choice == "2":
            list_wallets_data = load_wallets_from_list(wallets)
            if list_wallets_data:
                add_wallets_bulk(list_wallets_data)
            else:
                print("List in config.py empty. ")

        elif choice == "3":
            return
        else:
            print("Unknowmn choice. Try again. ")

async def main():
    await init_db()
    await print_banner()
    while True:
        print("\n--- MAIN MENU ---")
        print("1) Use existing wallets")
        print("2) Generate new wallets")
        print("3) Assign proxies")
        print("4) Auto route")
        print("5) Manual route")
        print("6) Clear all wallets")
        print("7) List all wallets")
        print("8) Buy $MON for all")
        print("0) Exit")
        
        ans = input("Select (1-8/0): ").strip()

        if ans == "1":
            await select_wallet_source()
        elif ans == "2":
            await create_wallets_via_script()
        elif ans == "3":
            await assign_proxies_to_wallets()
        elif ans == "4":
            await auto_route()
        elif ans == "5":
            await manual_route()
        elif ans == "6":
            await clear_all_wallets()
        elif ans == "7":
            await print_all_wallet_addresses()
        elif ans == '8':
            await buy_monad_for_all_wallets()
        elif ans == "0":
            break
        else:
            print("❌ Unknowmn choice. Try again")

if __name__ == "__main__":
    asyncio.run(main())