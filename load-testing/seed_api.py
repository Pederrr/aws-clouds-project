#!/usr/bin/env python3
import argparse
import csv
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import requests


class ApiClient:
    def __init__(self, base_url: str, timeout: float, retries: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()

    def _request(
        self,
        method: str,
        path: str,
        token: Optional[str] = None,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        last_error = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    headers=headers,
                    json=json,
                    params=params,
                    timeout=self.timeout,
                )
                if response.status_code >= 500 and attempt < self.retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise exc

        raise last_error  # pragma: no cover

    def register(self, email: str, password: str, name: str) -> requests.Response:
        return self._request(
            "POST",
            "/v1/register",
            json={
                "email": email,
                "password": password,
                "name": name,
            },
        )

    def login(self, email: str, password: str) -> Tuple[str, dict]:
        response = self._request(
            "POST",
            "/v1/login",
            json={
                "email": email,
                "password": password,
            },
        )
        if response.status_code != 201:
            raise RuntimeError(
                f"Login failed ({response.status_code}): {response.text}"
            )
        data = response.json()
        return data["access_token"], data

    def create_profile(
        self, token: str, display_name: str, visibility: str
    ) -> requests.Response:
        return self._request(
            "POST",
            "/v1/profiles",
            token=token,
            json={
                "display_name": display_name,
                "visibility": visibility,
            },
        )

    def add_book(self, token: str, payload: dict) -> requests.Response:
        return self._request("POST", "/v1/books", token=token, json=payload)

    def get_books(self, token: str, offset: int) -> requests.Response:
        return self._request(
            "GET",
            "/v1/books",
            token=token,
            params={"offset": offset},
        )

    def add_note(self, token: str, book_id: int, payload: dict) -> requests.Response:
        return self._request(
            "POST", f"/v1/books/{book_id}/notes", token=token, json=payload
        )


def build_isbn(user_index: int, book_index: int) -> str:
    base = 9780000000000 + (user_index * 100) + book_index
    return str(base)


def generate_books(rng: random.Random, user_index: int, count: int) -> List[dict]:
    words = [
        "Silent",
        "Ocean",
        "Winter",
        "Starlight",
        "River",
        "Hidden",
        "Crimson",
        "Garden",
        "Shadow",
        "Golden",
        "Echo",
        "Glass",
        "Forge",
        "Wander",
        "Map",
        "Cedar",
    ]
    authors = [
        "Avery",
        "Campbell",
        "Harper",
        "Jordan",
        "Morgan",
        "Parker",
        "Quinn",
        "Reese",
        "Sawyer",
        "Taylor",
        "Blake",
        "Elliot",
        "Lane",
        "Reid",
        "Spencer",
        "Hayes",
    ]
    statuses = ["To be read", "Currently reading", "Read", "Did not finish"]

    books = []
    for book_index in range(count):
        title = f"{rng.choice(words)} {rng.choice(words)}"
        author = f"{rng.choice(authors)} {rng.choice(authors)}"
        total_pages = rng.randint(120, 700)
        current_page = rng.randint(0, total_pages)
        reading_status = rng.choice(statuses)
        if reading_status == "To be read":
            current_page = 0
        books.append(
            {
                "title": title,
                "isbn": build_isbn(user_index, book_index),
                "author": author,
                "description": f"A story about {rng.choice(words).lower()} and {rng.choice(words).lower()}.",
                "reading_status": reading_status,
                "current_page": current_page,
                "total_pages": total_pages,
            }
        )
    return books


def generate_notes(rng: random.Random, notes_per_book: int) -> List[dict]:
    notes = []
    snippets = [
        "Thoughts on the chapter",
        "Key takeaway",
        "Interesting passage",
        "Plot twist",
        "Character insight",
        "Memorable quote",
        "Theme connection",
        "Open question",
    ]
    for _ in range(notes_per_book):
        notes.append(
            {
                "content": f"{rng.choice(snippets)}: {rng.choice(snippets).lower()}.",
                "visibility": "hidden",
            }
        )
    return notes


def fetch_book_id_map(
    api: ApiClient, token: str, expected_isbns: List[str]
) -> Dict[str, int]:
    remaining = set(expected_isbns)
    isbn_to_id: Dict[str, int] = {}
    offset = 1
    while remaining:
        response = api.get_books(token, offset=offset)
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch books ({response.status_code}): {response.text}"
            )
        payload = response.json()
        for item in payload.get("items", []):
            isbn = str(item.get("isbn"))
            if isbn in remaining:
                isbn_to_id[isbn] = item.get("id")
                remaining.remove(isbn)

        meta = payload.get("meta", {})
        if not meta.get("has_next"):
            break
        offset += 1

    return isbn_to_id


def seed_user(
    api: ApiClient,
    seed: int,
    index: int,
    books_per_user: int,
    notes_per_book: int,
    public_ratio: float,
    password_pattern: str,
) -> Tuple[str, str, str]:
    rng = random.Random(seed + index)
    email = f"seed{index:05d}@example.com"
    name = f"seed_user_{index:05d}"
    password = password_pattern.format(index=index)

    register_response = api.register(email=email, password=password, name=name)
    if register_response.status_code not in (201, 409):
        raise RuntimeError(
            f"Register failed ({register_response.status_code}): {
                register_response.text
            }"
        )

    token, _ = api.login(email=email, password=password)
    visibility = "public" if rng.random() < public_ratio else "hidden"
    profile_response = api.create_profile(
        token=token, display_name=name, visibility=visibility
    )
    if profile_response.status_code not in (200, 409):
        raise RuntimeError(
            f"Profile failed ({profile_response.status_code}): {profile_response.text}"
        )

    books = generate_books(rng, index, books_per_user)
    for book in books:
        response = api.add_book(token=token, payload=book)
        if response.status_code != 200:
            raise RuntimeError(
                f"Add book failed ({response.status_code}): {response.text}"
            )

    isbn_map = fetch_book_id_map(api, token, [book["isbn"] for book in books])
    for book in books:
        book_id = isbn_map.get(book["isbn"])
        if not book_id:
            raise RuntimeError(f"Book id not found for isbn {book['isbn']}")
        for note in generate_notes(rng, notes_per_book):
            response = api.add_note(token=token, book_id=book_id, payload=note)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Add note failed ({response.status_code}): {response.text}"
                )

    return email, password, name, visibility


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed BookLogr using the public API.")
    parser.add_argument(
        "--users", type=int, default=1000, help="Number of users to create."
    )
    parser.add_argument(
        "--books-per-user", type=int, default=10, help="Books per user."
    )
    parser.add_argument("--notes-per-book", type=int, default=2, help="Notes per book.")
    parser.add_argument(
        "--output", type=str, default="seed_users.csv", help="Output CSV path."
    )
    parser.add_argument(
        "--seed", type=int, default=int(os.getenv("SEED", "1337")), help="Random seed."
    )
    parser.add_argument(
        "--public-ratio",
        type=float,
        default=0.30,
        help="Ratio of public profiles (0-1).",
    )
    parser.add_argument(
        "--workers", type=int, default=8, help="Number of worker threads."
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="Request timeout seconds."
    )
    parser.add_argument(
        "--retries", type=int, default=3, help="Retries for 5xx or network errors."
    )
    parser.add_argument(
        "--password-pattern",
        type=str,
        default="seedpass-{index}",
        help="Password format string. Use {index} for the user index.",
    )
    return parser.parse_args()


def main() -> int:
    api_url = os.getenv("API_URL")
    if not api_url:
        print("API_URL is not set.", file=sys.stderr)
        return 1

    args = parse_args()
    if args.users <= 0:
        print("--users must be > 0", file=sys.stderr)
        return 1
    if args.books_per_user < 0 or args.notes_per_book < 0:
        print("--books-per-user and --notes-per-book must be >= 0", file=sys.stderr)
        return 1
    if not (0.0 <= args.public_ratio <= 1.0):
        print("--public-ratio must be between 0 and 1", file=sys.stderr)
        return 1

    api = ApiClient(api_url, timeout=args.timeout, retries=args.retries)

    with open(args.output, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["email", "password", "name", "profile_visibility"])

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [
                executor.submit(
                    seed_user,
                    api,
                    args.seed,
                    index,
                    args.books_per_user,
                    args.notes_per_book,
                    args.public_ratio,
                    args.password_pattern,
                )
                for index in range(args.users)
            ]
            completed = 0
            for future in as_completed(futures):
                email, password, name, visibility = future.result()
                writer.writerow([email, password, name, visibility])
                completed += 1
                if completed % 100 == 0:
                    print(f"Seeded {completed}/{args.users} users")

    print(f"Done. Wrote credentials to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
