import traceback

from quart import (Blueprint, Quart, abort, current_app, g, jsonify, request,
                   session)

from website.utils.captcha import FunCaptcha
from website.utils.oauth import OAuth2

# session.pop('logged_in', None)
blueprint = Blueprint("api", __name__, url_prefix="/api")
from website.blueprints.api.v1.captcha import blueprint as v1_captcha

blueprint.register_blueprint(v1_captcha)

@blueprint.route("/")
async def index():
    return jsonify(message="Success")

@blueprint.before_request
async def check_api_key():
    whitelisted_paths = {"/api/captcha/job", "/api/captcha/submit", "/api/captcha/count"}
    auth_required_paths = {"/api/captcha/job", "/api/captcha/submit", "/api/captcha/count"}

    if request.path not in whitelisted_paths:
        async with current_app.db_pool.acquire() as connection:
            api_keys = await connection.fetch("SELECT uuid FROM api.keys WHERE active = TRUE")
            if api_keys is None:
                abort(404)
            header = request.headers.get("x-api-key")
            arg = request.args.get("api_key")
            if not (header or arg in (str(key[0]) for key in api_keys)):
                abort(404)

    if request.path in auth_required_paths:
        discord_token = session.get("token")
        if not discord_token:
            abort(401)
        else:
            valid_session = await OAuth2.verify_session(discord_token)
            if valid_session is False:
                session.pop("token", None)
                abort(401)
            else:
                g.discord_data = valid_session


@blueprint.errorhandler(401)
async def access_denied(e):
    return jsonify(code=401, message="Unauthorized"), 401


@blueprint.errorhandler(429)
async def rate_limited(e):
    return jsonify(code=429, message="Too many requests!"), 429


@blueprint.errorhandler(500)
async def server_error(e):
    current_app.logger.error(traceback.format_exc())
    return jsonify(code=500, message="Internal server error"), 500
