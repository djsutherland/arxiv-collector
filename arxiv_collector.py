#!/usr/bin/env python
from __future__ import print_function

import collections
from functools import partial
import io
import os
import random
import re
import string
import subprocess
import sys
import tarfile


__version__ = "0.3.1"


def target(fname):
    seen_names = {fname}
    while os.path.islink(fname):
        new = os.readlink(fname)
        if new in seen_names:
            raise ValueError("Link cycle detected for {}...".format(fname))
        seen_names.add(new)
        fname = new
    return fname


def get_latexmk(version="4.64a", dest="latexmk", verbose=True):
    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib import urlopen
    import shutil
    import zipfile

    v = version.replace(".", "")
    url = "http://personal.psu.edu/jcc8/software/latexmk-jcc/latexmk-{}.zip".format(v)

    with io.BytesIO() as bio:
        if verbose:
            print("Downloading latexmk {}...".format(version), file=sys.stderr, end="")
        with urlopen(url) as web:
            shutil.copyfileobj(web, bio, length=131072)

        with zipfile.ZipFile(bio) as z:
            for zinfo in z.infolist():
                if os.path.basename(zinfo.filename) == "latexmk.pl":
                    with z.open(zinfo) as script, io.open(dest, "wb") as out:
                        shutil.copyfileobj(script, out)

                    # executable: https://stackoverflow.com/a/30463972/344821
                    mode = os.stat(dest).st_mode
                    mode |= (mode & 0o444) >> 2  # copy R bits to X
                    os.chmod(dest, mode)
                    break
            else:
                raise ValueError("Couldn't find latexmk.pl in {}".format(url))

        if verbose:
            print("saved to `{}`.".format(dest), file=sys.stderr)


version_re = re.compile(r"Latexmk, John Collins, \d+ \w+ \d+\. Version (.*)$")


def get_latexmk_version(latexmk="latexmk"):
    out = subprocess.check_output([latexmk, "--version"], stderr=subprocess.DEVNULL)
    match = version_re.search(out.decode())
    if not match:
        raise ValueError("Bad output of {} --version:\n{}".format(latexmk, out))
    return match.group(1)


# based on https://stackoverflow.com/a/1094933/344821
def sizeof_fmt(num, suffix="B", prec=0, pad=False):
    width = 3 if pad else ""
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return "{:{width}.{prec}f}{}{}".format(
                num, unit, suffix, prec=prec, width=width
            )
        num /= 1024.0
    return "{:.{prec}f}{}{}".format(num, "Yi", suffix, prec=prec)


strip_comment = partial(re.compile(r"(^|[^\\])%.*").sub, r"\1%")


def collect(
    out_tar,
    base_name="main",
    packages=("biblatex",),
    strip_comments=True,
    verbosity=1,
    latexmk="latexmk",
    deps_file=".deps",
):
    def eat(*args, **kwargs):
        pass

    output = partial(print)
    error = partial(print, file=sys.stderr)
    main = output if verbosity >= 1 else eat
    info = output if verbosity >= 2 else eat
    lowlevel = output if verbosity >= 3 else eat
    debug = output if verbosity >= 10 else eat

    while os.path.exists(deps_file):
        deps_file = deps_file + "-" + random.choice(string.ascii_lowercase)

    # Use latexmk to:
    #  - make sure we have a good main.bbl file
    #  - figure out which files we actually use (to not include unused figures)
    #  - keep track of which files we use from certain packages
    main("Building {}...".format(base_name))

    args = [
        latexmk,
        "-silent",
        "-pdf",
        "-deps",
        "-deps-out={}".format(deps_file),
        base_name,
    ]
    debug("Running ", args)
    try:
        output = subprocess.check_output(args, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        error("Build failed with code {}".format(e.returncode))
        error("Called {}".format(args))
        error("\nOutput was:\n" + e.output.decode())
        sys.exit(e.returncode)

    debug(output.decode())

    main("Build complete, gathering outputs...")

    def add(path, arcname=None, **kwargs):
        dest = target(path)
        if arcname is None:
            arcname = path

        if not os.path.exists(dest):
            raise OSError("'{}' doesn't exist!".format(path))
        info("Adding", dest)
        if arcname != dest:
            info("    as", arcname)
        out_tar.add(dest, arcname=arcname, **kwargs)

    def expect(seen, exp):
        if seen.endswith("\n"):
            seen = seen[:-1]
        if seen not in exp:
            msg = "deps file {} seems broken: expected the line\n{}\n  to be {}".format(
                deps_file,
                seen,
                ("one of:\n" + "\n".join(exp)) if len(exp) > 1 else exp[0],
            )
            raise ValueError(msg)

    with io.open(deps_file, "rt") as f:
        lines = iter(f)

        expect(
            next(lines),
            [
                "#===Dependents for {}:".format(base_name),
                "#===Dependents, and related info, for {}:".format(base_name),
            ],
        )
        expect(
            next(lines),
            [
                "{}.pdf :\\".format(base_name),
                "{}.pdf {} :\\".format(base_name, deps_file),
            ],
        )

        pkg_re = re.compile("/" + "|".join(re.escape(p) for p in packages) + "/")
        used_bib = False

        end_line = u"#===End dependents for {}:\n".format(base_name)
        for line in lines:
            if line == end_line:
                break

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
                    info("Adding", dep, "with comments stripped")
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
        else:
            # hit end of file without the break...
            expect(line, [end_line])

        try:
            bogus = next(lines)
        except StopIteration:
            pass
        else:
            expect(bogus, ["[end of file]"])

    bbl_pth = "{}.bbl".format(base_name)
    if os.path.exists(bbl_pth):
        add(bbl_pth)
    elif used_bib:
        msg = "Used a .bib file, but didn't find '{}'; this likely won't work."
        error(msg.format(bbl_pth))

    os.unlink(deps_file)


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
    fetch = parser.add_argument_group("get a latexmk version")
    fetch.add_argument(
        "--get-latexmk", metavar="PATH", help="Fetch the latexmk script to PATH."
    )
    fetch.add_argument(
        "--get-latexmk-version",
        metavar="VERSION",
        default="4.64a",
        help="Version of latexmk to get [default %(default)s].",
    )
    args = parser.parse_args()

    if args.get_latexmk:
        if os.path.exists(args.get_latexmk):
            msg = "Output `{}` already exists; delete it first if you want."
            parser.error(msg.format(args.get_latexmk))
        get_latexmk(
            version=args.get_latexmk_version,
            dest=args.get_latexmk,
            verbose=args.verbosity >= 1,
        )
        parser.exit(0)

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

    # check latexmk version works
    version = get_latexmk_version(args.latexmk)
    if version in {"4.63b", "4.64"}:
        msg = (
            "Your latexmk version ({}) has broken dependency tracking, so it "
            "won't work for us.\n"
            "Use `arxiv-collector --get-latexmk ./latexmk` to get a working "
            "version to the file `./latexmk`, then pass `--latexmk ./latexmk`."
        )
        raise ValueError(msg.format(version))

    with tarfile.open(args.dest, mode="w:gz") as t:
        collect(
            t,
            base_name=args.base_name,
            packages=args.packages,
            strip_comments=args.strip_comments,
            verbosity=args.verbosity,
            latexmk=args.latexmk,
        )
        n_members = len(t.getmembers())
    sz = sizeof_fmt(os.stat(args.dest).st_size)
    print("Output in {}: {} files, {} compressed".format(args.dest, n_members, sz))


if __name__ == "__main__":
    main()
