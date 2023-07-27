from setuptools import setup, find_packages

setup(
    name="tangods_caenfastps",
    version="0.0.1",
    description="Daniel Schick",
    author="dschick@mbi-berlin.de",
    author_email="Tango Device Server for CAEN FastPS Power Supplies",
    python_requires=">=3.6",
    entry_points={"console_scripts": ["CAENFastPS = tangods_caenfastps:main"]},
    license="MIT",
    packages=["tangods_caenfastps"],
    install_requires=[
        "pytango",
    ],
    url="https://github.com/MBI-Div-b/pytango-CAENFastPS",
    keywords=[
        "tango device",
        "tango",
        "pytango",
    ],
)
