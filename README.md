# Heatmap Example

## How to run locally
```sh
make up      # start all services (fresh containers always built)
make follow  # follow the logs
make down    # take down services (database volume will be deleted)
```

### Build Postgis Container for on ARM machine
There are no `postgis/postgis` ARM containers in the docker repository. You can build the
container locally if needed.
```sh
make arm-docker-postgis
```

## How to run tests locally
```sh
make test
make down  # test runs `make up` local database must be running for some tests.
```

## Development
These development notes expect you are running inside the ubuntu devcontainer environment.

### Using the devcontainer
You will need to have the [devcontainer cli](https://github.com/devcontainers/cli) installed.
You will need to have the [dca command](https://github.com/essercodes/devcontainer) on $PATH.

```sh
devcontainer up
dca
```

### Installing Development Dependencies
```sh
make install-python-dependencies
```

### Link claude skills
```sh
ln -s .agents .claude
chown :project -h .claude
```

### Install Claude Dependencies
```sh
source ./venv/bin/activate
pip install basedpyright

claude plugin marketplace add datacas/claude-basedpyright-lsp
claude plugin install basedpyright-lsp@basedpyright-marketplace
```
