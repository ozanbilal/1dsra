from setuptools import setup, find_packages

setup(
    name="dsra1d",
    version="0.1.0",
    packages=find_packages(),
    package_data={
        "dsra1d.web": ["static/*", "static/vendor/*", "static/modules/*"],
    },
)
