from collections import defaultdict
from typing import Any, Callable, Dict, List, Tuple, TypeVar, Union, cast

from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import BaseRoute

CallableT = TypeVar("CallableT", bound=Callable[..., Any])


def version(major: int, minor: int = 0, prefix: str = "") -> Callable[[CallableT], CallableT]:
    def decorator(func: CallableT) -> CallableT:
        func._api_version = (major, minor)  # type: ignore
        func._custom_prefix = prefix  # type: ignore
        return func

    return decorator


def version_to_route(
        route: BaseRoute,
        default_version: Tuple[int, int]
) -> tuple[Union[tuple[int, int], Any], APIRoute, Any]:
    api_route = cast(APIRoute, route)
    version = getattr(api_route.endpoint, "_api_version", default_version)
    custom_prefix = getattr(api_route.endpoint, "_custom_prefix", "")
    return version, api_route, custom_prefix


def VersionedFastAPI(
        app: FastAPI,
        version_format: str = "{major}.{minor}",
        version_prefix: str = "/v{major}_{minor}",
        invert_prefix: bool = False,
        default_version: Tuple[int, int] = (1, 0),
        enable_latest: bool = False,
        **kwargs: Any,
) -> FastAPI:
    parent_app = FastAPI(
        title=app.title,
        **kwargs,
    )
    version_route_mapping: Dict[Tuple[int, int, str], List[APIRoute]] = defaultdict(
        list
    )
    version_routes = [
        version_to_route(route, default_version) for route in app.routes
    ]

    for version, route, custom_prefix in version_routes:
        extended_version = version + (custom_prefix,)
        version_route_mapping[extended_version].append(route)  # type: ignore

    unique_routes: Dict[Tuple[str, str], APIRoute] = {}
    versions = sorted(version_route_mapping.keys())
    for version in versions:
        major, minor, custom_prefix = version
        prefix = version_prefix.format(major=major, minor=minor)
        prefix = custom_prefix + prefix if invert_prefix else prefix + custom_prefix
        semver = custom_prefix + version_format.format(major=major, minor=minor)
        versioned_app = FastAPI(
            title=app.title,
            description=app.description,
            version=semver,
        )
        if invert_prefix:
            for route in version_route_mapping[version]:
                for method in route.methods:
                    unique_routes[(prefix, (route.path + "|" + method))] = route
            matches = list(filter(lambda key:  key[0].startswith(custom_prefix), unique_routes.keys()))
            for key in matches:
                versioned_app.router.routes.append(unique_routes[key])
        else:
            for route in version_route_mapping[version]:
                for method in route.methods:
                    unique_routes[route.path + "|" + method] = route  # type: ignore
            for route in unique_routes.values():
                versioned_app.router.routes.append(route)

        parent_app.mount(prefix, versioned_app)

        @parent_app.get(
            f"{prefix}/openapi.json", name=semver, tags=["Versions"]
        )
        @parent_app.get(f"{prefix}/docs", name=semver, tags=["Documentations"])
        def noop() -> None:
            ...

    if enable_latest:
        prefix = "/latest"
        major, minor, custom_prefix = version
        semver = version_format.format(major=major, minor=minor)
        versioned_app = FastAPI(
            title=app.title,
            description=app.description,
            version=semver,
        )
        for route in unique_routes.values():
            versioned_app.router.routes.append(route)
        parent_app.mount(prefix, versioned_app)

    return parent_app
