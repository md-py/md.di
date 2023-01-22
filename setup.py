import setuptools


with open('readme.md') as fh:
    long_description = fh.read()

setuptools.setup(
    name='md.di',
    version='0.1.0',
    description='Dependency injection container & tools',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='License :: OSI Approved :: MIT License',
    package_dir={'': 'lib/'},
    packages=['md.di'],
    install_requires=['md.python==1.*', 'psr.container==1.*'],
    dependency_links=[
        'https://source.md.land/python/md-python/'
        'https://source.md.land/python/psr-container/'
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
