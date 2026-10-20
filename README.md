# Heatmap Example

[frontend](https://d3dtufqyf97rqt.cloudfront.net)
[api](https://ta6vnix4hb.execute-api.us-east-1.amazonaws.com)

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
make test  # or test-booking, test-vehicle, test-frontend
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

### Run Vite for Frontend
```sh
cd containers
pnpm run dev --host --port 8080
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
   images tagged with the commit SHA, runs each service's database migrations, and deploys booking,
   vehicle and frontend with the real images.
   If the images are already in ECR you can pass thier image tags to the first apply:
   `terraform apply -var 'image_tags={booking="<sha>",vehicle="<sha>",frontend="<sha>"}'`
5. Check it works: `curl "$(terraform output -raw api_url)/booking/health"` (and `/vehicle/health`).
6. Check the frontend: `terraform output -raw frontend_url`

### Gotchas
- If ecs task definitions (like environment variables) change, manually replace them: 
```sh
terraform apply -replace='aws_ecs_task_definition.service["frontend"]' -var 'image_tags={frontend="<sha>"}'
```
