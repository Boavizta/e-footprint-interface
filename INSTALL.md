# Local installation

## Install poetry

Follow the instructions on the [official poetry website](https://python-poetry.org/docs/#installation)

## Dependencies installation
```
poetry install
```

## Node
### Install node
Download and install nvm (node version manager) node from https://github.com/nvm-sh/nvm?tab=readme-ov-file#installing-and-updating then install node and npm with
```
nvm install node
```

check installation in the terminal with
```
node --version
npm --version
```
### Install js dependencies via npm

``` 
npm install
```

## Run Django project

### .env

create a .env file in the root directory of the project and add
```
DJANGO_PROD=False
```

### Run migrations

```
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic
```

### Create super user 

In the terminal 
```
python3 manage.py createsuperuser
```

### Launch boostrap css files continuous generation

```
npm run watch
```

### Run application

```
poetry run python manage.py runserver
```

# Run tests

## Python tests
```
poetry run python manage.py test
```

## E2E tests

To run all front end tests in console without opening the browser
```
npx cypress run --e2e
```

To check the tests in the browser, run this command
```
npx cypress open
```
Select E2E Testing in the Cypress window that opens and choose the browser you want to run the tests in.
Then click on the test file you want to run in the specs tabs

## js unit tests

```shell
npm install jest --global
jest
```
