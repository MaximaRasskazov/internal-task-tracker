import argparse
import json
from pathlib import Path

from app.core.paths import PROJECT_ROOT


def render_openapi() -> str:
    # Import lazily: init_env must work even when there is no valid application configuration.
    from app.core.config import Settings
    from app.main import create_app

    application = create_app(Settings(_env_file=None, app_env="test"))
    return json.dumps(application.openapi(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the implemented API contract deterministically"
    )
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "docs/api/openapi.json")
    parser.add_argument("--check", action="store_true", help="Fail if the saved contract differs")
    args = parser.parse_args()
    output: Path = args.output.absolute()
    expected = render_openapi()
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != expected:
            parser.exit(1, f"OpenAPI is missing or stale: {output}\n")
        print(f"OpenAPI is current: {output}")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(expected, encoding="utf-8", newline="\n")
        print(f"Exported OpenAPI: {output}")


if __name__ == "__main__":
    main()
