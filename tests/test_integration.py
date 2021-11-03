# Copyright 2021 Canonical Ltd.
# SPDX-License-Identifier: Apache-2.0
import pytest

TEST_BUNDLE = """
description: An s3 integrator deployment
series: focal

applications:
  s3-integrator:
    charm: {{ charm }}
    num_units: 1
    options:
      s3_endpoint: 's3.amazonaws.com'
      s3_region: 'eu-west-2'
      s3_bucket: 'stg-esm-python-pypi'
"""


@pytest.mark.integration
async def test_build_and_deploy(ops_test, charm_path):
    my_charm = await ops_test.build_charm(charm_path)
    await ops_test.model.deploy(my_charm)
    await ops_test.model.wait_for_idle()


@pytest.mark.integration
async def test_bundle(ops_test, charm_path):
    bundle = ops_test.render_bundle(
        TEST_BUNDLE.strip(), charm=await ops_test.build_charm(charm_path)
    )
    await ops_test.model.deploy(bundle)
    await ops_test.model.wait_for_idle()
    for unit in ops_test.model.units.values():
        assert unit.workload_status == "active"


# workaround for https://github.com/charmed-kubernetes/pytest-operator/issues/26
_, _, __name__ = __name__.rpartition(".")
