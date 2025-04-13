import requests
import time
import logging
import os

UUID_FILE = ".plex_uuid"

# Configure logging
logging.basicConfig(level=logging.INFO)

# Plex API details
API_URL = "https://community.plex.tv/api"
HEADERS = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "x-plex-client-identifier": "xxxx",
    "x-plex-platform": "Chrome",
    "x-plex-product": "Plex Web",
    "x-plex-token": "xxxx",
    "x-plex-version": "4.145.1",
}

# Configurable delay between requests
REQUEST_DELAY = 3.0  # Default to 3s

def get_uuid():
    """Fetch the UUID from a file, or prompt the user if it doesn't exist."""
    if os.path.exists(UUID_FILE):
        with open(UUID_FILE, "r") as f:
            return f.read().strip()
    else:
        uuid = input("Enter your Plex User UUID: ").strip()
        with open(UUID_FILE, "w") as f:
            f.write(uuid)
        return uuid


def make_api_request(query, variables, operation_name):
    """Reusable function to make API requests."""
    try:
        response = requests.post(
            API_URL,
            headers=HEADERS,
            json={"query": query, "variables": variables, "operationName": operation_name},
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {e}")
        return None


def fetch_watch_history(after_cursor=None):
    """Fetch watch history from the Plex API."""
    query = """
    query GetWatchHistoryHub($uuid: ID = "", $first: PaginationInt!, $after: String) {
      user(id: $uuid) {
        watchHistory(first: $first, after: $after) {
          nodes {
            id
            metadataItem {
              type
              title
              parent {
                title
              }
              grandparent {
                title
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """
    variables = {"first": 50, "uuid": get_uuid()}
    if after_cursor:
        variables["after"] = after_cursor

    return make_api_request(query, variables, "GetWatchHistoryHub")


def delete_activity(activity_id):
    """Delete a single activity from the Plex API."""
    mutation = """
    mutation removeActivity($input: RemoveActivityInput!) {
      removeActivity(input: $input)
    }
    """
    variables = {"input": {"id": activity_id, "type": "WATCH_HISTORY"}}
    while True:
        try:
            response = requests.post(
                API_URL,
                headers=HEADERS,
                json={"query": mutation, "variables": variables, "operationName": "removeActivity"},
            )
            response.raise_for_status()
            result = response.json()

            # Check for rate limit error
            if result.get("errors"):
                for error in result["errors"]:
                    if error.get("extensions", {}).get("code") == "RATE_LIMITED":
                        retry_after = error["extensions"].get("retryAfter", 60)  # Default to 60 seconds
                        logging.warning(f"Rate limit exceeded. Retrying after {retry_after} seconds... ⏳")
                        time.sleep(retry_after)
                        continue  # Retry the deletion

                logging.error(f"Failed to delete activity ID {activity_id}: {result['errors']}")
                return False
            else:
                logging.info(f"Successfully deleted activity ID: {activity_id}")
                return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Error deleting activity ID {activity_id}: {e}")
            return False


def delete_all_watch_history(auto_confirm=False):
    """Delete all watch history."""
    after_cursor = None
    while True:
        data = fetch_watch_history(after_cursor)
        if not data:
            logging.error("Failed to fetch watch history.")
            break

        nodes = data["data"]["user"]["watchHistory"]["nodes"]
        page_info = data["data"]["user"]["watchHistory"]["pageInfo"]

        for node in nodes:
            activity_id = node["id"]
            metadata = node["metadataItem"]
            item_type = metadata.get("type", "Unknown")
            title = metadata.get("title", "Unknown")
            parent_title = metadata.get("parent", {}).get("title", "")
            grandparent_title = metadata.get("grandparent", {}).get("title", "")

            # Determine emoji and display item details
            if item_type.lower() == "episode":
                emoji = "📺"
                item_display = f"{emoji} EPISODE: {title} (Show: {grandparent_title}, Season: {parent_title})"
            elif item_type.lower() == "movie":
                emoji = "🎥"
                item_display = f"{emoji} MOVIE: {title}"
            else:
                emoji = "📄"
                item_display = f"{emoji} OTHER: {title}"

            print(f"Found: {item_display} (ID: {activity_id})")

            # Confirm deletion
            if auto_confirm or input(f"Delete {item_display}? (y/n): ").lower() == "y":
                if delete_activity(activity_id):
                    print(f"✅ Successfully deleted: {item_display}")
                else:
                    print(f"❌ Failed to delete: {item_display}")
                time.sleep(REQUEST_DELAY)  # Configurable delay

        # Check if there's more data to fetch
        if not page_info["hasNextPage"]:
            break
        after_cursor = page_info["endCursor"]


def menu():
    """Display the main menu."""
    global REQUEST_DELAY
    print("Welcome to the Plex Watch History Manager!")
    print("1. Delete all watch history (auto-confirm)")
    print("2. Delete only movies (auto-confirm)")
    print("3. Delete only episodes (auto-confirm)")
    print("4. Dry run (preview items)")
    print("5. Set request delay (current: {:.6f}s)".format(REQUEST_DELAY))
    print("6. Exit")
    choice = input("Enter your choice: ")

    if choice == "1":
        delete_all_watch_history(auto_confirm=True)
    elif choice == "2":
        delete_filtered_watch_history("movie", auto_confirm=True)
    elif choice == "3":
        delete_filtered_watch_history("episode", auto_confirm=True)
    elif choice == "4":
        preview_watch_history()  # Call the new preview function
    elif choice == "5":
        REQUEST_DELAY = float(input("Enter new request delay in seconds (e.g., 0.001 for 1ms): "))
        print(f"Request delay set to {REQUEST_DELAY:.6f}s")
    elif choice == "6":
        exit()
    else:
        print("Invalid choice. Please try again.")


def delete_filtered_watch_history(filter_type, auto_confirm=False):
    """Delete filtered watch history by type."""
    after_cursor = None
    while True:
        data = fetch_watch_history(after_cursor)
        if not data:
            logging.error("Failed to fetch watch history.")
            break

        nodes = data["data"]["user"]["watchHistory"]["nodes"]
        page_info = data["data"]["user"]["watchHistory"]["pageInfo"]

        for node in nodes:
            activity_id = node["id"]
            metadata = node["metadataItem"]
            item_type = metadata.get("type", "Unknown")
            title = metadata.get("title", "Unknown")
            parent_title = metadata.get("parent", {}).get("title", "")
            grandparent_title = metadata.get("grandparent", {}).get("title", "")

            # Skip items that don't match the filter
            if item_type.lower() != filter_type.lower():
                continue

            # Determine emoji and display item details
            if item_type.lower() == "episode":
                emoji = "📺"
                item_display = f"{emoji} EPISODE: {title} (Show: {grandparent_title}, Season: {parent_title})"
            elif item_type.lower() == "movie":
                emoji = "🎥"
                item_display = f"{emoji} MOVIE: {title}"
            else:
                emoji = "📄"
                item_display = f"{emoji} OTHER: {title}"

            print(f"Found: {item_display} (ID: {activity_id})")

            # Confirm deletion
            if auto_confirm or input(f"Delete {item_display}? (y/n): ").lower() == "y":
                if delete_activity(activity_id):
                    print(f"✅ Successfully deleted: {item_display}")
                else:
                    print(f"❌ Failed to delete: {item_display}")
                time.sleep(REQUEST_DELAY)  # Configurable delay

        # Check if there's more data to fetch
        if not page_info["hasNextPage"]:
            break
        after_cursor = page_info["endCursor"]


if __name__ == "__main__":
    while True:
        menu()
