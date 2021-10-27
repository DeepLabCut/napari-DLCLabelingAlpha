from pathlib import Path
from setuptools import setup, find_packages


requirements = []
root = Path(__file__).parent
filename = str(root / "requirements.txt")
with open(filename) as f:
    for line in f:
        stripped = line.split("#")[0].strip()
        if len(stripped) > 0:
            requirements.append(stripped)


setup(
    name="napari-DeepLabCut",
    version="0.0.1",
    maintainer="Jessy Lauer",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=requirements,
    setup_requires=["setuptools_scm"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Framework :: napari",
        "Intended Audience :: Science/Research",
        "Development Status :: 3 - Alpha",
    ],
    entry_points={
        "napari.plugin": [
            "napari_dlc = dlclabel.napari_dlc",
        ],
    },
)
