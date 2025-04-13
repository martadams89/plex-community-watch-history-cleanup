# Plex History Cleanup

**Plex History Cleanup** is a Python tool that deletes your **Plex cloud watch history** — including movies, episodes, or both — by directly interacting with the undocumented `https://community.plex.tv/api` GraphQL endpoint.

This is useful if you want to:

- Reset your "Continue Watching" or "Watch Again" rows
- Remove movies/episodes from watch history for privacy
- Automate cleanup of your Plex activity for a specific user

> This tool operates on **Plex's cloud activity history**, not the history from your personal Plex Media Server.

---

## Features

- Delete all activity
- Delete only movies or only episodes
- Dry run (preview what would be deleted)
- Configurable delay between requests
- Rate limit handling with auto-retry
- Stores your UUID in a `.plex_uuid` file after prompting once

---

## How It Works

This script sends **GraphQL queries and mutations** to `https://community.plex.tv/api`, using the same headers your browser uses when browsing Plex Web.

It fetches your watch history, then issues a `removeActivity` mutation for each item.

---

## Rate Limiting

Plex occasionally rate-limits mutation calls. When this happens:

- The server returns an error with `"code": "RATE_LIMITED"`
- The script will **pause for the time specified** by `retryAfter` (usually 60 seconds) and then retry the deletion
- Logging clearly shows when you're rate-limited

---

## Setup

### 1. Clone the Repo

```bash
git clone https://github.com/yourname/plex-history-cleanup.git
cd plex-history-cleanup
```

### 2. Create a Virtual Environment (Optional but Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install requests
```

---

## Required Headers

To use the script, you'll need to provide:

### 1. `x-plex-token` (OAuth Token)

This is a temporary token generated when you log in to Plex Web.

**How to get it:**

1. Go to [https://app.plex.tv](https://app.plex.tv)
2. Open Developer Tools (F12 or right-click > Inspect)
3. Browse to Plex in the Server List
4. Selecg Discover > My Watch History
5. Go to the **Network** tab
6. Filter for requests to `https://community.plex.tv/api`
7. Look at a GraphQL request and copy the `x-plex-token` header value

### 2. `x-plex-client-identifier`

Also found in the headers of the same GraphQL requests in the Network tab. This is **unique per browser session** and can usually be reused for short-term use.

---

## User UUID

This identifies the specific user whose watch history you’re managing. It looks like a long hex string (e.g., `bc3b48bb77df78d`).

**How to get it:**

1. In the same Developer Tools > Network tab
2. Open up the Plex Web Dashboard
3. Navigate to the Plex Server in the Server List
4. Open Discover > My Watchlist History and then scroll down, the list should then expand showing further entries. 
5. Look for the latest api request in the developer tools. Right click on it and copy to cURL
6. Paste the cURL output into a text edit and search for the `uuid` string under the `variables` payload — it contains `"uuid": "your_user_uuid_here"`

---

## UUID Storage (`.plex_uuid`)

To avoid hardcoding the UUID into the script, the tool will:

- Check for a `.plex_uuid` file in the project directory
- If it doesn't exist, prompt you for the UUID once
- Save it to `.plex_uuid` so it's reused in future runs

---

## Configuration and Customization

Edit the `HEADERS` block at the top of `plex_history_cleanup.py`:

```bash
HEADERS = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "x-plex-client-identifier": "your-client-id-here",
    "x-plex-platform": "Chrome",
    "x-plex-product": "Plex Web",
    "x-plex-token": "your-oauth-token-here",
    "x-plex-version": "4.145.1",
}
```

You can change the default request delay by editing the global variable:

```bash
REQUEST_DELAY = 3.0  # Delay in seconds between delete requests
```

---

## Running the Script

Once configured, run the script:

```bash
python plex_history_cleanup/plex_history_cleanup.py
```

### Menu Options

You’ll be presented with:

```bash
1. Delete all watch history (auto-confirm)
2. Delete only movies (auto-confirm)
3. Delete only episodes (auto-confirm)
4. Dry run (preview items)
5. Set request delay
6. Exit
```

Use `Dry run` if you want to see what will be deleted without actually deleting it.

---

## Things You Must Configure

- `x-plex-token` → Replace with your browser's token
- `x-plex-client-identifier` → Set this to your identifier (can be reused temporarily)
- `UUID` → Will be prompted on first run and stored in `.plex_uuid`

---

## Limitations

- Only works for the **primary Plex account**, not shared users under a managed account
- Only deletes **cloud watch history**, not local server metadata
- The token may expire after a while; if you get 401 errors, extract a fresh token

---

## Disclaimer

This tool interacts with **undocumented APIs** and was reverse-engineered using browser developer tools. Use at your own risk.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
