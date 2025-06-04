# Release process

## Update interface version in [pyproject.toml](pyproject.toml)

## Update [CHANGELOG.md](CHANGELOG.md)

## Update [README.md](README.md) if needed

## Update poetry and npm dependencies

```shell
poetry update
npm install
```
if necessary, update node

```shell
nvm install node
```

## Generate latest requirements files with poetry

if not already done, install the export plugin:
```shell
poetry self add poetry-plugin-export
```
then
```shell
poetry export -f requirements.txt --without-hashes -o requirements.txt 
```

## Make sure all tests pass

Make sure css files are up to date.

```shell
npm run watch
```

if necessary, run

```shell
npm install jest --global
```

to install jest.

```shell
poetry run python manage.py test tests
npm run test:e2e
jest
```

## Make new version commit, starting with [Vx.y.z]

## Make PR and wait for CI to pass and review

## Test that the project works locally with connection to the production database and then deploy following the instructions in [DEPLOY_TO_PROD.md](DEPLOY_TO_PROD.md)

## Merge main with new version commit
