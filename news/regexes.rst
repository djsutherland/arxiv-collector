**Added:**

* Support for general line-wise regex replacements in ``.tex`` files, instead of only stripping comments.

**Changed:**

* The API for ``collect`` has changed: rather than the boolean ``strip_comments`` argument, use ``tex_replace=[STRIP_COMMENTS]`` or ``tex_replace=[]``. The default behavior is still to strip comments.
