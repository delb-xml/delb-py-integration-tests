# the casebooks corpus uses an external, local .dtd file that needs to be
# saved to the top level folder and whose reference needs to be adjusted

import asyncio
import re
from functools import partial
from pathlib import Path
from typing import Final


CWD: Final = Path.cwd().resolve()
ENTITIES_FILE: Final = Path("schema/entities.dtd")


adjust_references: Final = partial(
    re.compile(re.escape(b"../schema/entities.dtd"), flags=re.IGNORECASE).subn,
    b"./entities.dtd",
)


async def normalize_file(file: Path):
    contents, subs = adjust_references(file.read_bytes())
    if subs:
        file.write_bytes(contents)


async def main():
    (CWD / ENTITIES_FILE).rename(CWD / ENTITIES_FILE.name)

    async with asyncio.TaskGroup() as tasks:
        for file in CWD.glob("*.xml"):
            tasks.create_task(normalize_file(file))


if __name__ == "__main__":
    asyncio.run(main())
