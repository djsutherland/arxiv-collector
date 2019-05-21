from setuptools import setup

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="arxiv-collector",
    version="0.3.0",
    author="Dougal J. Sutherland",
    author_email="dougal@gmail.com",
    description="A small script to collect LaTeX sources for upload to the arXiv",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dougalsutherland/arxiv-collector",
    py_modules=["arxiv_collector"],
    entry_points={"console_scripts": ["arxiv-collector = arxiv_collector:main"]},
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
    ],
)
