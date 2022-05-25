**Added:**

* Support for a new ``--exclude-files`` argument (or ``exclude_files`` in the call to ``collect``), which will exclude a pattern of files from the built tarball. Might be useful e.g. for removing figure sources via the ``standalone`` package that won't build on arXiv, but where a pdf is included.
