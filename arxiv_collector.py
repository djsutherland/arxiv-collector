#!/usr/bin/env python
from __future__ import print_function

import collections
from functools import partial
import io
from operator import eq
import os
import re
import subprocess
import sys
import tarfile


__version__ = '0.2.2'


def consume(iterator):
    collections.deque(iterator, maxlen=0)


def target(fname):
    seen_names = {fname}
    while os.path.islink(fname):
        new = os.readlink(fname)
        if new in seen_names:
            raise ValueError("Link cycle detected for {}...".format(fname))
        seen_names.add(new)
        fname = new
    return fname


strip_comment = partial(re.compile(r"(^|[^\\])%.*").sub, r"\1%")


def collect(
    out_tar, base_name="main", packages=("biblatex",), strip_comments=True, verbosity=1
):
    # Use latexmk to:
    #  - make sure we have a good main.bbl file
    #  - figure out which files we actually use (to not include unused figures)
    #  - keep track of which files we use from certain packages
    if verbosity >= 1:
        print("Building {}...".format(base_name))

    proc = subprocess.Popen(
        ["latexmk", "-silent", "-pdf", "-deps", base_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )

    def next_line():
        return proc.stdout.readline().decode()

    def read_until(check):
        while True:
            line = next_line()
            if line == "":
                raise ValueError("Unexpected EOF")
            res = check(line)
            assert res is not NotImplemented
            if res:
                return
            yield line

    def add(path, arcname=None, **kwargs):
        dest = target(path)
        if arcname is None:
            arcname = path

        if not os.path.exists(dest):
            raise OSError("'{}' doesn't exist!".format(path))
        if verbosity >= 2:
            print("Adding {}".format(dest))
            print("    as {}".format(arcname))
        out_tar.add(dest, arcname=arcname, **kwargs)

    pat = "#===Dependents(, and related info,)? for {}:\n".format(re.escape(base_name))
    consume(read_until(re.compile(pat).match))
    assert next_line().strip() == "{}.pdf :\\".format(base_name)

    pkg_re = re.compile("/" + "|".join(re.escape(p) for p in packages) + "/")
    used_bib = False

    end_line = u"#===End dependents for {}:\n".format(base_name)
    for line in read_until(partial(eq, end_line)):
        dep = line.strip()
        if dep.endswith("\\"):
            dep = dep[:-1]

        if verbosity >= 3:
            print("Processing", dep, "...")

        if os.path.isabs(dep):
            if pkg_re.search(dep):
                add(dep, arcname=os.path.basename(dep))
        elif dep.endswith(".tex") and strip_comments:
            with io.open(dep) as f, io.BytesIO() as g:
                info = tarfile.TarInfo(name=dep)
                for line in f:
                    g.write(strip_comment(line).encode("utf-8"))
                info.size = g.tell()
                g.seek(0)
                out_tar.addfile(tarinfo=info, fileobj=g)
        elif dep.endswith(".eps"):
            # arxiv doesn't like epstopdf in subdirectories
            base = dep[:-4]
            add(base + "-eps-converted-to.pdf", arcname=base + ".pdf")
        elif dep.endswith("-eps-converted-to.pdf"):
            # old versions of latexmk output both the converted and the not
            pass
        elif dep.endswith(".bib"):
            used_bib = True
        else:
            add(dep)

    consume(iter(proc.stdout.read, b""))
    proc.wait()

    if proc.returncode:
        print("Build failed! Run   latexmk -pdf {}   to see why.".format(base_name))
        subprocess.check_call(["latexmk", "-C", base_name])
        sys.exit(proc.returncode)

    bbl_pth = "{}.bbl".format(base_name)
    if os.path.exists(bbl_pth):
        add(bbl_pth)
    elif used_bib:
        print(
            "Used a .bib file, but didn't find '{}'; this likely won't work.".format(
                bbl_pth
            )
        )


def main():
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("base_name", nargs="?")
    parser.add_argument("--dest", default="arxiv.tar.gz")

    parser.add_argument(
        "--include-package",
        "-p",
        action="append",
        dest="packages",
        default=["biblatex"],
    )
    parser.add_argument("--skip-biblatex", action="store_true")

    g = parser.add_mutually_exclusive_group()
    g.add_argument(
        "--strip-comments",
        action="store_true",
        default=True,
        help="Strip comments from all .tex files (by default).",
    )
    g.add_argument("--no-strip-comments", action="store_false", dest="strip_comments")

    g = parser.add_mutually_exclusive_group()
    g.add_argument(
        "--verbose", "-v", action="store_const", const=2, dest="verbosity", default=1
    )
    g.add_argument("--quiet", "-q", action="store_const", const=1, dest="verbosity")
    g.add_argument("--debug", action="store_const", const=10, dest="verbosity")

    parser.add_argument(
        "--version", action="version", version="%(prog)s {}".format(__version__)
    )
    args = parser.parse_args()

    if not args.base_name:
        from glob import glob

        cands = [c[:-4] for c in glob("*.tex")]
        if len(cands) > 1:
            cands = list(set(cands) & {"main", "paper"})
        if len(cands) == 1:
            args.base_name = cands[0]
        else:
            parser.error("Can't guess your filename; pass BASE_NAME.")

    if args.base_name.endswith(".tex"):
        args.base_name = args.base_name[:-4]
    if "." in args.base_name:
        parser.error("BASE_NAME ({!r}) shouldn't contain '.'".format(args.base_name))
    if "/" in args.base_name:
        parser.error("cd into the directory first")

    if args.skip_biblatex:
        args.packages.remove("biblatex")

    with tarfile.open(args.dest, mode="w:gz") as t:
        collect(
            t,
            base_name=args.base_name,
            packages=args.packages,
            strip_comments=args.strip_comments,
            verbosity=args.verbosity,
        )
    print("Output in {}".format(args.dest))


if __name__ == "__main__":
    main()
