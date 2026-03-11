from setuptools import setup, find_packages

setup(
    name="minicompiler",
    version="0.1.0",
    description="Educational compiler for a C-like language",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "compiler = src.main:main",  # команда compiler вызовет main() из src/main.py
        ],
    },
    install_requires=[],
    extras_require={
        "dev": ["pytest>=7.0"],
    },
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)