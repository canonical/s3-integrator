# Contributing to s3-integrator

## Setting up a development environment

1. Clone the repository

```bash
    $ git clone https://github.com/canonical/s3-integrator.git && cd s3-integrator
```

2. Create and activate a virtualenv with the development requirements:

```bash
    $ python -m venv venv
    $ source venv/bin/activate
    $ pip install -e .[dev,tests,lint]
```

3. Before committing changes, install and setup pre-commit to ensure your changes follow the current style of the repository:


```bash
    $ pip install pre-commit && pre-commit install
    $ git commit....
```

## Building the charm

1. Ensure you have installed the latest version of `charmcraft`

```bash
    $ sudo snap install charmcraft --classic
```

2. Pack the charm:

```bash
    $ charmcraft pack
```

## Deploying the charm

1. Simploy deploy the charm via juju:

```bash
    $ juju deploy ./s3-integrator_ubuntu-20.04-amd64.charm
```

## Testing

Testing currently relies on `tox` with `pytest` and `pytest-operator`.

To run non-integration tests, you can use:

```bash
    $ tox -e py
```

For the full integration suite, run:

```bash
    $ tox -e integration
```

To simply do a lint check, run:

```bash
    $ tox -e checklint
```
