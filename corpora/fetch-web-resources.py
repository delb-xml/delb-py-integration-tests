import asyncio
import io
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Final

import delb
from httpx import AsyncClient, HTTPError, HTTPStatusError
from stamina import retry


CORPORA = Path(__file__).parent


# helper


http_client: Final = AsyncClient()


def http_error(exc: Exception) -> bool:
    if isinstance(exc, HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, HTTPError)


@retry(attempts=5, on=http_error)
async def fetch_resource(url: str, destination: io.BufferedWriter):
    async with http_client.stream("GET", url, follow_redirects=True) as response:
        async for chunk in response.aiter_bytes():
            destination.write(chunk)
        print(f"Downloaded {url} to {destination.name}")


# tasks


async def fetch_sturm_edition(target: Path):
    base_url = "https://sturm-edition.de/api/files/"

    for item in delb.Document(base_url).css_select("idno"):
        filename = item.full_text
        if filename in ("Q.01.19151120.JVH.01.xml", "Q.01.19150315.JVH.01.xml"):
            # these are empty files
            continue
        with (target / filename).open("wb") as f:
            await fetch_resource(base_url + filename, f)

    print(f"Fetched all files referenced in {base_url}")


TASKS = {fetch_sturm_edition: "sturm-edition"}


# cli


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("--skip-existing", "-s", action="store_true")
    return parser.parse_args()


async def main():
    args = parse_args()
    CORPORA.mkdir(exist_ok=True)
    async with asyncio.TaskGroup() as tasks:
        for func, folder in TASKS.items():
            target = CORPORA / folder
            if args.skip_existing and target.exists():
                continue
            target.mkdir(exist_ok=True)
            tasks.create_task(func(target))
    await http_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
