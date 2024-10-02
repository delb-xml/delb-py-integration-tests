from pathlib import Path


CORPORA = Path(__file__).parent
ELTEC = CORPORA / "ELTeC"
SUBMODULES = CORPORA.parent / "git-submodules"


def main():
    ELTEC.mkdir(exist_ok=True, parents=True)

    for directory in (CORPORA, ELTEC):
        for link in (p for p in directory.iterdir() if p.is_symlink()):
            link.unlink()

    for submodule in (p for p in SUBMODULES.iterdir() if p.is_dir()):
        if submodule.name.startswith("ELTeC-"):
            link = CORPORA / "ELTeC" / submodule.name.removeprefix("ELTeC-")
        else:
            link = CORPORA / submodule.name

        link.symlink_to(submodule)


if __name__ == "__main__":
    main()
