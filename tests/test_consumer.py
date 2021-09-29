import unittest
import unittest.mock


def test_s3_credentials(s3_consumer):
    bucket = "fake-bucket"
    endpoint = "https://fake-endpoint.com"
    path = "fakepath"
    region = "fake-region-1"
    access_key_id = "fake_access_key"
    secret_access_key = "fake_secret_access_key"
    s3_consumer.set_s3_relation_data(
        bucket=bucket,
        endpoint=endpoint,
        path=path,
        region=region,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
    )
    assert s3_consumer.charm.s3_client.get_credentials() == {
        "bucket": bucket,
        "endpoint": endpoint,
        "path": path,
        "region": region,
        "access_key_id": access_key_id,
        "secret_access_key": secret_access_key,
    }
    assert s3_consumer.charm.event_calls["credentials_changed"] == 1


def test_s3_credentials_removed(s3_consumer):
    bucket = "fake-bucket"
    endpoint = "https://fake-endpoint.com"
    path = "fakepath"
    region = "fake-region-1"
    access_key_id = "fake_access_key"
    secret_access_key = "fake_secret_access_key"
    s3_consumer.set_s3_relation_data(
        bucket=bucket,
        endpoint=endpoint,
        path=path,
        region=region,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
    )
    s3_consumer.set_s3_relation_data(
        bucket="",
        endpoint="",
        path="",
        region="",
        access_key_id=None,
        secret_access_key=None,
    )
    assert s3_consumer.charm.s3_client.get_credentials() == {
        "bucket": "",
        "endpoint": "",
        "path": "",
        "region": "",
    }
    assert s3_consumer.charm.event_calls["credentials_changed"] == 2
