=========================
arxiv-collector changelog
=========================

.. current developments

v0.4.1
====================



v0.4.0
====================

**Added:**

* You can now pass `--latexmk-deps` to use a pre-made dependencies file. In particular, makes it possible to run directly on Overleaf.
* Option ``--include-bib`` to include ``.bib`` files, from @ryanakca (#14)
* Optino ``--extract-bib NAME`` to run ``biber`` to create a single ``.bib`` file with only the used entries, from @ryanakca (#14)



v0.3.5
====================

**Added:**

* ``--get-latexmk`` now gets the latest version from CTAN by default.

**Fixed:**

* Handle ``latexmk --version`` output for newest version (#11).



v0.3.4
====================

**Fixed:**

* Yet another python 2 error; thanks again, @physikerwelt.



v0.3.3
====================

**Fixed:**

* Fix another python 2 error. (Can people just use 3 already?)



v0.3.2
====================

**Fixed:**

* Fixed ``--get-latexmk`` in python 2.



v0.3.1
====================

**Changed:**

* Default ``--get-latexmk`` to the new 4.64a version, which works again.


v0.3.0
====================

**Added:**

* Check that your `latexmk` isn't a known-broken version.
* `--get-latexmk` utility to easily download an arbitrary `latexmk` version.
* Output number of files and total archive size when done

**Changed:**

* Remove some redundant info from --verbose output.
* Simplify code by using latexmk's ``--deps-out`` option



v0.2.3
====================

**Added:**

* Better ``--help`` output.
* Option to use a non-default ``latexmk`` path

**Changed:**

* Made ``--debug`` more useful (and way louder).

**Fixed:**

* Fixed bug when dependents message isn't the entire line (#8); thanks to @hysikerwelt for reporting.



v0.2.2
====================

**Changed:**

* Formatted with black
* Slightly better error message for non-existing files.

**Fixed:**

None

* Better error handling when the .bbl file doesn't exist
* Fixed errors when filename contains regex special characters



v0.2.1
====================

**Fixed:**

* Handle package inclusion correctly on Windows (#6 -- thanks @ast0815)



v0.2.0
====================

**Added:**

* Options for output verbosity.

**Fixed:**

* Fix Python 2 bug.
* Crash instead of looping forever if there's a cycle of symlinks.


v0.1.1
====================

**Changed:**

* Changed name of package to have `-` instead of `_` (whoops).




v0.1.0
====================

**Changed:**

* Set up on PyPI.



