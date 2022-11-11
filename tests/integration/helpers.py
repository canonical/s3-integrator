#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
from typing import Dict, Optional

import yaml
from juju.unit import Unit
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)


async def fetch_action_get_credentials(unit: Unit) -> Dict:
    """Helper to run an action to fetch credentials.

    Args:
        unit: The juju unit on which to run the get-s3-credentials action for credentials
        action: the
    Returns:
        A dictionary with the server config username and password
    """
    action = await unit.run_action(action_name="get-s3-credentials")
    result = await action.wait()
    return result.results


async def fetch_action_get_connection_info(unit: Unit) -> Dict:
    """Helper to run an action to fetch connection info.

    Args:
        unit: The juju unit on which to run the get_connection_info action for credentials
    Returns:
        A dictionary with the server config username and password
    """
    action = await unit.run_action(action_name="get-s3-connection-info")
    result = await action.wait()
    return result.results


async def fetch_action_sync_s3_credentials(unit: Unit, access_key: str, secret_key: str) -> Dict:
    """Helper to run an action to sync credentials.

    Args:
        unit: The juju unit on which to run the get-password action for credentials
        access_key: the access_key to access the s3 compatible endpoint
        secret_key: the secret key to access the s3 compatible endpoint
    Returns:
        A dictionary with the server config username and password
    """
    parameters = {"access-key": access_key, "secret-key": secret_key}
    action = await unit.run_action(action_name="sync-s3-credentials", **parameters)
    result = await action.wait()

    return result.results


def is_relation_joined(ops_test: OpsTest, endpoint_one: str, endpoint_two: str) -> bool:
    """Check if a relation is joined.

    Args:
        ops_test: The ops test object passed into every test case
        endpoint_one: The first endpoint of the relation
        endpoint_two: The second endpoint of the relation
    """
    for rel in ops_test.model.relations:
        endpoints = [endpoint.name for endpoint in rel.endpoints]
        if endpoint_one in endpoints and endpoint_two in endpoints:
            return True
    return False


def is_relation_broken(ops_test: OpsTest, endpoint_one: str, endpoint_two: str) -> bool:
    """Check if a relation is broken.

    Args:
        ops_test: The ops test object passed into every test case
        endpoint_one: The first endpoint of the relation
        endpoint_two: The second endpoint of the relation
    """
    for rel in ops_test.model.relations:
        endpoints = [endpoint.name for endpoint in rel.endpoints]
        if endpoint_one not in endpoints and endpoint_two not in endpoints:
            return True
    return False


async def run_command_on_unit(unit: Unit, command: str) -> Optional[str]:
    """Run a command in one Juju unit.

    Args:
        unit: the Juju unit instance.
        command: the command to run.

    Returns:
        command execution output or none if the command produces no output.
    """
    # workaround for https://github.com/juju/python-libjuju/issues/707
    action = await unit.run(command)
    result = await action.wait()
    code = str(result.results.get("Code") or result.results.get("return-code"))
    stdout = result.results.get("Stdout") or result.results.get("stdout")
    stderr = result.results.get("Stderr") or result.results.get("stderr")
    assert code == "0", f"{command} failed ({code}): {stderr or stdout}"
    return stdout


async def get_relation_data(
    ops_test: OpsTest,
    application_name: str,
    relation_name: str,
) -> list:
    """Returns a list that contains the relation-data.

    Args:
        ops_test: The ops test framework instance
        application_name: The name of the application
        relation_name: name of the relation to get connection data from
    Returns:
        a list that contains the relation-data
    """
    # get available unit id for the desired application
    units_ids = [
        app_unit.name.split("/")[1]
        for app_unit in ops_test.model.applications[application_name].units
    ]
    assert len(units_ids) > 0
    unit_name = f"{application_name}/{units_ids[0]}"
    raw_data = (await ops_test.juju("show-unit", unit_name))[1]
    if not raw_data:
        raise ValueError(f"no unit info could be grabbed for {unit_name}")
    data = yaml.safe_load(raw_data)
    # Filter the data based on the relation name.
    relation_data = [v for v in data[unit_name]["relation-info"] if v["endpoint"] == relation_name]
    if len(relation_data) == 0:
        raise ValueError(
            f"no relation data could be grabbed on relation with endpoint {relation_name}"
        )

    return relation_data


async def get_application_data(
    ops_test: OpsTest,
    application_name: str,
    relation_name: str,
) -> Dict:
    """Returns the application data bag of a given application and relation.

    Args:
        ops_test: The ops test framework instance
        application_name: The name of the application
        relation_name: name of the relation to get connection data from
    Returns:
        a dictionary that contains the application-data
    """
    relation_data = await get_relation_data(ops_test, application_name, relation_name)
    application_data = relation_data[0]["application-data"]
    return application_data


def get_certificate_from_file(filename: str) -> str:
    """Returns the certificate as a string."""
    with open(filename, "r") as file:
        certificate = file.read()
    return certificate
