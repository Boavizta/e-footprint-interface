# Setup your Docker environment

### Install Docker Desktop

Install Docker Desktop and choose the right architecture for you (e.g. arm64 for Mac Silicon) : [Link](https://www.docker.com/products/docker-desktop/)

### Install brew (for macOS)

On macOS, install [Homebrew](https://brew.sh/), so you can easily install some required stuff.

### Update your system /etc/hosts file

```console
# At the root directory of the repository
sudo sh -c 'cat docker/conf/host >> /etc/hosts'
```

### Setup HTTPs certificates for Localhost

```console
# Remember: need to install homebrew first
brew install nss mkcert
```

Or find another solution for your platform : Windows, Linux...

Source: [https://github.com/FiloSottile/mkcert](https://github.com/FiloSottile/mkcert)

### Install the CA Root for localhost

```console
mkcert -install
```

### Create self-signed certificates for boavizta.dev domain & sub-domains

```console
# At the root directory of the repository
mkcert -cert-file docker/conf/ssl/local-cert.pem -key-file docker/conf/ssl/local-key.pem "*.services.boavizta.dev" "*.boavizta.dev" "services.boavizta.dev" "boavizta.dev" "traefik"
```

Don't forget to restart your Chrome or Firefox.

### Run the stack

**The first step is to create your .env file. Simply copy the [.env.dist](.env.dist) and set the project  repositories' path on your system.**

```console
cp .env.dist .env
```

**Before the first launch, run this command to create the required network (one-time)**

```console
docker network create traefik
```

**First run the major dev services (traefik, django...)**

```console
docker compose --profile dev up -d
```

### List of local services

| Service Name | Service URL                               |
|--------------|-------------------------------------------|
| Web App      | https://efootprint.boavizta.dev/          |
| Traefik      | https://traefik.boavizta.dev/             |
