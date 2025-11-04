# the papyri corpus contains CR entities (&#xD;) that are implicitly converted to LF
# characters on serialization and that is okay. for example:
#
# <change when="2019-02-26T04:28:22-05:00"
#                  who="http://papyri.info/users/WesselvanDuijn">Submit - Submitted&#xD;
# </change>
#
# it seems to appear in editorial notes only and thus these entities have presumably
# been produced by an editor on Windows OS.

import asyncio
import re
from functools import partial
from pathlib import Path


cr_entity_to_lf_char = partial(re.compile(rb"&#xd;", flags=re.IGNORECASE).subn, b"\n")


async def normalize_file(file: Path):
    contents, subs = cr_entity_to_lf_char(file.read_bytes())
    if subs:
        file.write_bytes(contents)


async def main(files: set[Path]):
    async with asyncio.TaskGroup() as tasks:
        for file in files:
            tasks.create_task(normalize_file(file))
