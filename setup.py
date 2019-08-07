from setuptools import setup
setup(
    name='cranlock',
    version='0.0.1',
    license="BSD-3-Clause",
    packages=['cranlock'],
    package_data={
        'cranlock': ['get_package_versions.sh', 'list_dependencies.R']
    },
    entry_points={
        'console_scripts': [
            'cranlock = cranlock.main:main',
        ]
    },
    install_requires=[
        'requests',
        'bs4'
    ],
)
