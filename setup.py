from setuptools import find_packages, setup


setup(
    name="hca-cli",
    version="0.1.0",
    description="Self-documenting command line client for the Human Cell Atlas API",
    packages=find_packages("src"),
    package_dir={"": "src"},
    package_data={"hca_cli": ["data/*.json"]},
    include_package_data=True,
    python_requires=">=3.11",
    entry_points={"console_scripts": ["hca=hca_cli.cli:main"]},
)
