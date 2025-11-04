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
IGNORED_FILES: Final = {
    # faust-edition; commit fc05c17b989a31df9e6b2e536b81fe4bd6638919
    #
    # Redundantly used xml:id: le
    "transcript ▸ gm_duesseldorf ▸ KK123_20 ▸ 01.xml",
    # Redundantly used xml:id: lb
    "transcript ▸ gsa ▸ 389773 ▸ 0002.xml",
    #
    # papyri; commit 87e35ebd2144e791fa6f1d2c70f9d0d0a91fcfb4
    #
    # Redundantly used xml:id: asteriskos
    "charDecl.xml",
    # xml:id : attribute value pap(B) is not an NCName
    "APD ▸ apd12t.xml",
    # xml:id : attribute value pap(A) is not an NCName
    "APD ▸ apd16t.xml",
    # xml:id : attribute value pap(C) is not an NCName
    "APD ▸ apd17t.xml",
    # xml:id : attribute value pap(D) is not an NCName
    "APD ▸ apd18t.xml",
    # xml:id : attribute value pap(E) is not an NCName
    "APD ▸ apd21t.xml",
    # xml:id : attribute value pap(F) is not an NCName
    "APD ▸ apd22t.xml",
    # xml:id : attribute value pap(G) is not an NCName
    "APD ▸ apd23t.xml",
    # 30:362: mismatched tag
    "APD ▸ apd24t.xml",
    # xml:id : attribute value pap(I) is not an NCName
    "APD ▸ apd25t.xml",
    # xml:id : attribute value pap(K) is not an NCName
    "APD ▸ apd26t.xml",
    # xml:id : attribute value pap(L) is not an NCName
    "APD ▸ apd27t.xml",
    # xml:id : attribute value pap(2) is not an NCName
    "APD ▸ apd32t.xml",
    # 30:557: mismatched tag
    "APD ▸ apd34t.xml",
    # xml:id : attribute value pap(4) is not an NCName
    "APD ▸ apd35t.xml",
    # xml:id : attribute value pap(5) is not an NCName
    "APD ▸ apd36t.xml",
    # xml:id : attribute value pap(6) is not an NCName
    "APD ▸ apd37t.xml",
    # xml:id : attribute value pap(10) is not an NCName
    "APD ▸ apd41t.xml",
    # xml:id : attribute value pap(11) is not an NCName
    "APD ▸ apd42t.xml",
    # xml:id : attribute value pap(13) is not an NCName
    "APD ▸ apd44t.xml",
    # xml:id : attribute value pap(14) is not an NCName
    "APD ▸ apd45t.xml",
    # xml:id : attribute value pap(15) is not an NCName
    "APD ▸ apd46t.xml",
    # xml:id : attribute value pap(16) is not an NCName
    "APD ▸ apd47t.xml",
    # xml:id : attribute value pap(17) is not an NCName
    "APD ▸ apd48t.xml",
    # xml:id : attribute value pap(18) is not an NCName
    "APD ▸ apd49t.xml",
    # xml:id : attribute value pap(21) is not an NCName
    "APD ▸ apd50t.xml",
    # 30:253: mismatched tag
    "APD ▸ apd51t.xml",
    # 30:2233: mismatched tag
    "APD ▸ apd56t.xml",
    # xml:id : attribute value pap(19) is not an NCName
    "APD ▸ apd57t.xml",
    # xml:id : attribute value pap(23new) is not an NCName
    "APD ▸ apd59t.xml",
    # xml:id : attribute value pap(24) is not an NCName
    "APD ▸ apd60t.xml",
    # here, an attribute that contains an URL with one LF as character entity appended;
    # during parsing this gets normalized to an LF character (per XML spec sect. 3.3.3),
    # delb will serialize this as such, but with this representation, the next parsing
    # will then drop it (following the same spec); and this difference leads to
    # failure of the parse-serialize-equality test
    "HGV_meta_EpiDoc ▸ HGV26 ▸ 25169.xml",
    # Invalid character: Char 0x0 out of allowed range
    "HGV_metadata ▸ XML_dump ▸ Glossary.xml",
}


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
            filename = " ▸ ".join(file.relative_to(content_path).parts)
            if filename in IGNORED_FILES:
                file.unlink()
            else:
                files.add(file.rename(corpus_path / filename))

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
