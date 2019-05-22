=========================
arxiv-collector changelog
=========================

.. current developments

v0.3.1
====================

**Added:**



**Changed:**



**Deprecated:**



**Removed:**



**Fixed:**



**Security:**





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



