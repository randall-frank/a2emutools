Apple 2 Emulator Disk Tools
===========================
|pypi| |python| |MIT| |pre-commit| |black| |isort|

.. |pypi| image:: https://img.shields.io/pypi/v/a2emutools.svg?logo=python&logoColor=white
   :target: https://pypi.org/project/a2emutools

.. |python| image:: https://img.shields.io/pypi/pyversions/a2emutools?logo=python
   :target: https://pypi.org/project/a2emutools

.. |MIT| image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://opensource.org/licenses/MIT

.. |black| image:: https://img.shields.io/badge/code_style-black-000000.svg
   :target: https://github.com/psf/black

.. |isort| image:: https://img.shields.io/badge/imports-isort-%231674b1.svg?style=flat&labelColor=ef8336
   :target: https://pycqa.github.io/isort/

.. |pre-commit| image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
   :target: https://github.com/pre-commit/pre-commit

.. |title| image:: https://s3.amazonaws.com/www3.ensight.com/build/media/pyensight_title.png


Overview
--------
`a2emutools` is TODO

Documentation and Issues
------------------------
Documentation for the latest stable release is hosted at
`documentation <https://ensight.docs.pyansys.com/version/stable/>`_.

Installation
------------
Two modes of installation are available:

- User installation
- Developer installation

User installation
~~~~~~~~~~~~~~~~~
Install the latest release from `PyPI <https://pypi.org/project/a2emutools/>`_
with this command:

.. code::

   pip install a2emutools


Developer installation
~~~~~~~~~~~~~~~~~~~~~~
If you plan on doing local `a2emutools` *development*, consider
using a `virtual environment <https://docs.python.org/3/library/venv.html>`_.

To clone a2emutools and then install it in a virtual environment, run these
commands:

.. code::

   git clone https://github.com/randall-frank/a2emutools
   cd a2emutools
   pip install virtualenv
   virtualenv venv  # create virtual environment
   source venv/bin/activate  # (.\venv\Scripts\activate for Windows shell)
   pip install .[dev]   # install development dependencies

A developer installation allows you to edit `a2emutools` files locally.
Any changes that you make are reflected in your setup after restarting the
Python kernel.

To build and install `a2emutools`, run these commands:

.. code::

   python -m build   # build
   # this will replace the editable install done previously. If you don't want to replace,
   # switch your virtual environments to test the new install separately.
   pip install .[tests]   # install test dependencies
   pytest  # Run the tests

Pre-commit setup
----------------

``pre-commit`` is a multi-language package manager for pre-commit hooks.


To install pre-commit into your git hooks, run this command:

.. code::

   pre-commit install

``pre-commit`` then runs on every commit. Each time you clone a project,
installing ``pre-commit`` should always be the first action that you take.

If you want to manually run all pre-commit hooks on a repository, run this
command:

.. code::

   pre-commit run --all-files

A bunch of formatters run on your source files.

To run individual hooks, use this command, where ``<hook_id>`` is obtained from
from the ``.pre-commit-config.yaml`` file:

.. code::

   pre-commit run <hook_id>

The first time pre-commit runs on a file, it automatically downloads, installs,
and runs the hook.


Usage
-----
You can use this code to start the simplest PyEnSight session:

.. code:: python

   >>> from ansys.pyensight.core import LocalLauncher
   >>> session = LocalLauncher().start()
   >>> data = session.render(1920, 1080, aa=4)
   >>> with open("image.png", "wb") as f:
   ...    f.write(data)


Optionally, EnSight can work with an EnSight Docker container using code like this:

.. code:: python

   >>> from ansys.pyensight.core import DockerLauncher
   >>> launcher = DockerLauncher(data_directory="d:/data", use_dev=True)
   >>> launcher.pull()
   >>> session = launcher.start()
   >>> data = session.render(1920, 1080, aa=4)
   >>> with open("image.png", "wb") as f:
   ...    f.write(data)


In the preceding code, the ``data_directory`` argument specifies the host directory
to map into the container at the mount point, providing access to the data within
the container. This provides a method for EnSight running in the container to access
the host's file system to read or write data. The optional ``use_dev=True`` argument
specifies that the latest development version of EnSight should be used.

Also, PyEnSight can be launched as other PyAnsys products with the ``launch_ensight`` method:

.. code:: python

   >>> from ansys.pyensight.core import launch_ensight
   >>> session = launch_ensight(use_sos=3)
   >>> data = session.render(1920, 1080, aa=4)
   >>> with open("image.png", "wb") as f:
   ...    f.write(data)


Documentation and Issues
------------------------
Please see the latest release `documentation <https://ensight.docs.pyansys.com/>`_
page for more details.

Please feel free to post issues and other questions at `PyEnSight Issues
<https://github.com/randall-frank/a2emutools/issues>`_. This is the best place
to post questions and code.

License
-------
`a2emutools` is licensed under the MIT license.
