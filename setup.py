from setuptools import find_packages, setup

setup(
    name="AsteroidPy",
    version="1.1.3",
    description="A tool for asteroid observation scheduling and analysis",
    url="https://github.com/ziriuz84/asteroidpy",
    author="Sirio Negri",
    author_email="ziriuz84@gmail.com",
    license="GPL v3",
    packages=find_packages("."),
    install_requires=[
        "requests",
        "bs4",
        "configparser",
        "astropy",
        "httpx",
        "astroplan",
        "lxml",
        "astroquery",
        "platformdirs",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GPL v3",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
    entry_points={
        "console_scripts": ["asteroidpy=asteroidpy:main"],
    },
)
