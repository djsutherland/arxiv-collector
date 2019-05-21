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


__version__ = "0.2.3"


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
    out_tar,
    base_name="main",
    packages=("biblatex",),
    strip_comments=True,
    verbosity=1,
    latexmk="latexmk",
):
    def eat(*args, **kwargs):
        pass

    output = partial(print, file=sys.stderr)
    error = output
    main = output if verbosity >= 1 else eat
    info = output if verbosity >= 2 else eat
    lowlevel = output if verbosity >= 3 else eat
    debug = output if verbosity >= 10 else eat

    # Use latexmk to:
    #  - make sure we have a good main.bbl file
    #  - figure out which files we actually use (to not include unused figures)
    #  - keep track of which files we use from certain packages
    main("Building {}...".format(base_name))

    args = [latexmk, "-silent", "-pdf", "-deps", base_name]
    debug("Running ", args)
    proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1
    )

    def next_line():
        s = proc.stdout.readline().decode()
        if s:
            debug("(latexmk)\t" + s, end="")
        return s

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
        info("Adding", dest, "\n    as", arcname)
        out_tar.add(dest, arcname=arcname, **kwargs)

    pat = "#===Dependents(, and related info,)? for {}:\n".format(re.escape(base_name))
    consume(read_until(re.compile(pat).search))
    assert next_line().strip() == "{}.pdf :\\".format(base_name)

    pkg_re = re.compile("/" + "|".join(re.escape(p) for p in packages) + "/")
    used_bib = False

    end_line = u"#===End dependents for {}:\n".format(base_name)
    for line in read_until(partial(eq, end_line)):
        dep = line.strip()
        if dep.endswith("\\"):
            dep = dep[:-1]

        lowlevel("Processing", dep, "...")

        if os.path.isabs(dep):
            if pkg_re.search(dep):
                add(dep, arcname=os.path.basename(dep))
        elif dep.endswith(".tex") and strip_comments:
            with io.open(dep) as f, io.BytesIO() as g:
                tarinfo = tarfile.TarInfo(name=dep)
                for line in f:
                    g.write(strip_comment(line).encode("utf-8"))
                tarinfo.size = g.tell()
                g.seek(0)
                out_tar.addfile(tarinfo=tarinfo, fileobj=g)
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
        msg = "Build failed! Run   latexmk -pdf {}   to see why."
        error(msg.format(base_name))
        subprocess.check_call(["latexmk", "-C", base_name])
        sys.exit(proc.returncode)

    bbl_pth = "{}.bbl".format(base_name)
    if os.path.exists(bbl_pth):
        add(bbl_pth)
    elif used_bib:
        msg = "Used a .bib file, but didn't find '{}'; this likely won't work."
        error(msg.format(bbl_pth))


def main():
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "base_name",
        nargs="?",
        help="Name of the main tex file; default tries to guess.",
    )
    parser.add_argument(
        "--dest", default="arxiv.tar.gz", help="Output path [default: %(default)s]."
    )

    pkgs = parser.add_argument_group("packages to include")
    pkgs.add_argument(
        "--include-package",
        "-p",
        action="append",
        dest="packages",
        default=["biblatex"],
        help=(
            "Include a system package in the collection if used; can pass more "
            "than once. Default is only biblatex."
        ),
    )
    pkgs.add_argument(
        "--skip-biblatex",
        action="store_true",
        help="Don't include biblatex even if it's used.",
    )

    parser.add_argument(
        "--latexmk",
        default="latexmk",
        help="Path to the latexmk command [default: %(default)s].",
    )

    contents = parser.add_argument_group("content options")
    g = contents.add_mutually_exclusive_group()
    g.add_argument(
        "--strip-comments",
        action="store_true",
        default=True,
        help="Strip comments from all .tex files (by default).",
    )
    g.add_argument(
        "--no-strip-comments",
        action="store_false",
        dest="strip_comments",
        help="Don't strip comments from any .tex files.",
    )

    output = parser.add_argument_group("output options")
    g = output.add_mutually_exclusive_group()
    opt = partial(g.add_argument, action="store_const", dest="verbosity")
    opt("--verbose", "-v", const=2, default=1, help="Include some extra output.")
    opt("--quiet", "-q", const=1, help="Default amount of verbosity.")
    opt("--silent", const=0, help="Only print error messages.")
    opt("--debug", const=10, help="Print lots and lots of output.")

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
            latexmk=args.latexmk,
        )
    print("Output in {}".format(args.dest))


if __name__ == "__main__":
    main()
