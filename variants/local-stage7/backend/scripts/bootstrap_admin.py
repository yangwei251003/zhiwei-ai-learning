from __future__ import annotations

import argparse
import getpass
import os
import sys
from collections.abc import Callable, Mapping, Sequence

from sqlalchemy import inspect

from app.core.config import Settings, get_settings
from app.core.database import build_engine, build_session_factory
from app.services.admin_bootstrap import AdminBootstrapError, bootstrap_admin


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="安全创建小智析析的首个管理员账户")
    parser.add_argument("--username", required=True, help="管理员用户名")
    parser.add_argument("--email", required=True, help="管理员邮箱")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="从 XZX_ADMIN_PASSWORD 环境变量读取密码",
    )
    return parser


def run(
    argv: Sequence[str] | None = None,
    *,
    settings: Settings | None = None,
    password_reader: Callable[[str], str] = getpass.getpass,
    environ: Mapping[str, str] | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    settings = settings or get_settings()
    engine = build_engine(settings.database_url)
    try:
        if not inspect(engine).has_table("users"):
            print(
                "数据库尚未迁移，请先运行 alembic upgrade head。",
                file=sys.stderr,
            )
            return 1
        if args.non_interactive:
            password = (environ or os.environ).get("XZX_ADMIN_PASSWORD", "")
            if not password:
                print(
                    "非交互模式需要设置 XZX_ADMIN_PASSWORD。",
                    file=sys.stderr,
                )
                return 1
        else:
            password = password_reader("管理员密码：")
            confirmation = password_reader("再次输入管理员密码：")
            if password != confirmation:
                print("两次输入的密码不一致。", file=sys.stderr)
                return 1
        result = bootstrap_admin(
            build_session_factory(engine),
            username=args.username,
            email=args.email,
            password=password,
        )
    except AdminBootstrapError as exc:
        print(f"管理员初始化失败：{exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    print(f"管理员已创建：{result.username} <{result.email}>")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
