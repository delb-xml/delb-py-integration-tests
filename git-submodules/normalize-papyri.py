# the casebooks corpus uses an external, local .dtd file that needs to be saved to
# the top level folder and whose reference needs to be adjusted

import asyncio
import re
from functools import partial
from pathlib import Path
from typing import Final


CWD: Final = Path.cwd().resolve()


cr_ent_to_lf = partial(re.compile(re.escape(b"&#xd;"), flags=re.IGNORECASE).subn, b"\n")


async def normalize_file(file: Path):
    contents, subs = cr_ent_to_lf(file.read_bytes())
    if subs:
        file.write_bytes(contents)


async def main():
    async with asyncio.TaskGroup() as tasks:
        for file in CWD.glob("*.xml"):
            tasks.create_task(normalize_file(file))


if __name__ == "__main__":
    asyncio.run(main())
