#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.
import asyncio
import base64
import json
import logging
from pathlib import Path

import pytest
import yaml
from pytest_operator.plugin import OpsTest

from .helpers import (
    fetch_action_get_connection_info,
    fetch_action_sync_s3_credentials,
    get_application_data,
    get_certificate_from_file,
    get_relation_data,
    is_relation_broken,
    is_relation_joined,
)

logger = logging.getLogger(__name__)

S3_METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
S3_APP_NAME = S3_METADATA["name"]

APP_METADATA = yaml.safe_load(
    Path("./tests/integration/application-charm/metadata.yaml").read_text()
)
APPLICATION_APP_NAME = APP_METADATA["name"]

APPS = [S3_APP_NAME, APPLICATION_APP_NAME]
FIRST_RELATION = "first-s3-credentials"
SECOND_RELATION = "second-s3-credentials"


@pytest.mark.abort_on_fail
@pytest.mark.skip_if_deployed
async def test_build_and_deploy(ops_test: OpsTest):
    """Build the charm and deploy 1 units for provider and requirer charm."""
    # Build and deploy charm from local source folder
    s3_charm = await ops_test.build_charm(".")
    app_charm = await ops_test.build_charm("./tests/integration/application-charm/")

    await asyncio.gather(
        ops_test.model.deploy(s3_charm, application_name=S3_APP_NAME, num_units=1),
        ops_test.model.deploy(app_charm, application_name=APPLICATION_APP_NAME, num_units=1),
    )
    # Reduce the update_status frequency until the cluster is deployed
    async with ops_test.fast_forward():
        await ops_test.model.block_until(
            lambda: len(ops_test.model.applications[S3_APP_NAME].units) == 1
        )

        await ops_test.model.block_until(
            lambda: len(ops_test.model.applications[APPLICATION_APP_NAME].units) == 1
        )
        await asyncio.gather(
            ops_test.model.wait_for_idle(
                apps=[S3_APP_NAME],
                status="blocked",
                timeout=1000,
            ),
            ops_test.model.wait_for_idle(
                apps=[APPLICATION_APP_NAME],
                status="waiting",
                raise_on_blocked=True,
                timeout=1000,
            ),
        )

    assert len(ops_test.model.applications[S3_APP_NAME].units) == 1

    for unit in ops_test.model.applications[S3_APP_NAME].units:
        assert unit.workload_status == "blocked"

    assert len(ops_test.model.applications[APPLICATION_APP_NAME].units) == 1


@pytest.mark.abort_on_fail
async def test_sync_credential_action(ops_test: OpsTest):
    """Tests the correct output of actions."""
    s3_integrator_unit = ops_test.model.applications[S3_APP_NAME].units[0]
    action = await s3_integrator_unit.run_action(action_name="get-s3-credentials")
    result = await action.wait()
    assert result.status == "failed"

    access_key = "test-access-key"
    secret_key = "test-secret-key"

    action_result = await fetch_action_sync_s3_credentials(
        s3_integrator_unit, access_key=access_key, secret_key=secret_key
    )

    # test the correct status of the charm
    async with ops_test.fast_forward():
        await ops_test.model.wait_for_idle(apps=[S3_APP_NAME], status="active")

    assert action_result["ok"] == "Credentials successfully updated."

    connection_info = await fetch_action_get_connection_info(s3_integrator_unit)
    assert connection_info["access-key"] == "************"
    assert connection_info["secret-key"] == "************"

    # checks for another update of of the credentials
    updated_secret_key = "new-test-secret-key"
    action_result = await fetch_action_sync_s3_credentials(
        s3_integrator_unit, access_key=access_key, secret_key=updated_secret_key
    )

    async with ops_test.fast_forward():
        await ops_test.model.wait_for_idle(apps=[S3_APP_NAME], status="active")

    # check that secret key has been updated
    assert action_result["ok"] == "Credentials successfully updated."

    connection_info = await fetch_action_get_connection_info(s3_integrator_unit)
    assert connection_info["access-key"] == "************"
    assert connection_info["secret-key"] == "************"


@pytest.mark.abort_on_fail
async def test_config_options(ops_test: OpsTest):
    """Tests the correct handling of configuration parameters."""
    # test tls-ca-chain
    ca_chain = get_certificate_from_file("tests/ca_chain.pem")
    ca_chain_bytes = base64.b64encode(ca_chain.encode("utf-8"))
    configuration_parameters = {
        "tls-ca-chain": ca_chain_bytes.decode("utf-8"),
        "s3-api-version": "1.0",
        "storage-class": "cinder",
        "attributes": "a1:v1, a2:v2, a3:v3",
        "path": "/test/path_1/",
        "region": "us-east-2",
        "endpoint": "s3.amazonaws.com",
    }
    # apply new configuration options
    await ops_test.model.applications[S3_APP_NAME].set_config(configuration_parameters)
    # wait for active status
    await ops_test.model.wait_for_idle(apps=[S3_APP_NAME], status="active")
    # test the returns
    s3_integrator_unit = ops_test.model.applications[S3_APP_NAME].units[0]
    action = await s3_integrator_unit.run_action(action_name="get-s3-connection-info")
    action_result = await action.wait()
    configured_options = action_result.results
    # test the correctness of the configuration fields
    assert configured_options["storage-class"] == "cinder"
    assert configured_options["s3-api-version"] == "1.0"
    assert len(json.loads(configured_options["attributes"])) == 3
    assert len(json.loads(configured_options["tls-ca-chain"])) == 2
    assert configured_options["region"] == "us-east-2"
    assert configured_options["path"] == "/test/path_1/"
    assert configured_options["endpoint"] == "s3.amazonaws.com"


@pytest.mark.abort_on_fail
async def test_relation_creation(ops_test: OpsTest):
    """Relate charms and wait for the expected changes in status."""
    await ops_test.model.add_relation(S3_APP_NAME, f"{APPLICATION_APP_NAME}:{FIRST_RELATION}")

    async with ops_test.fast_forward():
        await ops_test.model.block_until(
            lambda: is_relation_joined(ops_test, FIRST_RELATION, FIRST_RELATION)
            == True  # noqa: E712
        )

        await ops_test.model.wait_for_idle(apps=APPS, status="active")
    await ops_test.model.wait_for_idle(apps=APPS, status="active")
    # test the content of the relation data bag

    relation_data = await get_relation_data(ops_test, APPLICATION_APP_NAME, FIRST_RELATION)
    application_data = await get_application_data(ops_test, APPLICATION_APP_NAME, FIRST_RELATION)
    # check if the different parameters correspond to expected ones.
    relation_id = relation_data[0]["relation-id"]
    # check correctness for some fields
    assert "access-key" in application_data
    assert "secret-key" in application_data
    assert "bucket" in application_data
    assert application_data["bucket"] == f"relation-{relation_id}"
    assert application_data["access-key"] == "test-access-key"
    assert application_data["secret-key"] == "new-test-secret-key"
    assert application_data["storage-class"] == "cinder"
    assert application_data["s3-api-version"] == "1.0"
    assert len(json.loads(application_data["attributes"])) == 3
    assert len(json.loads(application_data["tls-ca-chain"])) == 2
    assert application_data["region"] == "us-east-2"
    assert application_data["path"] == "/test/path_1/"

    # update bucket name and check if the change is propagated in the relation databag
    new_bucket_name = "new-bucket-name"
    params = {"bucket": new_bucket_name}
    await ops_test.model.applications[S3_APP_NAME].set_config(params)
    # wait for active status
    await ops_test.model.wait_for_idle(apps=[S3_APP_NAME], status="active")
    application_data = await get_application_data(ops_test, APPLICATION_APP_NAME, FIRST_RELATION)
    # check bucket name
    assert application_data["bucket"] == new_bucket_name

    # check that bucket name set in the requirer application is correct
    await ops_test.model.add_relation(S3_APP_NAME, f"{APPLICATION_APP_NAME}:{SECOND_RELATION}")
    # wait for relation joined
    async with ops_test.fast_forward():
        await ops_test.model.block_until(
            lambda: is_relation_joined(ops_test, SECOND_RELATION, SECOND_RELATION)
            == True  # noqa: E712
        )
        await ops_test.model.wait_for_idle(apps=APPS, status="active")

    # read data of the second relation
    application_data = await get_application_data(ops_test, APPLICATION_APP_NAME, SECOND_RELATION)
    assert "access-key" in application_data
    assert "secret-key" in application_data
    assert "bucket" in application_data
    # check correctness of connection parameters in the relation databag
    assert application_data["bucket"] == new_bucket_name
    assert application_data["access-key"] == "test-access-key"
    assert application_data["secret-key"] == "new-test-secret-key"
    assert application_data["storage-class"] == "cinder"
    assert application_data["s3-api-version"] == "1.0"
    assert len(json.loads(application_data["attributes"])) == 3
    assert len(json.loads(application_data["tls-ca-chain"])) == 2
    assert application_data["region"] == "us-east-2"
    assert application_data["path"] == "/test/path_1/"


async def test_relation_broken(ops_test: OpsTest):
    """Remove relation and wait for the expected changes in status."""
    # Remove relations
    await ops_test.model.applications[S3_APP_NAME].remove_relation(
        f"{APPLICATION_APP_NAME}:{FIRST_RELATION}", S3_APP_NAME
    )
    await ops_test.model.block_until(
        lambda: is_relation_broken(ops_test, FIRST_RELATION, FIRST_RELATION) is True
    )
    await ops_test.model.applications[S3_APP_NAME].remove_relation(
        f"{APPLICATION_APP_NAME}:{SECOND_RELATION}", S3_APP_NAME
    )
    await ops_test.model.block_until(
        lambda: is_relation_broken(ops_test, SECOND_RELATION, SECOND_RELATION) is True
    )
    # test correct application status
    async with ops_test.fast_forward():
        await asyncio.gather(
            ops_test.model.wait_for_idle(
                apps=[S3_APP_NAME], status="active", raise_on_blocked=True
            ),
            ops_test.model.wait_for_idle(
                apps=[APPLICATION_APP_NAME], status="waiting", raise_on_blocked=True
            ),
        )
