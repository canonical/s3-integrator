# Integrating artifactory

## Integrating with consumer charms

To consume the S3 Integrator charm, add this repository to your `requirements.txt` or
`setup.py`: `s3-integrator@ git+https://github.com/canonical/s3-integrator.git`. Then,
in `src/charm.py`, include the following:

```python
from charms.s3_integrator.v0.s3 import S3Consumer
```

Then, in your charm `__init__` method, include the following:

```python
    self.s3_credential_client = S3Consumer(self, "<name_from_metadata_yaml>")
```

## Example Bundle

An easy way to deploy this charm with relations is via [Juju Bundles](https://juju.is/docs/sdk/bundles).

To do this, create a file called `bundle.yaml`. One example bundle might look like this:

```yaml
description: An app deployment
series: focal

applications:
  s3-integrator:
    charm: "./s3-integrator_ubuntu-20.04-amd64.charm"
    num_units: 1
    options:
      s3_endpoint: 's3.amazonaws.com'
      s3_region: 'eu-west-2'
      s3_bucket: 'my-fake-bucket'
      s3_path: "binary-files"
    
  artifactory:
   charm: "./artifactory-operator_ubuntu-20.04-amd64.charm"
   num_units: 1
   options:
     replicator_allow_self_signed_certificates: true
     s3_enabled: true
     repo_types: debian,generic,npm,pypi
   constraints: mem=4G cores=4

relations:
  - ["artifactory:db", "postgres:db"]
  - ["haproxy:reverseproxy", "artifactory:website"]
  - ["elasticsearch:client", "artifactory:elasticsearch"]
  - ["artifactory:s3_credentials", "s3-integrator:s3_credentials"]
```
