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
make test  # or test-booking, test-vehicle, test-schema-migrations
make down  # tests start the database container; stop it when done
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

## op init aws

```sh
OP_SERVICE_ACCOUNT_TOKEN=$(cat /home/max/op_secret) op --account my.1password.com plugin init aws
# echo "source /home/max/.config/op/plugins.sh" >> ~/.bashrc && source ~/.bashrc
```

## Deploying to AWS

Infrastructure is in `terraform/`

### First-time setup
AWS is set up under a separate AWS account, configured in AWS Organiztions.

You need AWS credentials that can assume the account's `OrganizationAccountAccessRole`

1. Check `github_repository` in `terraform/github_oidc.tf`. It must match the `sub` claim your
   GitHub org/repo sends, which can include numeric IDs (`owner@id/repo@id`). A mismatch shows up
   as "Not authorized to perform sts:AssumeRoleWithWebIdentity" in the workflow. The default subject
   claim prefix is can be found in the repository settings: 
   https://github.com/<org>/<repo>/settings/actions/oidc-configuration
2. Create the infrastructure:
   ```sh
   cd terraform
   terraform init
   terraform apply
   ```
   The ECS services start with a placeholder image tag and can't run yet; that's expected.
3. In the GitHub repo, go to Settings -> Secrets and variables -> Actions -> Variables and add the
   repository variable `AWS_ROLE_ARN` with the value of `terraform output -raw github_actions_role_arn`.
4. Push to `main` (or re-run the workflow). The first run rebuilds every container, pushes the
   images tagged with the commit SHA, runs the database migrations, and deploys booking and
   vehicle with the real images.
   If the images are already in ECR you can pass thier image tags to the first apply:
   `terraform apply -var 'image_tags={booking="<sha>",vehicle="<sha>",schema-migrations="<sha>"}'`
5. Check it works: `curl "$(terraform output -raw api_url)/booking/health"` (and `/vehicle/health`).

