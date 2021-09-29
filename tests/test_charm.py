# Copyright 2021 Canonical Ltd.
# SPDX-License-Identifier: Apache-2.0

import json
import unittest
import unittest.mock
import uuid


def test_set_charm_config_without_changes_does_not_update(s3_charm):
    original_values = {
        "s3_endpoint": "s3.amazonaws.com",
        "s3_region": "us-west-2",
        "s3_path": "filestore",
    }
    send_credentials_mock = s3_charm.stack.enter_context(
        unittest.mock.patch.object(s3_charm.charm, "_send_s3_credentials")
    )
    s3_charm.harness.update_config(original_values)
    assert send_credentials_mock.call_count == 0


def test_set_charm_config_with_changes_updates(s3_charm):
    send_credentials_mock = s3_charm.stack.enter_context(
        unittest.mock.patch.object(s3_charm.charm, "_send_s3_credentials")
    )
    original_values = {
        "s3_endpoint": "s3.amazonaws.com",
        "s3_bucket": str(uuid.uuid4()).replace("-", ""),
        "s3_region": "us-west-2",
        "s3_path": "filestore",
    }
    new_values = original_values.copy()
    new_values["s3_access_key_id"] = "fake-access-key"
    new_values["s3_secret_access_key"] = "fake-secret-access-key"
    s3_charm.harness.update_config(new_values)
    send_credentials_mock.assert_called_once()


def test_set_s3_credentials_action_updates_config(s3_charm):
    send_credentials_mock = s3_charm.stack.enter_context(
        unittest.mock.patch.object(s3_charm.charm, "_send_s3_credentials")
    )
    access_key = "fake-access-key"
    secret = "fake-secret-access-key"
    event = unittest.mock.Mock(
        params={"access-key-id": access_key, "secret-access-key": secret}
    )
    s3_charm.charm._on_sync_s3_credentials(event)
    send_credentials_mock.assert_called_once()
    assert s3_charm.charm._stored.s3_access_key_id == access_key
    assert s3_charm.charm._stored.s3_secret_access_key == secret


def test_send_s3_credentials(s3_charm):
    set_credentials_mock = s3_charm.stack.enter_context(
        unittest.mock.patch.object(s3_charm.charm.s3_provider, "set_credentials")
    )
    new_values = {
        "s3_endpoint": "s3.amazonaws.com",
        "s3_bucket": str(uuid.uuid4()).replace("-", ""),
        "s3_region": "us-west-2",
        "s3_path": "filestore",
        "s3_access_key_id": "fake-access-key",
        "s3_secret_access_key": "fake-secret-access-key",
    }
    with s3_charm.harness.hooks_disabled():
        s3_charm.harness.update_config(new_values)
        for k, v in new_values.items():
            setattr(s3_charm.charm._stored, k, v)
    s3_charm.charm._send_s3_credentials()
    set_credentials_mock.assert_called_with(
        **{k.replace("s3_", ""): v for k, v in new_values.items()}
    )


def test_set_s3_credentials(s3_charm):
    set_relation_data_mock = s3_charm.stack.enter_context(
        unittest.mock.patch.object(s3_charm.charm.s3_provider, "_set_relation_data")
    )
    new_values = {
        "endpoint": "s3.fakeaws.com",
        "bucket": str(uuid.uuid4()).replace("-", ""),
        "region": "us-east-2",
        "path": "filestore-fake",
        "access_key_id": "fake-access-key",
        "secret_access_key": "fake-secret-access-key",
    }
    s3_charm.charm.s3_provider.set_credentials(**new_values)
    for k, v in new_values.items():
        assert getattr(s3_charm.charm.s3_provider._stored, k) == v
    set_relation_data_mock.assert_called_once()


def test_generate_data(s3_charm):
    new_values = {
        "bucket": str(uuid.uuid4()).replace("-", ""),
        "region": "us-east-2",
        "endpoint": "s3.fakeaws.com",
        "access_key_id": "fake-access-key",
        "secret_access_key": "fake-secret-access-key",
        "path": "filestore-fake",
    }
    expected = {"s3_credentials": json.dumps(new_values)}
    with s3_charm.harness.hooks_disabled():
        for k, v in new_values.items():
            setattr(s3_charm.charm.s3_provider._stored, k, v)
    assert s3_charm.charm.s3_provider._generate_relation_data() == expected


def test_set_relation_data_without_event(s3_charm):
    new_values = {
        "bucket": str(uuid.uuid4()).replace("-", ""),
        "region": "us-east-2",
        "endpoint": "s3.fakeaws.com",
        "access_key_id": "fake-access-key",
        "secret_access_key": "fake-secret-access-key",
        "path": "filestore-fake",
    }
    with s3_charm.harness.hooks_disabled():
        for k, v in new_values.items():
            setattr(s3_charm.charm.s3_provider._stored, k, v)
    s3_charm.charm.s3_provider._set_relation_data()
    assert s3_charm.consumer_relation.data[s3_charm.charm.app] == {
        "s3_credentials": json.dumps(new_values)
    }


def test_set_relation_data_with_event(s3_charm):
    new_values = {
        "bucket": str(uuid.uuid4()).replace("-", ""),
        "region": "us-east-2",
        "endpoint": "s3.fakeaws.com",
        "access_key_id": "fake-access-key",
        "secret_access_key": "fake-secret-access-key",
        "path": "filestore-fake",
    }
    with s3_charm.harness.hooks_disabled():
        for k, v in new_values.items():
            setattr(s3_charm.charm.s3_provider._stored, k, v)
    event = unittest.mock.MagicMock()
    event.relation.data = {s3_charm.charm.app: {}}
    s3_charm.charm.s3_provider._set_relation_data(event)
    assert event.relation.data[s3_charm.charm.app] == {
        "s3_credentials": json.dumps(new_values)
    }
