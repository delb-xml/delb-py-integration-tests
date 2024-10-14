import asyncio
from argparse import Namespace
from contextlib import chdir
from importlib import import_module
from pathlib import Path
from subprocess import DEVNULL, run
from typing import Final

from dit.commons import SUBMODULES_PATH

COMMIT_MESSAGE: Final = "Filtered and normalized for usage with delb integration tests"
CONTENT_ROOTS: Final = {
    "casebooks": "cases",
    "disco": "tei/all-periods-per-author",
    "ELTeC-cze": "level1",
    "ELTeC-deu": "level1",
    "ELTeC-eng": "level1",
    "ELTeC-eng-ext": "level1",
    "ELTeC-fra": "level1",
    "ELTeC-fra-ext1": "level1",
    "ELTeC-fra-ext2": "level1",
    "ELTeC-gre": "level1",
    "ELTeC-gsw": "level0",
    "ELTeC-hrv": "level1",
    "ELTeC-hun": "level1",
    "ELTeC-ita": "level1",
    "ELTeC-lav": "level1",
    "ELTeC-lit": "level1",
    "ELTeC-lit-ext": "level1",
    "ELTeC-nor": "level2",
    "ELTeC-pol": "level1",
    "ELTeC-por": "level1",
    "ELTeC-por-ext": "level1",
    "ELTeC-rom": "level1",
    "ELTeC-rus": "level0",
    "ELTeC-slv": "level1",
    "ELTeC-spa": "level1",
    "ELTeC-srp": "level1",
    "ELTeC-srp-ext": "level1",
    "ELTeC-swe": "level1",
    "ELTeC-ukr": "level1",
    "faust-edition": "xml",
    "medieval-manuscripts-oxford": "collections",
    "ride": "tei_all",
}
FILE_SIZE_LIMIT: Final = 10 * 1024**2
GIT_BRANCH: Final = "delb-integration-tests"


async def normalize_submodule(corpus_path: Path):
    name = corpus_path.name

    # ensure git worktree is clean
    git_diff_result = run(["git", "diff", "--quiet", "--exit-code"], cwd=corpus_path)
    if git_diff_result.returncode != 0:
        print(f"ERROR: {name} has uncommited changes.")
        return

    # switch to designated branch
    if matching_branches := run(
        ["git", "branch", "--list", GIT_BRANCH], capture_output=True, cwd=corpus_path
    ).stdout:
        if matching_branches.startswith(b"*"):
            print(f"WARNING: {name} has branch '{GIT_BRANCH}' checked out. Skipping.")
            return
        else:
            run(
                ["git", "branch", "--delete", "--force", GIT_BRANCH], cwd=corpus_path
            ).check_returncode()

    run(["git", "clean", "--force"], cwd=corpus_path, stdout=DEVNULL).check_returncode()
    run(["git", "switch", "--create", GIT_BRANCH], cwd=corpus_path).check_returncode()

    # flatten the desired file tree
    if root := CONTENT_ROOTS.get(name):
        content_path = corpus_path / root
    else:
        content_path = corpus_path

    files: set[Path] = set()
    for dirpath, _, filenames in content_path.walk():
        for file in (
            path
            for path in (dirpath / n for n in filenames if n.endswith(".xml"))
            if path.stat().st_size < FILE_SIZE_LIMIT
        ):
            files.add(
                file.rename(
                    corpus_path / " ▸ ".join(file.relative_to(content_path).parts)
                )
            )

    # apply corpus specific filtering and normalization
    try:
        module = import_module(f"{__name__}.{name}")
    except ModuleNotFoundError:
        pass
    else:
        with chdir(corpus_path):
            await getattr(module, "main")(files)

    # remove unneeded files and commit
    await clean_corpus_folder(corpus_path)
    run(["git", "add", "--all"], cwd=corpus_path).check_returncode()
    run(
        ["git", "commit", "--all", f"--message={COMMIT_MESSAGE}"],
        cwd=corpus_path,
        stdout=DEVNULL,
    ).check_returncode()


async def clean_corpus_folder(corpus_path: Path):
    # remove all subfolders and their contents
    for dirpath, directories, files in corpus_path.walk(top_down=False):
        for directory in (dirpath / p for p in directories):
            directory.rmdir()

        if dirpath == corpus_path:
            continue

        for file in (dirpath / p for p in files):
            file.unlink()

    # remove all unneeded files
    for item in corpus_path.iterdir():
        if not item.is_file():
            print(f"CRITICAL: Unexpected object: '{item}'")
            continue

        if (
            item.suffix not in (".xml", ".dtd")
            or item.stat().st_size >= FILE_SIZE_LIMIT  # noqa: W503
        ) and item.name != ".git":
            item.unlink()


async def normalize_submodules(args: Namespace):
    submodules = [p.name for p in SUBMODULES_PATH.iterdir() if p.is_dir()]
    if args.submodule:
        submodules = [d for d in submodules if d in args.submodule]

    async with asyncio.TaskGroup() as tasks:
        for submodule in submodules:
            tasks.create_task(normalize_submodule(SUBMODULES_PATH / submodule))


def cmd_normalize(args):
    asyncio.run(normalize_submodules(args))
