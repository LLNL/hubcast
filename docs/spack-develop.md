# Developing Hubcast with Spack (Recommended)
## Prerequisites
You'll need to install Spack if you haven't already. You can clone Spack from
GitHub by running the following,

```bash
$ git clone -c feature.manyFiles=true https://github.com/spack/spack.git
$ cd spack/
```

Next we'll need to load Spack into our shell. (Add one of the following lines
-- prepended by the directory you cloned spack into -- to your
`.zshrc`, `.bashrc`, or equivalent to make it permenent.)

```bash
# For bash/zsh/sh
$ . spack/share/spack/setup-env.sh

# For tcsh/csh
$ source spack/share/spack/setup-env.csh

# For fish
$ . spack/share/spack/setup-env.fish
```

## Activating the Development Environment
Activate the Spack environment by entering the following,
```bash
$ cd path/to/hubcast
$ spack env activate -d .
```

> [!TIP]
> If you've got [direnv](https://direnv.net) installed on your system
> you can run `direnv allow` to automatically load the spack environment
> when you cd into the repository in the future.

## Installing the Development Environment
Install Hubcast's development dependencies with Spack by running
the following,
```bash
$ spack install
```

## Upgrading the Development Environment
To update your Spack environment run,
```bash
$ spack concretize --force --fresh
$ spack install
```
