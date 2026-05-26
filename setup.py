from setuptools import setup, find_packages
import os

# Read requirements
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="pokemon-card-game",
    version="1.0.0",
    packages=find_packages(),
    py_modules=["main", "train", "quickstart"],
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "pokemon-card-game=main:cli",
        ]
    },
    description="Pokémon Card Game - ML Edition",
    author="Your Name",
    url="https://github.com/YOUR_USERNAME/pokemon-card-game",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
