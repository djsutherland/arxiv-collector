A small script to collect your LaTeX files for submission to the arXiv. Particularly useful if you use biblatex, and you can [use it directly on Overleaf](#using-directly-on-overleaf).

## Usage

Install with `pip install arxiv-collector` or `conda install -c conda-forge arxiv-collector` – or just download [`arxiv_collector.py`](arxiv_collector.py), it's a stand-alone script with no dependencies. Works with any reasonable version of Python 3, or 2.7 if you really must.

Use with `arxiv-collector` from your project's main directory, or `arxiv-collector file.tex` if you have more than one `.tex` file and it can't guess correctly which one to use; `arxiv-collector --help` for more.


## Main features:

- By default, strips potentially-embarrassing comments from your uploaded `.tex` files. (Use `--no-strip-comments` to turn this off; it's based on a regular expression, and it's definitely possible for it to screw up, especially if you use `%` in a `verbatim` block or something.)

- Includes the necessary parts of any system package you tell it to upload. By default, this includes biblatex (if you use it) to avoid errors like

> Package biblatex Warning: File '<file>.bbl' is wrong format version

- Only uploads things you actually use: if you have an image you're not including anymore or whatever, doesn't upload it.


## Requirements:

- A working installation of [`latexmk`](http://personal.psu.edu/jcc8/software/latexmk/), on your PATH. (This is used to make the `.bbl` file and to track which files are used.)
  - If you have working TeX and Perl installations, you likely already have `latexmk` even if you don't use it. If you don't, you can either install it the "normal" way (`tmlgr install latexmk`, `apt-get install latexmk`, ...), or just grab the script with `arxiv-collector --get-latexmk path/to/output/latexmk`.
  - If `latexmk` isn't on your PATH for whatever reason, add `--latexmk ./path/to/latexmk` to your `arxiv-collector` call.
  - **NOTE:** `latexmk` version 4.63b has broken dependency tracking, which means `arxiv-collector` won't work with it. You can either update it with your package manager, or you can get a working version, e.g. 4.64a, with `arxiv-collector --get-latexmk path/to/output/latexmk`, and either put it in e.g. `~/bin` or pass `--latexmk` to your `arxiv-collector` invocations.


## Caveats

The script may or may not work if you do something weird with your project layout / etc; always check that the arXiv output pdf looks right. [Let me know](https://github.com/djsutherland/arxiv-collector/issues/new) if you run into any problems, including a copy of the not-working project if possible.

In particular, if you include figures or other files with absolute paths (`\includegraphics{/home/me/wow.png}` instead of `\includegraphics{../wow.png}`), the script will think it's a system file and not include it by default. You can hack it with `--include-packages` to include any directory name in the path.


## Using directly on Overleaf

It's easy to set up Overleaf to run the script on each compilation, so that you're always ready to upload to arXiv at a moment's notice! (You can of course comment out or remove the lines below after running it once, but it shouldn't add much overhead to just do it every time.)

First, add `arxiv_collector.py` to your project. You can do "New file", "From external url", then put in `https://raw.githubusercontent.com/djsutherland/arxiv-collector/master/arxiv_collector.py`.

Now, [add a file called `.latexmkrc`](https://www.overleaf.com/learn/latex/Articles%2FHow_to_use_latexmkrc_with_Overleaf:_examples_and_techniques) if you don't have one already. This is a control file that tells `latexmk` how to compile your project (which is what Overleaf uses behind the scenes). If you use something slightly complicated like an index or a glossary, you might need to add in [Overleaf's default settings file](https://www.overleaf.com/learn/how-to/How_does_Overleaf_compile_my_project%3F), which this will override, but for 95% of projects you don't need to worry about this.

Add to the `.latexmkrc` file (whether you're starting from blank or from Overleaf's default, doesn't matter) the following contents:
```
$dependents_list = 1;
$deps_file = ".deps";

END {
  system("python arxiv_collector.py --latexmk-deps $deps_file");
}
```

Now, after you compile, you can download `arxiv.tar.gz` by clicking on the blue page icon to the right of the big green Recompile button ("Logs and output files"), clicking on "Other logs & files", then choosing `arxiv.tar.gz`. Upload that file to the arXiv, and you should be good!
