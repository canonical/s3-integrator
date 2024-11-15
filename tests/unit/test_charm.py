# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import unittest
from asyncio.log import logger
from unittest import mock

from ops.model import BlockedStatus
from ops.testing import Harness

from charm import S3IntegratorCharm


class TestCharm(unittest.TestCase):
    def setUp(self):
        self.harness = Harness(S3IntegratorCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()
        self.peer_relation_id = self.harness.add_relation(
            "s3-integrator-peers", "s3-integrator-peers"
        )
        self.charm = self.harness.charm

    def test_on_start(self):
        """Checks that the charm started in blockled status for missing parameters."""
        self.harness.set_leader(True)
        self.charm.on.config_changed.emit()
        self.charm.on.start.emit()
        # check that the charm is in blocked status
        logger.info(f"Status: {self.harness.model.unit.status}")
        self.assertTrue(isinstance(self.harness.model.unit.status, BlockedStatus))

    def test_on_config_changed(self):
        """Checks that configuration parameters are correctly stored in the databag."""
        # ensure that the peer relation databag is empty
        peer_relation_databag = self.harness.get_relation_data(
            self.peer_relation_id, self.harness.charm.app
        )
        self.assertEqual(peer_relation_databag, {})
        # trigger the leader_elected and config_changed events
        self.harness.set_leader(True)
        self.harness.update_config({"region": "test-region"})
        self.harness.update_config({"endpoint": "test-endpoint"})

        # ensure that the peer relation has 'cluster_name' set to the config value
        peer_relation_databag = self.harness.get_relation_data(
            self.peer_relation_id, self.harness.charm.app
        )

        self.assertEqual(peer_relation_databag["region"], "test-region")
        self.assertEqual(peer_relation_databag["endpoint"], "test-endpoint")

        peer_relation_databag = self.harness.get_relation_data(
            self.peer_relation_id, self.harness.charm.app
        )

        self.harness.update_config({"region": ""})
        self.assertIsNot("region", peer_relation_databag)

    def test_set_access_and_secret_key(self):
        """Tests that secret and access keys are set."""
        self.harness.set_leader(True)
        action_event = mock.Mock()
        action_event.params = {"access-key": "test-access-key", "secret-key": "test-secret-key"}
        self.harness.charm._on_sync_s3_credentials_action(action_event)

        access_key = self.harness.charm.app_peer_data["access-key"]
        secret_key = self.harness.charm.app_peer_data["secret-key"]
        # verify app data is updated and results are reported to user
        self.assertEqual("test-access-key", access_key)
        self.assertEqual("test-secret-key", secret_key)

        action_event.set_results.assert_called_once_with({
            "ok": "Credentials successfully updated."
        })

    def test_get_s3_credentials(self):
        """Tests that secret and access key are retrieved correctly."""
        self.harness.set_leader(True)
        event = mock.Mock()
        self.harness.charm.on_get_credentials_action(event)
        event.fail.assert_called()

        self.harness.charm.app_peer_data["access-key"] = "test-access-key"
        self.harness.charm.app_peer_data["secret-key"] = "test-secret-key"

        self.harness.charm.on_get_credentials_action(event)
        event.set_results.assert_called_with({"ok": "Credentials are configured."})

    def test_get_connection_info(self):
        """Tests that s3 connection parameters are retrieved correctly."""
        self.harness.set_leader(True)
        event = mock.Mock()
        self.harness.charm.app_peer_data["access-key"] = "test-access-key"
        self.harness.charm.app_peer_data["secret-key"] = "test-secret-key"
        self.harness.charm.on_get_connection_info_action(event)
        event.set_results.assert_called_with({
            "access-key": "************",
            "secret-key": "************",
        })
        # update some configuration parameters
        self.harness.update_config({"region": "test-region"})
        self.harness.update_config({"endpoint": "test-endpoint"})
        # test that new parameter are present in the event results.
        self.harness.charm.on_get_connection_info_action(event)
        event.set_results.assert_called_with({
            "access-key": "************",
            "secret-key": "************",
            "region": "test-region",
            "endpoint": "test-endpoint",
        })
