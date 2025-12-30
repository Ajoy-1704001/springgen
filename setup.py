from setuptools import setup, find_packages

setup(
    name="springgen",
    version="1.0.2",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pyfiglet",
        "termcolor",
        "jinja2",
        "pyyaml"
    ],
    entry_points={
        "console_scripts": [
            "springgen=springgen.springgen:main",
        ],
    },
    python_requires=">=3.8",
    description="Interactive Spring Boot CRUD CLI",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Ajoy Deb Nath",
    url="https://github.com/Ajoy-1704001/springgen",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
    ]
)
