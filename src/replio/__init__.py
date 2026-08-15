from importlib.metadata import version, PackageNotFoundError


def get_version() -> str:
    try:
        return version('replio')
    except PackageNotFoundError:
        return 'unknown'
