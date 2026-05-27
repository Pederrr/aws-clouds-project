import csv
import os
import random
from datetime import datetime, timezone

from locust import HttpUser, between, task


SEED_USERS_PATH = os.path.join(os.path.dirname(__file__), "existing_users.csv")

READING_STATUSES = [
    "To be read",
    "Currently reading",
    "Read",
    "Did not finish",
]

BOOK_CATALOG = [
    {
        "title": "The Atlas of Dust",
        "author": "Marina Feld",
        "description": "A cartographer uncovers a forgotten city hidden by storms.",
    },
    {
        "title": "Rivers of Glass",
        "author": "Owen Pierce",
        "description": "A journalist traces a family legend across continents.",
    },
    {
        "title": "Signal in the Pines",
        "author": "Harper Sun",
        "description": "A ranger discovers a radio signal echoing from decades past.",
    },
    {
        "title": "Orbit of Silence",
        "author": "Leena Vos",
        "description": "A deep space crew navigates a mysterious blackout zone.",
    },
    {
        "title": "Winter Market",
        "author": "Cade Morgan",
        "description": "A baker builds a business while unraveling a town secret.",
    },
    {
        "title": "Paper Kingdom",
        "author": "Nora Whit",
        "description": "An archivist discovers letters that rewrite a rebellion.",
    },
    {
        "title": "Tide of Ember",
        "author": "Rafael Kline",
        "description": "A coastal village faces a season of strange fires.",
    },
]


def load_seed_users():
    users = []
    with open(SEED_USERS_PATH, "r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            users.append(
                {
                    "email": row["email"].strip(),
                    "password": row["password"].strip(),
                    "name": row["name"].strip(),
                    "profile_visibility": row["profile_visibility"].strip(),
                }
            )
    return users


SEED_USERS = load_seed_users()
PUBLIC_PROFILE_NAMES = [
    user["name"]
    for user in SEED_USERS
    if user["profile_visibility"].lower() == "public"
]


def generate_isbn13():
    return "978" + "".join(str(random.randint(0, 9)) for _ in range(10))


class BookLogrUser(HttpUser):
    wait_time = between(2, 8)

    def on_start(self):
        self.user = random.choice(SEED_USERS)
        self.access_token = None
        self.refresh_token = None
        self.book_cache = {}
        self.note_ids = []
        self.login()
        self.ensure_profile()

    def auth_headers(self, use_refresh=False):
        token = self.refresh_token if use_refresh else self.access_token
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    def login(self):
        payload = {"email": self.user["email"], "password": self.user["password"]}
        with self.client.post(
            "/v1/login",
            json=payload,
            name="auth: login",
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                response.success()
            else:
                response.failure(
                    f"Login failed: {response.status_code} {response.text}"
                )

    def refresh_access_token(self):
        if not self.refresh_token:
            return False
        with self.client.post(
            "/v1/token/refresh",
            headers=self.auth_headers(use_refresh=True),
            name="auth: refresh",
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token", self.refresh_token)
                response.success()
                return True
            response.failure(f"Refresh failed: {response.status_code} {response.text}")
            return False

    def request_with_refresh(self, method, url, name=None, **kwargs):
        headers = kwargs.pop("headers", {})
        headers.update(self.auth_headers())
        with self.client.request(
            method,
            url,
            headers=headers,
            name=name,
            catch_response=True,
            **kwargs,
        ) as response:
            if response.status_code == 401 and self.refresh_access_token():
                response.success()
                return self.client.request(
                    method,
                    url,
                    headers=self.auth_headers(),
                    name=f"{name} (retry)" if name else None,
                    **kwargs,
                )
            if response.status_code >= 400:
                response.failure(f"{response.status_code} {response.text}")
            return response

    def ensure_profile(self):
        response = self.request_with_refresh("GET", "/v1/profiles", name="profile: me")
        if response is None:
            return
        if response.status_code == 404:
            payload = {
                "display_name": self.user["name"],
                "visibility": self.user["profile_visibility"],
            }
            self.request_with_refresh(
                "POST", "/v1/profiles", name="profile: create", json=payload
            )

    def update_book_cache(self, items):
        for book in items:
            book_id = book.get("id")
            if not book_id:
                continue
            self.book_cache[book_id] = book

    def fetch_books(self):
        params = {
            "status": random.choice(READING_STATUSES),
            "sort_by": random.choice(
                ["created_on", "title", "author", "rating", "isbn"]
            ),
            "order": random.choice(["asc", "desc"]),
        }
        response = self.request_with_refresh(
            "GET", "/v1/books", name="books: list", params=params
        )
        if response is None or response.status_code != 200:
            return []
        data = response.json() or {}
        items = data.get("items", [])
        self.update_book_cache(items)
        return items

    def select_book_id(self):
        if not self.book_cache:
            self.fetch_books()
        if not self.book_cache:
            return None
        return random.choice(list(self.book_cache.keys()))

    def select_note_id(self):
        if not self.note_ids:
            return None
        return random.choice(self.note_ids)

    @task(6)
    def list_books(self):
        self.fetch_books()

    @task(3)
    def add_book(self):
        template = random.choice(BOOK_CATALOG)
        total_pages = random.randint(120, 900)
        status = random.choice(READING_STATUSES)
        current_page = (
            total_pages
            if status == "Read"
            else random.randint(0, max(1, total_pages - 1))
        )

        payload = {
            "title": template["title"],
            "author": template["author"],
            "description": template["description"],
            "isbn": generate_isbn13(),
            "reading_status": status,
            "current_page": current_page,
            "total_pages": total_pages,
        }
        response = self.request_with_refresh(
            "POST", "/v1/books", name="books: add", json=payload
        )
        if response is not None and response.status_code == 200:
            self.fetch_books()

    @task(4)
    def update_book(self):
        book_id = self.select_book_id()
        if not book_id:
            return
        cached = self.book_cache.get(book_id, {})
        total_pages = cached.get("total_pages") or random.randint(120, 900)
        current_page = cached.get("current_page") or 0
        if total_pages and current_page < total_pages:
            current_page = min(total_pages, current_page + random.randint(1, 20))

        payload = {
            "status": random.choice(READING_STATUSES),
            "current_page": current_page,
            "total_pages": total_pages,
            "rating": round(random.uniform(0, 5), 1),
        }
        self.request_with_refresh(
            "PATCH",
            f"/v1/books/{book_id}",
            name="books: update",
            json=payload,
        )

    @task(3)
    def add_note(self):
        book_id = self.select_book_id()
        if not book_id:
            return
        payload = {
            "content": f"Note created at {datetime.now(timezone.utc).isoformat()}.",
            "visibility": random.choice(["hidden", "public"]),
            "created_on": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "quote_page": random.randint(1, 400),
        }
        response = self.request_with_refresh(
            "POST",
            f"/v1/books/{book_id}/notes",
            name="notes: add",
            json=payload,
        )
        if response is not None and response.status_code == 200:
            notes = self.request_with_refresh(
                "GET",
                f"/v1/books/{book_id}/notes",
                name="notes: list",
            )
            if notes is not None and notes.status_code == 200:
                note_items = notes.json() or []
                if note_items:
                    note_id = note_items[0].get("id")
                    if note_id and note_id not in self.note_ids:
                        self.note_ids.append(note_id)

    @task(2)
    def update_note(self):
        note_id = self.select_note_id()
        if not note_id:
            return
        payload = {
            "content": f"Updated note at {datetime.now(timezone.utc).isoformat()}.",
            "visibility": random.choice(["hidden", "public"]),
        }
        self.request_with_refresh(
            "PATCH",
            f"/v1/notes/{note_id}",
            name="notes: update",
            json=payload,
        )

    @task(2)
    def list_notes(self):
        book_id = self.select_book_id()
        if not book_id:
            return
        self.request_with_refresh(
            "GET",
            f"/v1/books/{book_id}/notes",
            name="notes: list",
        )

    @task(2)
    def view_own_profile(self):
        self.request_with_refresh("GET", "/v1/profiles", name="profile: me")

    @task(2)
    def view_public_profile(self):
        if not PUBLIC_PROFILE_NAMES:
            return
        display_name = random.choice(PUBLIC_PROFILE_NAMES)
        self.request_with_refresh(
            "GET",
            f"/v1/profiles/{display_name}",
            name="profile: public",
        )
