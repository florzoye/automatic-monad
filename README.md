# 🚀 **Monad AutoTestTool**  

**Monad AutoTestTool** – a powerful tool for managing EVM wallets with both automated and custom routes in the MONAD test network.  

---

## 📌 **Functionality**  

- **SQLite3 Database Storage**  
    - Automatic data collection  
    - Sorting by last script execution  
    - Auto-skipping wallets without `proxy` or `balance ≤ 0.1 $MON`  

- **Wallet Management**  
    - Automatic EVM wallet generation and saving in `new_addresses.csv`  
    - Import from a text file `private_key.txt`  
    - Import from a Python list format `[{'key':'123qwe','proxy':'user:pass@ip:port'}]`  

- **Proxy Assignment**  
    - Automatic assignment from Python list  
    - Additional assignment from `proxy.txt` file  

- **Task Execution Routes**  
  - **General Features**  
    - Custom delay between tasks  
    - Batch execution of accounts (default: 5 at a time, adjustable via `max_workers = x`)  

  - **Automatic Route**  
      - Activities are sorted by last execution date (starting with the oldest) and executed sequentially  

  - **Manual Route**  
      - Users select the execution sequence of scripts  
      - Manual batch size adjustment for task execution  

- **Supported dApps**  
    - BeanExchange  
    - KinzaFinance  
    - Magma  
    - Meme coin purchases via main site (`https://testnet.monad.xyz/`)  
    - Monorail  
    - Minting LilChogStars  
    - Pandaria  

- **MON Token Purchase**  
    - Automatically buys $MON for $2 via GasZip (requires at least $2.5 ETH/ARB balance per wallet)  

---

## 🚀 **Usage**  

### 🛠️ **Available Commands:**  
| #  | Action  |
|----|---------|
| 1️⃣  | Use existing wallets  |  
| 2️⃣  | Create new wallets  |
| 3️⃣  | Assign proxies from `proxy.txt`  |
| 4️⃣  | Automatic execution route  |
| 5️⃣  | Manual execution route  |
| 6️⃣  | Delete all wallets from the database  |
| 7️⃣  | Display all wallet addresses  |
| 8️⃣  | Buy $MON for all wallets  |  

---

## 🔧 **Configuration**  
Modify RPC settings and other parameters in `config.py`:  
```python
monad_rpc = 'https://testnet-rpc.monad.xyz/'
arb_rpc = "https://1rpc.io/arb"
wallets = [{'key': '123qweasxd','proxy': 'user:pass@ip:port'}] # ADD YOUR WALLETS AND PROXIES HERE
```


---

## 📌 **What’s Included:**  
- ✅ **Full script functionality**  
- ✅ **Task automation**  
- ✅ **Limit bypassing and optimization**  
- ✅ **Technical support**  
- ✅ **Option to add 3-5 new dApps** *(only available with active update plans)*  

💬 **contact via Telegram:** [@xflorzoye](https://t.me/xflorzoye)  

---
## monad
