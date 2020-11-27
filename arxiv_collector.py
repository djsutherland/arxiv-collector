#!/usr/bin/env python
from __future__ import print_function

from functools import partial
import io
import os
import random
import re
import string
import subprocess
import sys
import tarfile

__version__ = "0.4.1"

################################################################################
# General helpers


def target(fname):
    seen_names = {fname}
    while os.path.islink(fname):
        new = os.readlink(fname)
        if new in seen_names:
            raise ValueError("Link cycle detected for {}...".format(fname))
        seen_names.add(new)
        fname = new
    return fname


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


def _eat(*args, **kwargs):
    pass


def expect(seen, exp, deps_file):
    if seen.endswith("\n"):
        seen = seen[:-1]
    if seen not in exp:
        msg = "deps file {} seems broken: expected the line\n{}\n  to be {}".format(
            deps_file, seen, ("one of:\n" + "\n".join(exp)) if len(exp) > 1 else exp[0]
        )
        raise ValueError(msg)


def expect_re(seen, pattern, deps_file, error_msg=None):
    if seen.endswith("\n"):
        seen = seen[:-1]
    match = re.match(pattern, seen)
    if not match:
        msg = "deps file {} seems broken: confused by line\n{}".format(deps_file, seen)
        if error_msg is not None:
            msg += error_msg
        raise ValueError(msg)
    return match


strip_comment = partial(re.compile(r"(^|[^\\])%.*").sub, r"\1%")

################################################################################
# Utilities to check and download latexmk


def get_latexmk(version="ctan", dest="latexmk", verbose=True):
    try:
        from urllib.request import urlopen
    except ImportError:
        from urllib2 import urlopen as _urlopen
        from contextlib import closing

        def urlopen(*args, **kwargs):
            return closing(_urlopen(*args, **kwargs))

    import shutil
    import zipfile

    if version.lower() == "ctan":
        url = "http://mirrors.ctan.org/support/latexmk.zip"
    else:
        v = version.replace(".", "")
        url = "http://personal.psu.edu/jcc8/software/latexmk-jcc/latexmk-{}.zip".format(
            v
        )

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


version_re = re.compile(r"Latexmk, John Collins, \d+ \w+\.? \d+\. Version (.*)\s*$")


def get_latexmk_version(latexmk="latexmk"):
    with io.open(os.devnull, "w") as devnull:  # subprocess.DEVNULL is 3.3+
        out = subprocess.check_output([latexmk, "--version"], stderr=devnull).decode()

    match = version_re.search(out)
    if not match:
        raise ValueError("Bad output of {} --version:\n{}".format(latexmk, out))
    return match.group(1)


################################################################################
# Gather the dependency file via latexmk


class LatexmkException(Exception):
    def __init__(self, message, base_error=None):
        super(LatexmkException, self).__init__(message)
        self.base_error = base_error


def get_deps(base_name="main", latexmk="latexmk", deps_file=".deps", verbosity=1):
    # Use latexmk to:
    #  - make sure we have a good main.bbl file
    #  - figure out which files we actually use (to not include unused figures)
    #  - keep track of which files we use from certain packages
    debug = print if verbosity >= 10 else _eat
    lowlevel = print if verbosity >= 3 else _eat

    while os.path.exists(deps_file):
        debug("{} already exists...".format(deps_file))
        deps_file = deps_file + "-" + random.choice(string.ascii_lowercase)

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
        msg = (
            "Build failed with code {}\n".format(e.returncode)
            + "Called {}\n".format(args)
            + "\nOutput was:\n"
            + e.output.decode()
        )
        raise LatexmkException(msg, base_error=e)

    debug(output.decode())
    lowlevel("Dependencies in {}".format(deps_file))

    return deps_file


################################################################################
# Gather everything into a tar file


def collect(
    out_tar,
    deps_file,
    packages=("biblatex",),
    strip_comments=True,
    verbosity=1,
    latexmk="latexmk",
    delete_deps_after=False,
    extract_bib_name=False,
    include_bib=False,
):
    error = partial(print, file=sys.stderr)
    info = print if verbosity >= 2 else _eat
    lowlevel = print if verbosity >= 3 else _eat
    # debug = print if verbosity >= 10 else _eat

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

    with io.open(deps_file, "rt") as f:
        lines = iter(f)

        filename = expect_re(
            next(lines),
            r"#===Dependents(?:, and related info,)? for (.*):$",
            deps_file,
            "Expected to start with '#===Dependents'",
        ).group(1)
        base_name, _ = os.path.splitext(filename)

        output_name = expect_re(
            next(lines),
            r"(.*) :\\$",
            deps_file,
            "Expected something like '{}.pdf :\\'".format(base_name),
        ).group(1)
        jobname, _ = os.path.splitext(output_name)

        info(
            "Deps file {}: source {}, base name {}, output {}, jobname {}".format(
                deps_file, filename, base_name, output_name, jobname
            )
        )

        pkg_re = re.compile("/" + "|".join(re.escape(p) for p in packages) + "/")
        used_bib = False

        end_lines = [
            u"#===End dependents for {}:\n".format(filename),
            u"#===End dependents for {}:\n".format(base_name),
        ]
        for line in lines:
            if line in end_lines:
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
                if include_bib:
                    add(dep)
            else:
                add(dep)
        else:
            # hit end of file without the break...
            expect(line, end_lines, deps_file)

        try:
            bogus = next(lines)
        except StopIteration:
            pass
        else:
            expect(bogus, ["[end of file]"], deps_file)

    bbl_pth = jobname + '.bbl'
    if os.path.exists(bbl_pth):
        add(bbl_pth, arcname = base_name + '.bbl')
    elif used_bib:
        msg = "Used a .bib file, but didn't find '{}'; this likely won't work."
        error(msg.format(bbl_pth))

    if extract_bib_name:
        info("Running biber on {}.bcf...".format(base_name))
        extracted = subprocess.check_output(
            [
                "biber",
                "--output-format=bibtex",
                "-O",
                "-",
                "-q",
                "-q",
                base_name + ".bcf",
            ]
        )
        tarinfo = tarfile.TarInfo(name=extract_bib_name)
        tarinfo.size = len(extracted)
        out_tar.addfile(tarinfo=tarinfo, fileobj=io.BytesIO(extracted))
        info("Adding extracted biblatex file:", extract_bib_name)

    if delete_deps_after:
        os.unlink(deps_file)


################################################################################
# The overall command-line driver


def parse_args():
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
    parser.add_argument(
        "--include-bib",
        action="store_true",
        default=False,
        help="Include all used .bib files, even though arXiv will ignore them.",
    )
    parser.add_argument(
        "--extract-bib",
        metavar="BIB_NAME",
        help=(
            "Include a new .bib file which contains only the used bib entries. "
            "arXiv will ignore this, but you might want it for another reason."
        ),
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
    fetch = parser.add_argument_group("get a latexmk version")
    fetch.add_argument(
        "--get-latexmk", metavar="PATH", help="Fetch the latexmk script to PATH."
    )
    fetch.add_argument(
        "--get-latexmk-version",
        metavar="VERSION",
        default="CTAN",
        help="Version of latexmk to get [default %(default)s].",
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

    op = parser.add_argument_group("compilation options")
    op.add_argument(
        "--latexmk-deps",
        help="Skip latexmk compilation and use the preexisting dependencies file",
    )

    parser.add_argument(
        "--version", action="version", version="%(prog)s {}".format(__version__)
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

    if args.skip_biblatex:
        args.packages.remove("biblatex")

    if not args.latexmk_deps:  # if we need to worry about latexmk stuff...
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

        # guess the base name if necessary
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
            parser.error(
                "BASE_NAME ({!r}) shouldn't contain '.'".format(args.base_name)
            )
        if "/" in args.base_name:
            parser.error("cd into the directory first")

    return args


def main():
    args = parse_args()

    if args.latexmk_deps:
        deps_file = args.latexmk_deps
    else:
        if args.verbosity >= 1:
            print("Building {}...".format(args.base_name))

        try:
            deps_file = get_deps(
                base_name=args.base_name, latexmk=args.latexmk, verbosity=args.verbosity
            )
        except LatexmkException as e:
            print(str(e), file=sys.stderr)
            sys.exit(e.base_error.returncode)

    if args.verbosity >= 1:
        print("Gathering outputs...")

    with tarfile.open(args.dest, mode="w:gz") as t:
        collect(
            out_tar=t,
            deps_file=deps_file,
            packages=args.packages,
            strip_comments=args.strip_comments,
            verbosity=args.verbosity,
            delete_deps_after=not args.latexmk_deps,
            extract_bib_name=args.extract_bib,
            include_bib=args.include_bib,
        )
        n_members = len(t.getmembers())
    sz = sizeof_fmt(os.stat(args.dest).st_size)

    if args.verbosity >= 1:
        print("Output in {}: {} files, {} compressed".format(args.dest, n_members, sz))


if __name__ == "__main__":
    main()
