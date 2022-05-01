from datetime import timedelta

import asyncpg
from quart import Quart, jsonify, render_template, request
from quart_rate_limiter import RateLimit, RateLimiter
from quart_rate_limiter.redis_store import RedisStore
from werkzeug.middleware.proxy_fix import ProxyFix

# redis_store = RedisStore("redis://@champfaith.alulj7.0001.usw1.cache.amazonaws.com:6379/0")
rate_limiter = RateLimiter(
    # store=redis_store,
    default_limits=[
        RateLimit(10, timedelta(seconds=1)),
        RateLimit(100, timedelta(seconds=60)),
    ],  # "10/second", "100/minute"
)


def create_app(debug: bool):
    application = Quart(__name__)
    if debug is True:
        from dotenv import load_dotenv

        load_dotenv()

    application.config.from_prefixed_env()
    application.config.update(
        {
            "JSON_SORT_KEYS": False,
        }
    )

    rate_limiter.init_app(application)

    @application.before_serving
    async def default_api_key():
        db_login = application.config["POSTGRES_URI"]
        application.db_pool = await asyncpg.create_pool(
            db_login, min_size=5, max_size=50
        )
        async with application.db_pool.acquire() as connection:
            api_key = await connection.fetchrow("SELECT id FROM api.keys")
            if api_key is None:
                import uuid

                new_api_key = uuid.uuid4()
                await connection.execute(
                    f"INSERT INTO api.keys (uuid) VALUES ($1)", new_api_key
                )

    @application.errorhandler(404)
    async def page_not_found(e):
        return (
            await render_template("error.html", status=404),
            404,
            {"Refresh": "1.5; url=/"},
        )

    @application.errorhandler(405)
    async def method_not_allowed(e):
        return jsonify(code=405, message="Method not allowed"), 405

    @application.route("/favicon.ico")
    async def favicon_ico():
        return await application.send_static_file("favicon.ico")

    @application.route("/robots.txt")
    async def robots_txt():
        return await application.send_static_file("robots.txt")

    from website.blueprints.api.api import blueprint as api_blueprint
    from website.blueprints.views.views import blueprint as views_blueprint

    application.register_blueprint(api_blueprint)
    application.register_blueprint(views_blueprint)

    return application
