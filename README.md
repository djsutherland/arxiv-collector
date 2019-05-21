A small script to collect your LaTeX files for submission to the arXiv. Install with `pip install arxiv-collector` or `conda install -c conda-forge arxiv-collector`; use with `arxiv-collector [paper.tex]` from your project's main directory.

Main features:

- By default, strips potentially-embarrassing comments from your uploaded `.tex` files.

- Includes the necessary parts of any system package you tell it to upload. By default, this includes biblatex (if you use it) to avoid errors like

> Package biblatex Warning: File '<file>.bbl' is wrong format version

- Only uploads things you actually use: if you have an image you're not including anymore or whatever, doesn't upload it.


Requirements:

- A working installation of [`latexmk`](http://personal.psu.edu/jcc8/software/latexmk/), on your PATH. (This is used to make the `.bbl` file and to track which files are used.)

*NOTE:* `latexmk` versions 4.63b and 4.64, the latest versions as of this writing, have broken dependency tracking, which means `arxiv-collector` won't work with them. Luckily, `latexmk` is just a standalone perl script, so you can download a working version with `arxiv-collector --get-latexmk path/to/output/file`, and either put it in e.g. `~/bin` or pass `--latexmk` to your `arxiv-collector` invocations.


The script has only really been tested on my own projects; let me know if you run into any problems.

Known limitations:

- If you include figures or other files with absolute paths (`\includegraphics{/home/me/wow.png}` instead of `\includegraphics{../wow.png}`), the script will think it's a system file and not include it by default. You can hack it with `--include-packages` to include any directory name in the path.
