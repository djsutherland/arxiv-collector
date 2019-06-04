A small script to collect your LaTeX files for submission to the arXiv. Install with `pip install arxiv-collector` or `conda install -c conda-forge arxiv-collector`; use with `arxiv-collector [paper.tex]` from your project's main directory.

Main features:

- By default, strips potentially-embarrassing comments from your uploaded `.tex` files.

- Includes the necessary parts of any system package you tell it to upload. By default, this includes biblatex (if you use it) to avoid errors like

> Package biblatex Warning: File '<file>.bbl' is wrong format version

- Only uploads things you actually use: if you have an image you're not including anymore or whatever, doesn't upload it.


Requirements:

- A working installation of [`latexmk`](http://personal.psu.edu/jcc8/software/latexmk/), on your PATH. (This is used to make the `.bbl` file and to track which files are used.)
  - If you have working TeX and Perl installations, you likely already have latexmk even if you don't use it. If you don't, you can either install latexmk the "normal" way (e.g. `tmlgr install latexmk`, `apt-get install latexmk`, ...), or just grab the standalone script with `arxiv-collector --get-latexmk path/to/output/latexmk`.
  - If `latexmk` isn't on your PATH for whatever reason, add `--latexmk ./path/to/latexmk` to your `arxiv-collector` call.
  - **NOTE:** `latexmk` version 4.63b has broken dependency tracking, which means `arxiv-collector` won't work with it. You can either update it with your package manager, or you can get a working version, e.g. 4.64a, with `arxiv-collector --get-latexmk path/to/output/latexmk`, and either put it in e.g. `~/bin` or pass `--latexmk` to your `arxiv-collector` invocations.


The script may or may not work if you do something weird with your tex project layout / etc; always check the arXiv output pdf looks reasonable. [Let me know](https://github.com/dougalsutherland/arxiv-collector/issues/new) if you run into any problems, including a copy of the not-working project if possible.

Known limitations:

- If you include figures or other files with absolute paths (`\includegraphics{/home/me/wow.png}` instead of `\includegraphics{../wow.png}`), the script will think it's a system file and not include it by default. You can hack it with `--include-packages` to include any directory name in the path.
