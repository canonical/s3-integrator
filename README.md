# s3-integrator
## Description

An operator charm providing an integrator for connecting to s3

## Usage

### Adding your S3 Credentials

To deploy your S3 credentials to the application, run the following action:

```bash
$ juju run-action s3-integrator/leader sync-s3-credentials access-key-id=<your_key> secret-access-key=<your_secret_key>
```

### Configuring the Integrator

To configure the S3 integrator charm, you may provide the following configuration options:

```yaml
s3_endpoint: ""
s3_bucket: ""
s3_region: ""
s3_path: "filestore"
```

### Deploying the S3 Integrator

```bash
$ juju deploy ./s3-integrator_ubuntu-20.04-amd64.charm
```

