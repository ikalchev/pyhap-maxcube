from setuptools import setup

with open('README.md', 'r', encoding='utf-8') as fp:
    long_description = fp.read()

setup(
    name='pyhap-maxcube',
    description='HAP-python Accessories for e-Q3 MAX! devices.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Ivan Kalchev',
    version='0.5',
    url='https://github.com/ikalchev/pyhap-maxcube',
    classifiers=[
        'Development Status :: 5 - Beta',
        'Programming Language :: Python :: 3',
        'Operating System :: Linux',
        'Topic :: Home Automation',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: Apache Software License',
        'Intended Audience :: Developers',
    ],
    license='Apache-2.0',
    packages=[
        'pyhap.accessories.maxcube',
    ],
    install_requires=[
        'HAP-python >= 2.0.0',
        'maxcube-api >= 0.1.0',
    ],
)
